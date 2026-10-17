"""Unit tests for Offline Sync and conflict resolution per Section 5.14."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_offline_sync():
    client.post("/audit/v1/reset", json={})

    # Setup match
    client.post("/audit/v1/events", json={
        "event_id": "evt-init-sync",
        "match_id": "sync-match-1",
        "type": "match_init",
        "payload": {
            "sport_id": "football",
            "home_team_id": "team-a",
            "away_team_id": "team-b",
        },
    })
    client.post("/audit/v1/events", json={
        "event_id": "evt-start-sync",
        "match_id": "sync-match-1",
        "type": "match_start",
        "payload": {},
    })

    # Replay offline sync with score event
    resp = client.post("/audit/v1/offline-sync", json={
        "device_id": "dev-001",
        "actions": [
            {
                "action_id": "act-1",
                "type": "score_event",
                "queued_at": "2026-10-17T11:00:00Z",
                "base_version": 2,
                "payload": {
                    "event_id": "evt-sync-score-1",
                    "match_id": "sync-match-1",
                    "type": "score",
                    "payload": {"team_id": "team-a", "event_type": "goal"},
                },
            }
        ],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["applied"] == 1
    assert data["results"][0]["status"] == "applied"
    assert data["results"][0]["resolution"] == "appended"
