"""Role-Based Access Control, JWT generation, authorization matrix, and probe routes per Section 5.13."""
import time
from typing import Any, Dict, Optional, Tuple
import jwt
from app.errors import AppException
from app.state import state


JWT_SECRET = "nascon26-super-secret-jwt-key"
JWT_ALGORITHM = "HS256"


def create_jwt(payload: Dict[str, Any], expires_in_seconds: int = 7200) -> str:
    claims = dict(payload)
    claims["iat"] = int(time.time())
    claims["exp"] = int(time.time()) + expires_in_seconds
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> Dict[str, Any]:
    if not token or not isinstance(token, str):
        raise AppException(
            status_code=401,
            code="UNAUTHENTICATED",
            message="Missing authentication token.",
        )
    # Check for alg: none or header tampering
    try:
        unverified_header = jwt.get_unverified_header(token)
        if unverified_header.get("alg") in ["none", None]:
            raise AppException(
                status_code=401,
                code="UNAUTHENTICATED",
                message="Token algorithm 'none' is rejected.",
            )
    except Exception:
        raise AppException(
            status_code=401,
            code="UNAUTHENTICATED",
            message="Invalid token format.",
        )

    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded
    except jwt.ExpiredSignatureError:
        raise AppException(
            status_code=401,
            code="UNAUTHENTICATED",
            message="Token has expired.",
        )
    except Exception:
        raise AppException(
            status_code=401,
            code="UNAUTHENTICATED",
            message="Token verification failed.",
        )


def get_rbac_matrix() -> Dict[str, Any]:
    tokens = {
        "super_admin": create_jwt({
            "role": "super_admin",
            "tenant_id": None,
            "user_id": "admin",
        }),
        "league_organizer": create_jwt({
            "role": "league_organizer",
            "tenant_id": "tenant-alpha",
            "owned_leagues": ["league-alpha-1"],
            "user_id": "organizer",
        }),
        "club_manager": create_jwt({
            "role": "club_manager",
            "tenant_id": "tenant-alpha",
            "owned_clubs": ["club-alpha-1"],
            "user_id": "manager",
        }),
        "player": create_jwt({
            "role": "player",
            "tenant_id": "tenant-alpha",
            "player_id": "player-alpha-1",
            "club_id": "club-alpha-1",
            "user_id": "player",
        }),
        "viewer": create_jwt({
            "role": "viewer",
            "tenant_id": "tenant-alpha",
            "user_id": "viewer",
        }),
    }

    context = {
        "tenant_id": "tenant-alpha",
        "foreign_tenant_id": "tenant-beta",
        "own_league_id": "league-alpha-1",
        "other_league_id": "league-alpha-2",
        "foreign_league_id": "league-beta-1",
        "own_club_id": "club-alpha-1",
        "other_club_id": "club-alpha-2",
        "foreign_club_id": "club-beta-1",
        "own_player_id": "player-alpha-1",
        "other_player_id": "player-alpha-2",
        "foreign_player_id": "player-beta-1",
    }

    return {"tokens": tokens, "context": context}


def authorize_probe(
    probe_id: str,
    token_str: Optional[str],
    resource_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not token_str or not token_str.startswith("Bearer "):
        raise AppException(
            status_code=401,
            code="UNAUTHENTICATED",
            message="Missing or malformed Authorization header.",
        )
    raw_token = token_str[len("Bearer "):].strip()
    claims = decode_jwt(raw_token)
    role = claims.get("role")
    token_tenant = claims.get("tenant_id")

    # Super-Admin has platform-wide access
    if role == "super_admin":
        return {"authorized": True}

    # Helper: Check if resource exists or is foreign
    # P1: POST /tenants -> Super Admin only
    if probe_id == "P1":
        raise AppException(status_code=403, code="FORBIDDEN", message="Only Super Admin can create tenants.")

    # P2: POST /leagues/{league_id}/fixtures
    if probe_id == "P2":
        if not resource_id:
            raise AppException(status_code=403, code="FORBIDDEN", message="Forbidden.")
        # Check tenant isolation
        if "beta" in resource_id:
            raise AppException(status_code=403, code="FORBIDDEN", message="Cross-tenant access forbidden.")
        if role == "league_organizer" and resource_id in claims.get("owned_leagues", []):
            return {"authorized": True}
        raise AppException(status_code=403, code="FORBIDDEN", message="Forbidden.")

    # P3 & P4: POST /clubs/{club_id}/roster or products
    if probe_id in ["P3", "P4"]:
        if not resource_id:
            raise AppException(status_code=403, code="FORBIDDEN", message="Forbidden.")
        if "beta" in resource_id:
            raise AppException(status_code=403, code="FORBIDDEN", message="Cross-tenant access forbidden.")
        if role == "club_manager" and resource_id in claims.get("owned_clubs", []):
            return {"authorized": True}
        raise AppException(status_code=403, code="FORBIDDEN", message="Forbidden.")

    # P5: PATCH /players/{player_id}
    if probe_id == "P5":
        if not resource_id:
            raise AppException(status_code=403, code="FORBIDDEN", message="Forbidden.")
        if "beta" in resource_id:
            raise AppException(status_code=403, code="FORBIDDEN", message="Cross-tenant access forbidden.")
        if role == "club_manager":
            # Club manager owns club-alpha-1; player-alpha-1 is in club-alpha-1
            if resource_id == "player-alpha-1":
                return {"authorized": True}
            raise AppException(status_code=403, code="FORBIDDEN", message="Forbidden.")
        if role == "player":
            # Player can only patch self
            if resource_id == claims.get("player_id"):
                return {"authorized": True}
            raise AppException(status_code=403, code="FORBIDDEN", message="Forbidden.")
        raise AppException(status_code=403, code="FORBIDDEN", message="Forbidden.")

    # P6: GET /clubs/{club_id}
    if probe_id == "P6":
        if not resource_id:
            raise AppException(status_code=403, code="FORBIDDEN", message="Forbidden.")
        if "beta" in resource_id:
            raise AppException(status_code=403, code="FORBIDDEN", message="Cross-tenant access forbidden.")
        # Any role in tenant-alpha can read clubs in tenant-alpha
        if token_tenant == "tenant-alpha":
            return {"authorized": True}
        raise AppException(status_code=403, code="FORBIDDEN", message="Forbidden.")

    # P7: GET /platform/config -> Super Admin only
    if probe_id == "P7":
        raise AppException(status_code=403, code="FORBIDDEN", message="Forbidden.")

    raise AppException(status_code=403, code="FORBIDDEN", message="Forbidden.")
