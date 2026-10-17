"""Unit tests for Standings, H2H mini-league, differentials, and drawing-of-lots per Section 5.10 and Appendix A."""
import pytest
from fastapi.testclient import TestClient
from app.crypto import lots_key
from app.main import app

client = TestClient(app)


def test_test_vector_2_drawing_of_lots():
    """Verify drawing of lots deterministic hash keys against Appendix A Test Vector 2."""
    seed = 42
    league_id = "lg-1"
    k1 = lots_key(seed, league_id, "t1")
    k2 = lots_key(seed, league_id, "t2")
    k3 = lots_key(seed, league_id, "t3")

    assert k1 == "0613316991ce0ac31e88d6003e3ff4d5e21bb072ac5f81b42c0cdc6598453293"
    assert k2 == "e3e3a14e22727f936e1f288cf5d02a8a9362b1da13c5432725fc10b2c7955dd9"
    assert k3 == "c8f28e3c2f1eb6c4f636b4f57050e3362a2b39c07fda9b61742a26dd20397028"


def test_standings_computation():
    client.post("/audit/v1/reset", json={})
    # Register league
    resp = client.post("/audit/v1/leagues", json={
        "league_id": "lg-test",
        "sport_id": "football",
        "teams": ["t1", "t2", "t3", "t4"],
        "fixtures": [
            {"match_id": "m1", "home": "t1", "away": "t2"},
            {"match_id": "m2", "home": "t3", "away": "t4"},
        ],
        "points": {"win": 3, "draw": 1, "loss": 0},
        "qualification": {"spots": 2},
        "lots_seed": 42,
    })
    assert resp.status_code == 201

    # Start and score m1
    client.post("/audit/v1/events", json={
        "event_id": "evt-s-m1",
        "match_id": "m1",
        "type": "match_start",
        "payload": {},
    })
    client.post("/audit/v1/events", json={
        "event_id": "evt-score-m1",
        "match_id": "m1",
        "type": "score",
        "payload": {"team_id": "t1", "event_type": "goal"},
    })
    client.post("/audit/v1/events", json={
        "event_id": "evt-end-m1",
        "match_id": "m1",
        "type": "match_end",
        "payload": {},
    })

    # Fetch standings
    st_resp = client.get("/audit/v1/standings/lg-test")
    assert st_resp.status_code == 200
    data = st_resp.json()
    assert data["league_id"] == "lg-test"
    assert len(data["table"]) == 4
    # t1 should be rank 1 with 3 points
    assert data["table"][0]["team_id"] == "t1"
    assert data["table"][0]["points"] == 3
