"""Event-sourced scoring engine per Section 5.8 and 5.9.
Append-only log, compensating events rollback, zero hard-coded sport names.
"""
from typing import Any, Dict, List, Optional, Tuple
from app.crypto import canonical, get_salt, sign
from app.errors import AppException, validation_error
from app.state import state


def register_league(body: Dict[str, Any]) -> Dict[str, Any]:
    league_id = body.get("league_id")
    sport_id = body.get("sport_id")
    teams = body.get("teams")
    fixtures = body.get("fixtures")

    bad_fields = []
    if not isinstance(league_id, str) or not league_id:
        bad_fields.append("league_id")
    if not isinstance(sport_id, str) or not sport_id:
        bad_fields.append("sport_id")
    if not isinstance(teams, list) or len(teams) < 2 or len(teams) > 40 or len(set(teams)) != len(teams):
        bad_fields.append("teams")
    if not isinstance(fixtures, list) or len(fixtures) < 1:
        bad_fields.append("fixtures")
    else:
        teams_set = set(teams) if isinstance(teams, list) else set()
        for f in fixtures:
            if not isinstance(f, dict):
                bad_fields.append("fixtures")
                break
            mid = f.get("match_id")
            h = f.get("home")
            a = f.get("away")
            if not mid or not isinstance(mid, str):
                bad_fields.append("fixtures.match_id")
            if h not in teams_set or a not in teams_set or h == a:
                bad_fields.append("fixtures.teams")

    qual = body.get("qualification")
    if not isinstance(qual, dict) or not isinstance(qual.get("spots"), int) or qual["spots"] < 1:
        bad_fields.append("qualification.spots")
    elif isinstance(teams, list) and qual["spots"] > len(teams):
        bad_fields.append("qualification.spots")

    if bad_fields:
        raise validation_error("Validation failed for league registration.", fields=bad_fields)

    with state.lock:
        if sport_id not in state.sports:
            raise AppException(
                status_code=404,
                code="SPORT_NOT_FOUND",
                message=f"Sport {sport_id} not found.",
                details={"sport_id": sport_id},
            )
        if league_id in state.leagues:
            raise AppException(
                status_code=409,
                code="LEAGUE_EXISTS",
                message=f"League {league_id} already exists.",
                details={"league_id": league_id},
            )

        for f in fixtures:
            mid = f["match_id"]
            if mid in state.matches:
                raise AppException(
                    status_code=409,
                    code="MATCH_EXISTS",
                    message=f"Match {mid} already exists.",
                    details={"match_id": mid},
                )

        sport_cfg = state.sports[sport_id]
        points_cfg = body.get("points") or {"win": 3, "draw": 1, "loss": 0}
        tb_order = body.get("tie_break_order") or list(sport_cfg.get("tie_break_order", []))
        lots_seed = body.get("lots_seed", state.seed)

        state.leagues[league_id] = {
            "league_id": league_id,
            "sport_id": sport_id,
            "teams": teams,
            "fixtures": fixtures,
            "points": points_cfg,
            "tie_break_order": tb_order,
            "qualification": qual,
            "lots_seed": lots_seed,
        }

        # Initialize match streams
        salt = get_salt()
        for f in fixtures:
            mid = f["match_id"]
            home_t = f["home"]
            away_t = f["away"]
            state.matches[mid] = {
                "match_id": mid,
                "sport_id": sport_id,
                "league_id": league_id,
                "home_team_id": home_t,
                "away_team_id": away_t,
                "status": "upcoming",
            }
            # Automatic match_init event
            init_payload = {
                "sport_id": sport_id,
                "home_team_id": home_t,
                "away_team_id": away_t,
                "league_id": league_id,
            }
            init_evt_id = f"evt-init-{mid}"
            sig = sign(salt, init_evt_id, init_payload)
            state.match_events[mid] = [
                {
                    "sequence": 1,
                    "event_id": init_evt_id,
                    "type": "match_init",
                    "payload": init_payload,
                    "signature": sig,
                    "compensated": False,
                    "compensated_by": None,
                }
            ]

        return {
            "league_id": league_id,
            "status": "created",
            "team_count": len(teams),
            "fixture_count": len(fixtures),
        }


def append_event(body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    event_id = body.get("event_id")
    match_id = body.get("match_id")
    evt_type = body.get("type")
    payload = body.get("payload")

    if not event_id or not isinstance(event_id, str):
        raise validation_error("Missing or invalid event_id.", fields=["event_id"])
    if not match_id or not isinstance(match_id, str):
        raise validation_error("Missing or invalid match_id.", fields=["match_id"])
    if not evt_type or not isinstance(evt_type, str):
        raise validation_error("Missing or invalid type.", fields=["type"])
    if not isinstance(payload, dict):
        raise validation_error("Missing or invalid payload.", fields=["payload"])

    with state.lock:
        # Check idempotency first
        if event_id in state.event_responses:
            stored = state.event_responses[event_id]
            if canonical(stored["body"]) == canonical(body):
                return 200, stored["response"]
            raise AppException(
                status_code=409,
                code="DUPLICATE_EVENT_ID",
                message=f"Event {event_id} already exists with a different body.",
                details={"event_id": event_id},
            )

        if evt_type == "match_init":
            if match_id in state.matches:
                raise AppException(
                    status_code=409,
                    code="MATCH_EXISTS",
                    message=f"Match {match_id} already exists.",
                    details={"match_id": match_id},
                )
            sport_id = payload.get("sport_id")
            if sport_id not in state.sports:
                raise AppException(
                    status_code=404,
                    code="SPORT_NOT_FOUND",
                    message=f"Sport {sport_id} not found.",
                    details={"sport_id": sport_id},
                )
            h = payload.get("home_team_id")
            a = payload.get("away_team_id")
            if not h or not a or h == a:
                raise validation_error("Invalid home or away team.", fields=["payload"])

            state.matches[match_id] = {
                "match_id": match_id,
                "sport_id": sport_id,
                "league_id": payload.get("league_id"),
                "home_team_id": h,
                "away_team_id": a,
                "status": "upcoming",
            }
            state.match_events[match_id] = []
        else:
            if match_id not in state.matches:
                raise AppException(
                    status_code=404,
                    code="MATCH_NOT_FOUND",
                    message=f"Match {match_id} not found.",
                    details={"match_id": match_id},
                )

        match = state.matches[match_id]
        sport = state.sports[match["sport_id"]]
        events_log = state.match_events[match_id]

        # Project current match state from events log to validate transitions and limits
        proj = project_score(match_id)
        current_status = proj["status"]

        if evt_type == "match_start":
            if current_status != "upcoming":
                raise AppException(
                    status_code=409,
                    code="ILLEGAL_TRANSITION",
                    message=f"Match status is {current_status}, cannot transition to in_progress.",
                    details={"current_status": current_status},
                )
        elif evt_type == "score":
            if current_status != "in_progress":
                raise AppException(
                    status_code=409,
                    code="MATCH_NOT_IN_PROGRESS",
                    message=f"Match is not in progress (current status: {current_status}).",
                    details={"current_status": current_status},
                )
            team_id = payload.get("team_id")
            if team_id not in [match["home_team_id"], match["away_team_id"]]:
                raise validation_error(f"Team {team_id} is not in match {match_id}.", fields=["payload.team_id"])
            
            event_type = payload.get("event_type")
            scoring_events = sport.get("scoring_events", {})
            if event_type not in scoring_events:
                raise AppException(
                    status_code=400,
                    code="UNKNOWN_EVENT_TYPE",
                    message=f"Unknown scoring event {event_type} for sport {match['sport_id']}.",
                    details={"event_type": event_type},
                )

            # Check model limits
            scoring_model = sport.get("scoring_model")
            periods = sport.get("periods", {})
            if scoring_model == "innings":
                # Check team balls and wickets
                t_stat = proj["home"] if team_id == match["home_team_id"] else proj["away"]
                max_balls = periods.get("innings_per_team", 1) * periods.get("overs_per_innings", 20) * periods.get("balls_per_over", 6)
                max_wickets = periods.get("innings_per_team", 1) * periods.get("wickets_per_innings", 10)
                if (t_stat["balls"] is not None and t_stat["balls"] >= max_balls) or \
                   (t_stat["wickets"] is not None and t_stat["wickets"] >= max_wickets):
                    raise AppException(
                        status_code=409,
                        code="INNINGS_COMPLETE",
                        message=f"Innings complete for team {team_id}.",
                        details={"team_id": team_id},
                    )
            elif scoring_model == "round":
                best_of = periods.get("best_of", 3)
                target = (best_of + 1) // 2
                t_stat = proj["home"] if team_id == match["home_team_id"] else proj["away"]
                if t_stat["score"] >= target:
                    raise AppException(
                        status_code=409,
                        code="SERIES_ALREADY_DECIDED",
                        message=f"Series already decided. Team {team_id} has won {t_stat['score']} rounds.",
                        details={"team_id": team_id},
                    )

        elif evt_type == "discipline":
            if current_status != "in_progress":
                raise AppException(
                    status_code=409,
                    code="MATCH_NOT_IN_PROGRESS",
                    message="Discipline events only allowed when match is in progress.",
                    details={"current_status": current_status},
                )
            team_id = payload.get("team_id")
            if team_id not in [match["home_team_id"], match["away_team_id"]]:
                raise validation_error(f"Team {team_id} is not in match.", fields=["payload.team_id"])
            if not isinstance(payload.get("points"), int) or isinstance(payload.get("points"), bool):
                raise validation_error("Points must be an integer.", fields=["payload.points"])

        elif evt_type == "tiebreak_winner":
            if current_status != "in_progress":
                raise AppException(
                    status_code=409,
                    code="MATCH_NOT_IN_PROGRESS",
                    message="Tiebreak winner can only be declared when match is in progress.",
                    details={"current_status": current_status},
                )
            team_id = payload.get("team_id")
            if team_id not in [match["home_team_id"], match["away_team_id"]]:
                raise validation_error(f"Team {team_id} is not in match.", fields=["payload.team_id"])

        elif evt_type == "match_end":
            if current_status != "in_progress":
                raise AppException(
                    status_code=409,
                    code="ILLEGAL_TRANSITION",
                    message=f"Cannot end match with status {current_status}.",
                    details={"current_status": current_status},
                )
            # If score is level, draw_allowed is false, and no active tiebreak_winner -> 409 TIE_NOT_ALLOWED
            if proj["home"]["score"] == proj["away"]["score"] and not sport.get("draw_allowed", True):
                if not proj.get("tiebreak_winner_team_id"):
                    raise AppException(
                        status_code=409,
                        code="TIE_NOT_ALLOWED",
                        message="Match ended level, draw is not allowed, and no active tiebreak winner exists.",
                        details={"match_id": match_id},
                    )

        elif evt_type == "compensation":
            comp_id = payload.get("compensates")
            if not comp_id:
                raise validation_error("Missing compensates target event_id.", fields=["payload.compensates"])
            
            # Find the target event in this match
            target_evt = None
            for e in events_log:
                if e["event_id"] == comp_id:
                    target_evt = e
                    break
            
            if not target_evt:
                # Check if it belongs to another match or does not exist
                found_other = False
                for other_mid, other_evts in state.match_events.items():
                    if other_mid != match_id and any(oe["event_id"] == comp_id for oe in other_evts):
                        found_other = True
                        break
                if found_other:
                    raise AppException(
                        status_code=409,
                        code="INVALID_COMPENSATION",
                        message=f"Event {comp_id} belongs to another match.",
                        details={"compensates": comp_id},
                    )
                raise AppException(
                    status_code=404,
                    code="EVENT_NOT_FOUND",
                    message=f"Target event {comp_id} not found.",
                    details={"event_id": comp_id},
                )

            if target_evt["type"] not in ["score", "discipline", "tiebreak_winner"]:
                raise AppException(
                    status_code=409,
                    code="INVALID_COMPENSATION",
                    message=f"Cannot compensate event type {target_evt['type']}.",
                    details={"event_id": comp_id, "type": target_evt["type"]},
                )

            if target_evt["compensated"]:
                raise AppException(
                    status_code=409,
                    code="INVALID_COMPENSATION",
                    message=f"Event {comp_id} is already compensated.",
                    details={"event_id": comp_id},
                )

            # Mark target event as compensated
            target_evt["compensated"] = True
            target_evt["compensated_by"] = event_id

        # Append to log
        salt = get_salt()
        sig = sign(salt, event_id, payload)
        seq = len(events_log) + 1
        new_event = {
            "sequence": seq,
            "event_id": event_id,
            "type": evt_type,
            "payload": payload,
            "signature": sig,
            "compensated": False,
            "compensated_by": None,
        }
        events_log.append(new_event)

        resp = {
            "event_id": event_id,
            "match_id": match_id,
            "type": evt_type,
            "sequence": seq,
            "match_version": seq,
            "signature": sig,
        }
        state.event_responses[event_id] = {"body": body, "response": resp}
        return 201, resp


def project_score(match_id: str) -> Dict[str, Any]:
    with state.lock:
        if match_id not in state.matches:
            raise AppException(
                status_code=404,
                code="MATCH_NOT_FOUND",
                message=f"Match {match_id} not found.",
                details={"match_id": match_id},
            )
        match = state.matches[match_id]
        sport = state.sports[match["sport_id"]]
        events = state.match_events.get(match_id, [])

    home_id = match["home_team_id"]
    away_id = match["away_team_id"]
    scoring_model = sport.get("scoring_model")
    scoring_events_cfg = sport.get("scoring_events", {})
    periods_cfg = sport.get("periods", {})
    bpo = periods_cfg.get("balls_per_over", 6)

    # Initialize stats
    is_innings = (scoring_model == "innings")
    home_stats = {
        "team_id": home_id,
        "score": 0,
        "wickets": 0 if is_innings else None,
        "balls": 0 if is_innings else None,
        "overs": "0.0" if is_innings else None,
        "fair_play": 0,
    }
    away_stats = {
        "team_id": away_id,
        "score": 0,
        "wickets": 0 if is_innings else None,
        "balls": 0 if is_innings else None,
        "overs": "0.0" if is_innings else None,
        "fair_play": 0,
    }

    status = "upcoming"
    tiebreak_winner_team = None

    for evt in events:
        if evt["compensated"]:
            continue
        etype = evt["type"]
        epayload = evt["payload"]

        if etype == "match_start":
            status = "in_progress"
        elif etype == "match_end":
            status = "completed"
        elif etype == "tiebreak_winner":
            tiebreak_winner_team = epayload.get("team_id")
        elif etype == "discipline":
            tid = epayload.get("team_id")
            pts = epayload.get("points", 0)
            if tid == home_id:
                home_stats["fair_play"] += pts
            elif tid == away_id:
                away_stats["fair_play"] += pts
        elif etype == "score":
            tid = epayload.get("team_id")
            event_type = epayload.get("event_type")
            cfg = scoring_events_cfg.get(event_type, {})
            t_obj = home_stats if tid == home_id else away_stats

            if scoring_model == "event":
                t_obj["score"] += cfg.get("points", 0)
            elif scoring_model == "innings":
                t_obj["score"] += cfg.get("runs", 0)
                if cfg.get("legal_ball", False):
                    t_obj["balls"] += 1
                if cfg.get("wicket", False):
                    t_obj["wickets"] += 1
            elif scoring_model == "round":
                t_obj["score"] += cfg.get("rounds", 0)

    # Update overs string for innings
    if is_innings:
        home_b = home_stats["balls"]
        away_b = away_stats["balls"]
        home_stats["overs"] = f"{home_b // bpo}.{home_b % bpo}"
        away_stats["overs"] = f"{away_b // bpo}.{away_b % bpo}"

    # Determine outcome & winner
    outcome = "pending"
    winner_team_id = None
    if status == "completed":
        h_score = home_stats["score"]
        a_score = away_stats["score"]
        if h_score > a_score:
            outcome = "home_win"
            winner_team_id = home_id
        elif a_score > h_score:
            outcome = "away_win"
            winner_team_id = away_id
        else:
            if tiebreak_winner_team:
                winner_team_id = tiebreak_winner_team
                outcome = "home_win" if tiebreak_winner_team == home_id else "away_win"
            elif sport.get("draw_allowed", True):
                outcome = "draw"
                winner_team_id = None
            else:
                outcome = "undecided"
                winner_team_id = None

    return {
        "match_id": match_id,
        "sport_id": match["sport_id"],
        "league_id": match.get("league_id"),
        "status": status,
        "outcome": outcome,
        "winner_team_id": winner_team_id,
        "tiebreak_winner_team_id": tiebreak_winner_team,
        "home": home_stats,
        "away": away_stats,
        "version": len(events),
        "events": events,
    }
