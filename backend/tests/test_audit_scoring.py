"""Unit tests for Event-Sourced Scoring & Mystery Sport per Section 5.6, 5.9, and Appendix A."""
import os
import pytest
from fastapi.testclient import TestClient
from app.crypto import canonical, sign
from app.main import app

client = TestClient(app)


def test_test_vector_1_signature():
    """Verify exact signature against Appendix A Test Vector 1."""
    salt = "demo-salt"
    id_ = "evt-1"
    payload = {"team_id": "t1", "event_type": "goal"}
    can = canonical(payload)
    assert can == '{"event_type":"goal","team_id":"t1"}'
    sig = sign(salt, id_, payload)
    assert sig == "972a8b558690b19121cc5bea84978f85e8eb15a3735018db36616bab1d7ec501"


def test_mystery_sport_creation():
    client.post("/audit/v1/reset", json={})
    resp = client.post("/audit/v1/sports", json={
        "sport_id": "kabaddi",
        "name": "Kabaddi",
        "scoring_model": "event",
        "periods": {"count": 2, "duration_minutes": 20},
        "scoring_events": {
            "raid_point": {"points": 1},
            "tackle_point": {"points": 1},
            "all_out": {"points": 2},
        },
        "draw_allowed": False,
        "overtime": {"policy": "golden_score", "duration_minutes": 5},
        "tie_break_order": ["h2h_points", "h2h_diff", "overall_diff", "scored", "fair_play", "draw_lots"],
        "roster": {
            "min_squad_size": 7,
            "max_squad_size": 12,
            "required_positions": {"raider": 2, "defender": 3},
        },
    })
    assert resp.status_code == 201
    assert resp.json()["sport_id"] == "kabaddi"


def test_event_stream_and_compensation():
    client.post("/audit/v1/reset", json={})
    # 1. Match Init
    resp = client.post("/audit/v1/events", json={
        "event_id": "evt-init-test",
        "match_id": "match-test-1",
        "type": "match_init",
        "payload": {
            "sport_id": "football",
            "home_team_id": "team-a",
            "away_team_id": "team-b",
        },
    })
    assert resp.status_code == 201

    # 2. Match Start
    resp = client.post("/audit/v1/events", json={
        "event_id": "evt-start-test",
        "match_id": "match-test-1",
        "type": "match_start",
        "payload": {},
    })
    assert resp.status_code == 201

    # 3. Score
    resp = client.post("/audit/v1/events", json={
        "event_id": "evt-score-1",
        "match_id": "match-test-1",
        "type": "score",
        "payload": {"team_id": "team-a", "event_type": "goal"},
    })
    assert resp.status_code == 201

    # Check score before compensation
    score_resp = client.get("/audit/v1/score/match-test-1")
    assert score_resp.status_code == 200
    assert score_resp.json()["home"]["score"] == 1

    # 4. Compensating event for disallowed goal
    resp = client.post("/audit/v1/events", json={
        "event_id": "evt-comp-1",
        "match_id": "match-test-1",
        "type": "compensation",
        "payload": {"compensates": "evt-score-1", "reason": "Offside disallowed"},
    })
    assert resp.status_code == 201

    # Check score after compensation -> score returns to 0
    score_resp = client.get("/audit/v1/score/match-test-1")
    assert score_resp.status_code == 200
    assert score_resp.json()["home"]["score"] == 0
