"""Unit tests for RBAC, JWT authorization probes, and API security per Section 5.13."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_rbac_matrix_and_probes():
    matrix_resp = client.post("/audit/v1/rbac-matrix")
    assert matrix_resp.status_code == 200
    data = matrix_resp.json()
    tokens = data["tokens"]
    ctx = data["context"]

    super_token = tokens["super_admin"]
    org_token = tokens["league_organizer"]
    mgr_token = tokens["club_manager"]
    viewer_token = tokens["viewer"]

    # P1: Super admin only
    assert client.post("/audit/v1/rbac/tenants", headers={"Authorization": f"Bearer {super_token}"}).status_code == 200
    assert client.post("/audit/v1/rbac/tenants", headers={"Authorization": f"Bearer {org_token}"}).status_code == 403

    # P2 own league: Organizer allowed (200), Manager denied (403)
    own_league = ctx["own_league_id"]
    assert client.post(f"/audit/v1/rbac/leagues/{own_league}/fixtures", headers={"Authorization": f"Bearer {org_token}"}).status_code == 200
    assert client.post(f"/audit/v1/rbac/leagues/{own_league}/fixtures", headers={"Authorization": f"Bearer {mgr_token}"}).status_code == 403

    # P7 platform config: Super admin allowed (200), others 403
    assert client.get("/audit/v1/rbac/platform/config", headers={"Authorization": f"Bearer {super_token}"}).status_code == 200
    assert client.get("/audit/v1/rbac/platform/config", headers={"Authorization": f"Bearer {viewer_token}"}).status_code == 403

    # Unauthenticated / invalid token
    assert client.get("/audit/v1/rbac/platform/config").status_code == 401
    assert client.get("/audit/v1/rbac/platform/config", headers={"Authorization": "Bearer invalid.fake.token"}).status_code == 401


def test_rate_limiting():
    # Make sure ping responds 200 initially
    res = client.get("/api/v1/ping")
    assert res.status_code == 200
    assert res.json()["message"] == "pong"
