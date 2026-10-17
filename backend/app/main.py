"""NaSCon 26 Multi-Sport League Platform Backend.
Implements the complete mandatory autograder interface (/audit/v1/*), /health, and /api/v1/ping.
"""
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Header, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.build_apk import ensure_apk_exists
from app.errors import AppException

ensure_apk_exists()
from app.fixtures import (
    generate_double_elim,
    generate_round_robin,
    generate_single_elim,
    generate_swiss,
)
from app.offline_sync import process_offline_sync
from app.rbac import authorize_probe, get_rbac_matrix
from app.roster import get_roster_history, process_transfer, setup_roster
from app.scoring import append_event, project_score, register_league
from app.sports import validate_and_create_sport
from app.standings import compute_standings
from app.state import state
from app.store import get_inventory, process_checkout

app = FastAPI(title="NaSCon 26 League Platform")

# Rolling rate limiter for /api/v1/*
# 100 requests per rolling 10 s per client IP
RATE_LIMIT_WINDOW = 10.0
RATE_LIMIT_MAX = 100
request_timestamps: Dict[str, List[float]] = {}


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return exc.to_response()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    bad_fields = []
    for err in exc.errors():
        loc = err.get("loc", [])
        if loc:
            bad_fields.append(".".join(str(x) for x in loc if x != "body"))
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Schema or validation error in request body.",
                "details": {"fields": bad_fields},
            }
        },
    )


@app.middleware("http")
async def security_and_limit_middleware(request: Request, call_next):
    # Check body size for /audit/v1/* POST/PATCH
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 1048576:
        return JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": "PAYLOAD_TOO_LARGE",
                    "message": "Body exceeds 1 MB limit.",
                    "details": {"max_bytes": 1048576},
                }
            },
        )

    # Rate limiting for /api/v1/* (exempt /audit/v1/* and /health)
    path = request.url.path
    if path.startswith("/api/v1/"):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        with state.lock:
            ts_list = request_timestamps.setdefault(client_ip, [])
            # Purge older than rolling 10s
            cutoff = now - RATE_LIMIT_WINDOW
            ts_list = [t for t in ts_list if t > cutoff]
            request_timestamps[client_ip] = ts_list

            if len(ts_list) >= RATE_LIMIT_MAX:
                retry_after = int(RATE_LIMIT_WINDOW)
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMITED",
                            "message": "Rate limit exceeded for /api/v1/*.",
                            "details": {"limit": RATE_LIMIT_MAX, "window_seconds": RATE_LIMIT_WINDOW},
                        }
                    },
                    headers={"Retry-After": str(retry_after)},
                )
            ts_list.append(now)

    response = await call_next(request)
    return response


# --- 5.4 Health Probe ---
@app.get("/health")
def health():
    return {"status": "ok"}


# --- Rate Limit Probe ---
@app.get("/api/v1/ping")
def ping():
    return {"message": "pong", "pong": True}


# --- 5.5 Reset and Baseline Data ---
@app.post("/audit/v1/reset")
async def audit_reset(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    seed = body.get("seed", 42) if isinstance(body, dict) else 42
    stock = body.get("stock") if isinstance(body, dict) else None
    return state.reset(seed=seed, stock=stock)


# --- 5.6 Mystery Sport from JSON ---
@app.post("/audit/v1/sports", status_code=201)
async def audit_create_sport(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise AppException(status_code=400, code="VALIDATION_ERROR", message="Malformed JSON.")
    if not isinstance(body, dict):
        raise AppException(status_code=400, code="VALIDATION_ERROR", message="JSON object required.")
    return validate_and_create_sport(body)


# --- 5.7 Schedule and Bracket Generation ---
@app.post("/audit/v1/fixtures")
async def audit_fixtures(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise AppException(status_code=400, code="VALIDATION_ERROR", message="Malformed JSON.")
    if not isinstance(body, dict):
        raise AppException(status_code=400, code="VALIDATION_ERROR", message="JSON object required.")

    fmt = body.get("format")
    teams = body.get("teams")
    params = body.get("params", {})

    if not isinstance(teams, list) or len(teams) != len(set(teams)):
        raise AppException(status_code=400, code="VALIDATION_ERROR", message="Invalid teams array.", details={"fields": ["teams"]})

    if fmt == "round_robin":
        return generate_round_robin(teams, params)
    elif fmt == "swiss":
        return generate_swiss(teams, params)
    elif fmt == "single_elim":
        return generate_single_elim(teams, params)
    elif fmt == "double_elim":
        return generate_double_elim(teams, params)
    else:
        raise AppException(status_code=400, code="VALIDATION_ERROR", message=f"Unknown format {fmt}.", details={"fields": ["format"]})


# --- 5.8 Register a League for Standings ---
@app.post("/audit/v1/leagues", status_code=201)
async def audit_leagues(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise AppException(status_code=400, code="VALIDATION_ERROR", message="Malformed JSON.")
    return register_league(body)


# --- 5.9 Events and Score Projection ---
@app.post("/audit/v1/events")
async def audit_events(request: Request, response: Response):
    try:
        body = await request.json()
    except Exception:
        raise AppException(status_code=400, code="VALIDATION_ERROR", message="Malformed JSON.")
    st_code, data = append_event(body)
    response.status_code = st_code
    return data


@app.get("/audit/v1/score/{match_id}")
def audit_score(match_id: str):
    return project_score(match_id)


# --- 5.10 Standings ---
@app.get("/audit/v1/standings/{league_id}")
def audit_standings(league_id: str):
    return compute_standings(league_id)


# --- 5.11 Roster, Transfers, Loans and History ---
@app.post("/audit/v1/roster/setup", status_code=201)
async def audit_roster_setup(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise AppException(status_code=400, code="VALIDATION_ERROR", message="Malformed JSON.")
    return setup_roster(body)


@app.post("/audit/v1/roster/transfer")
async def audit_roster_transfer(request: Request, response: Response):
    try:
        body = await request.json()
    except Exception:
        raise AppException(status_code=400, code="VALIDATION_ERROR", message="Malformed JSON.")
    st_code, data = process_transfer(body)
    response.status_code = st_code
    return data


@app.get("/audit/v1/roster/history/{player_id}")
def audit_roster_history(player_id: str, as_of: Optional[str] = None):
    return get_roster_history(player_id, as_of=as_of)


# --- 5.12 Checkout and Inventory ---
@app.post("/audit/v1/checkout")
async def audit_checkout(request: Request, response: Response):
    try:
        body = await request.json()
    except Exception:
        raise AppException(status_code=400, code="VALIDATION_ERROR", message="Malformed JSON.")
    st_code, data = process_checkout(body)
    response.status_code = st_code
    return data


@app.get("/audit/v1/inventory/{variant_id}")
def audit_inventory(variant_id: str):
    return get_inventory(variant_id)


# --- 5.13 RBAC, Probe Routes and Security ---
@app.post("/audit/v1/rbac-matrix")
def audit_rbac_matrix():
    return get_rbac_matrix()


@app.post("/audit/v1/rbac/tenants")
def probe_p1(authorization: Optional[str] = Header(None)):
    return authorize_probe("P1", authorization)


@app.post("/audit/v1/rbac/leagues/{league_id}/fixtures")
def probe_p2(league_id: str, authorization: Optional[str] = Header(None)):
    return authorize_probe("P2", authorization, resource_id=league_id)


@app.post("/audit/v1/rbac/clubs/{club_id}/roster")
def probe_p3(club_id: str, authorization: Optional[str] = Header(None)):
    return authorize_probe("P3", authorization, resource_id=club_id)


@app.post("/audit/v1/rbac/clubs/{club_id}/products")
def probe_p4(club_id: str, authorization: Optional[str] = Header(None)):
    return authorize_probe("P4", authorization, resource_id=club_id)


@app.patch("/audit/v1/rbac/players/{player_id}")
def probe_p5(player_id: str, authorization: Optional[str] = Header(None)):
    return authorize_probe("P5", authorization, resource_id=player_id)


@app.get("/audit/v1/rbac/clubs/{club_id}")
def probe_p6(club_id: str, authorization: Optional[str] = Header(None)):
    return authorize_probe("P6", authorization, resource_id=club_id)


@app.get("/audit/v1/rbac/platform/config")
def probe_p7(authorization: Optional[str] = Header(None)):
    return authorize_probe("P7", authorization)


# --- 5.14 Offline Sync ---
@app.post("/audit/v1/offline-sync")
async def audit_offline_sync(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise AppException(status_code=400, code="VALIDATION_ERROR", message="Malformed JSON.")
    return process_offline_sync(body)
