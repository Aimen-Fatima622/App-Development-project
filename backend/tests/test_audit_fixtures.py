"""Unit tests for Fixtures & Bracket generation per Section 5.7 and 9.3."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_round_robin_schedule():
    teams = ["t1", "t2", "t3", "t4", "t5"]
    resp = client.post("/audit/v1/fixtures", json={
        "format": "round_robin",
        "teams": teams,
        "params": {
            "legs": 1,
            "withdrawals": [{"team_id": "t3", "after_round": 2}],
            "withdrawal_policy": "forfeit_remaining",
        }
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "round_robin"
    assert data["legs"] == 1
    assert data["team_count"] == 5
    assert data["round_count"] == 5
    assert len(data["rounds"]) == 5
    assert data["summary"]["total"] == 10
    assert data["summary"]["forfeit"] > 0


def test_swiss_schedule():
    teams = ["t1", "t2", "t3", "t4", "t5"]
    resp = client.post("/audit/v1/fixtures", json={
        "format": "swiss",
        "teams": teams,
        "params": {
            "total_rounds": 3,
            "round": 2,
            "history": [
                {
                    "round": 1,
                    "bye": "t5",
                    "matches": [
                        {"home": "t1", "away": "t3", "result": "home"},
                        {"home": "t2", "away": "t4", "result": "draw"},
                    ],
                }
            ],
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "swiss"
    assert data["round"] == 2
    assert len(data["pairings"]) == 2
    assert data["bye"] is not None
    assert len(data["standings"]) == 5


def test_single_elimination():
    teams = ["t1", "t2", "t3", "t4", "t5", "t6"]
    resp = client.post("/audit/v1/fixtures", json={
        "format": "single_elim",
        "teams": teams,
        "params": {
            "third_place_match": True,
            "results": [{"match_id": "R1M2", "winner": "t4"}],
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "single_elim"
    assert data["bracket_size"] == 8
    # Match R1M2 winner should be t4
    r1_matches = data["rounds"][0]["matches"]
    r1m2 = next(m for m in r1_matches if m["match_id"] == "R1M2")
    assert r1m2["winner"] == "t4"


def test_double_elimination():
    teams = ["t1", "t2", "t3", "t4"]
    resp = client.post("/audit/v1/fixtures", json={
        "format": "double_elim",
        "teams": teams,
        "params": {
            "bracket_reset": True,
            "results": [
                {"match_id": "WR1M1", "winner": "t1"},
                {"match_id": "WR1M2", "winner": "t2"},
            ],
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "double_elim"
    assert "winners" in data
    assert "losers" in data
    assert "grand_final" in data
    gf2 = next((m for m in data["grand_final"] if m["match_id"] == "GF2"), None)
    assert gf2 is not None
    assert gf2["conditional"] is True
