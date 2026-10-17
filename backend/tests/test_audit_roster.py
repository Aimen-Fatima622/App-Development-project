"""Unit tests for Roster, Transfers, Loans, History, and Edge Case 6."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_roster_transfer_and_in_progress_match():
    client.post("/audit/v1/reset", json={})

    # Setup scenario with in-progress match
    setup_resp = client.post("/audit/v1/roster/setup", json={
        "league": {
            "league_id": "lg-r1",
            "tenant_id": "tenant-alpha",
            "sport_id": "football",
            "transfer_window": {"open": "2026-09-01", "close": "2026-09-30"},
            "max_squad_size": 5,
            "required_positions": {"gk": 1},
        },
        "squads": [
            {"squad_id": "sq-a", "club_id": "club-a", "tenant_id": "tenant-alpha", "name": "A"},
            {"squad_id": "sq-b", "club_id": "club-b", "tenant_id": "tenant-alpha", "name": "B"},
        ],
        "players": [
            {"player_id": "p1", "name": "Ali", "position": "gk", "squad_id": "sq-a", "role": "captain"},
            {"player_id": "p2", "name": "Bilal", "position": "df", "squad_id": "sq-a", "role": "starter"},
            {"player_id": "p3", "name": "Hassan", "position": "gk", "squad_id": "sq-a", "role": "substitute"},
        ],
        "matches_in_progress": [
            {"match_id": "m-live", "home_squad_id": "sq-a", "away_squad_id": "sq-b"}
        ],
    })
    assert setup_resp.status_code == 201

    # Transfer player p2 during in-progress match -> state: deferred_until_match_end
    tr_resp = client.post("/audit/v1/roster/transfer", json={
        "request_id": "tr-001",
        "league_id": "lg-r1",
        "player_id": "p2",
        "type": "transfer",
        "from_squad_id": "sq-a",
        "to_squad_id": "sq-b",
        "effective_date": "2026-09-30",
        "loan_end_date": None,
        "reason": "Tactical move",
        "requested_by": "user-77",
    })
    assert tr_resp.status_code == 201
    data = tr_resp.json()
    assert data["state"] == "deferred_until_match_end"
    assert data["blocking_match_id"] == "m-live"


def test_loan_auto_return():
    client.post("/audit/v1/reset", json={})
    client.post("/audit/v1/roster/setup", json={
        "league": {
            "league_id": "lg-r1",
            "tenant_id": "tenant-alpha",
            "sport_id": "football",
            "transfer_window": {"open": "2026-01-01", "close": "2026-12-31"},
            "max_squad_size": 10,
            "required_positions": {},
        },
        "squads": [
            {"squad_id": "sq-a", "club_id": "club-a", "tenant_id": "tenant-alpha"},
            {"squad_id": "sq-b", "club_id": "club-b", "tenant_id": "tenant-alpha"},
        ],
        "players": [
            {"player_id": "p1", "name": "Ali", "position": "df", "squad_id": "sq-a", "role": "starter"},
        ],
        "matches_in_progress": [],
    })

    # Loan player p1 from sq-a to sq-b until 2026-10-01
    client.post("/audit/v1/roster/transfer", json={
        "request_id": "tr-loan-1",
        "league_id": "lg-r1",
        "player_id": "p1",
        "type": "loan",
        "from_squad_id": "sq-a",
        "to_squad_id": "sq-b",
        "effective_date": "2026-06-01",
        "loan_end_date": "2026-10-01",
        "reason": "Development loan",
        "requested_by": "user-1",
    })

    # Check history with as_of after loan_end_date
    hist_resp = client.get("/audit/v1/roster/history/p1?as_of=2026-10-05")
    assert hist_resp.status_code == 200
    h_data = hist_resp.json()
    assert h_data["current_squad_id"] == "sq-a"
    actions = [e["action"] for e in h_data["history"]]
    assert "loan_return" in actions
