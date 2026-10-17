"""Roster management, transfers, loans, and audit history per Section 5.11 and edge case 6."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from app.crypto import canonical
from app.errors import AppException, validation_error
from app.state import state


def setup_roster(body: Dict[str, Any]) -> Dict[str, Any]:
    league_cfg = body.get("league")
    squads_cfg = body.get("squads")
    players_cfg = body.get("players")
    matches_in_progress = body.get("matches_in_progress", [])

    bad_fields = []
    if not isinstance(league_cfg, dict):
        bad_fields.append("league")
    if not isinstance(squads_cfg, list):
        bad_fields.append("squads")
    if not isinstance(players_cfg, list):
        bad_fields.append("players")

    if bad_fields:
        raise validation_error("Validation failed for roster setup.", fields=bad_fields)

    league_id = league_cfg.get("league_id")
    tenant_id = league_cfg.get("tenant_id")
    sport_id = league_cfg.get("sport_id")

    if not league_id or not tenant_id or not sport_id:
        raise validation_error("Missing required league fields.", fields=["league"])

    with state.lock:
        sport = state.sports.get(sport_id, {})
        sport_roster = sport.get("roster", {})
        max_squad = league_cfg.get("max_squad_size", sport_roster.get("max_squad_size", 25))
        req_pos = league_cfg.get("required_positions", sport_roster.get("required_positions", {}))

        # Store league roster config
        state.roster_leagues[league_id] = {
            "league_id": league_id,
            "tenant_id": tenant_id,
            "sport_id": sport_id,
            "transfer_window": league_cfg.get("transfer_window", {"open": "2026-01-01", "close": "2026-12-31"}),
            "max_squad_size": max_squad,
            "required_positions": req_pos,
            "matches_in_progress": matches_in_progress,
        }

        squad_counts: Dict[str, int] = {}
        for sq in squads_cfg:
            sq_id = sq["squad_id"]
            state.squads[sq_id] = {
                "squad_id": sq_id,
                "club_id": sq.get("club_id"),
                "tenant_id": sq.get("tenant_id", tenant_id),
                "name": sq.get("name"),
                "league_id": league_id,
            }
            squad_counts[sq_id] = 0

        for p in players_cfg:
            p_id = p["player_id"]
            sq_id = p.get("squad_id")
            if sq_id and sq_id in squad_counts:
                squad_counts[sq_id] += 1
            
            p_obj = {
                "player_id": p_id,
                "name": p.get("name"),
                "position": p.get("position"),
                "squad_id": sq_id,
                "parent_squad_id": None,
                "role": p.get("role", "starter"),
                "league_id": league_id,
                "on_loan": False,
                "loan_end_date": None,
            }
            state.players[p_id] = p_obj
            # Clear or init history
            state.roster_history[p_id] = []

        return {
            "league_id": league_id,
            "status": "configured",
            "squad_counts": squad_counts,
        }


def process_transfer(body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    req_id = body.get("request_id")
    league_id = body.get("league_id")
    player_id = body.get("player_id")
    action_type = body.get("type")
    from_sq_id = body.get("from_squad_id")
    to_sq_id = body.get("to_squad_id")
    eff_date = body.get("effective_date")
    loan_end = body.get("loan_end_date")
    reason = body.get("reason", "")
    who = body.get("requested_by", "system")

    # Rule Check 1: Schema, dates, loan_end_date > effective_date, to_squad_id present unless release
    bad_fields = []
    if not req_id or not isinstance(req_id, str):
        bad_fields.append("request_id")
    if not league_id or not isinstance(league_id, str):
        bad_fields.append("league_id")
    if not player_id or not isinstance(player_id, str):
        bad_fields.append("player_id")
    if action_type not in ["transfer", "loan", "release"]:
        bad_fields.append("type")
    if not eff_date or not isinstance(eff_date, str):
        bad_fields.append("effective_date")

    if action_type in ["transfer", "loan"]:
        if not to_sq_id or not isinstance(to_sq_id, str):
            bad_fields.append("to_squad_id")

    if action_type == "loan":
        if not loan_end or not isinstance(loan_end, str):
            bad_fields.append("loan_end_date")
        elif eff_date and loan_end <= eff_date:
            bad_fields.append("loan_end_date")

    if bad_fields:
        raise validation_error("Validation failed for roster transfer.", fields=bad_fields)

    with state.lock:
        # Check idempotency
        if req_id in state.transfer_responses:
            stored = state.transfer_responses[req_id]
            if canonical(stored["body"]) == canonical(body):
                return 200, stored["response"]
            raise AppException(
                status_code=409,
                code="DUPLICATE_ORDER_ID",
                message="Duplicate request ID with different body.",
                details={"request_id": req_id},
            )

        # Rule Check 2: League / player / squads exist
        if league_id not in state.roster_leagues and league_id not in state.leagues:
            raise AppException(
                status_code=404,
                code="LEAGUE_NOT_FOUND",
                message=f"League {league_id} not found.",
                details={"league_id": league_id},
            )
        if player_id not in state.players:
            raise AppException(
                status_code=404,
                code="PLAYER_NOT_FOUND",
                message=f"Player {player_id} not found.",
                details={"player_id": player_id},
            )
        if from_sq_id not in state.squads:
            raise AppException(
                status_code=404,
                code="SQUAD_NOT_FOUND",
                message=f"Squad {from_sq_id} not found.",
                details={"squad_id": from_sq_id},
            )
        if action_type in ["transfer", "loan"] and to_sq_id not in state.squads:
            raise AppException(
                status_code=404,
                code="SQUAD_NOT_FOUND",
                message=f"Squad {to_sq_id} not found.",
                details={"squad_id": to_sq_id},
            )

        league = state.roster_leagues.get(league_id, {})
        league_tenant = league.get("tenant_id", "tenant-alpha")
        from_sq = state.squads[from_sq_id]
        to_sq = state.squads.get(to_sq_id)
        player = state.players[player_id]

        # Rule Check 3: From and to squads belong to the league's tenant
        if from_sq.get("tenant_id") != league_tenant or (to_sq and to_sq.get("tenant_id") != league_tenant):
            raise AppException(
                status_code=409,
                code="CROSS_TENANT_TRANSFER",
                message="Cannot transfer across different tenants.",
                details={"league_tenant": league_tenant},
            )

        # Rule Check 4: Player's current squad in this league equals from_squad_id
        if player.get("squad_id") != from_sq_id:
            raise AppException(
                status_code=409,
                code="NOT_IN_SQUAD",
                message=f"Player {player_id} is in squad {player.get('squad_id')}, not {from_sq_id}.",
                details={"player_id": player_id, "current_squad_id": player.get("squad_id")},
            )

        # Rule Check 5: transfer/loan: effective_date inside window (inclusive). Release allowed on any date.
        if action_type in ["transfer", "loan"]:
            t_win = league.get("transfer_window", {})
            w_open = t_win.get("open", "1970-01-01")
            w_close = t_win.get("close", "2099-12-31")
            if not (w_open <= eff_date <= w_close):
                raise AppException(
                    status_code=409,
                    code="TRANSFER_WINDOW_CLOSED",
                    message="Effective date is outside the transfer window.",
                    details={"effective_date": eff_date, "window": t_win},
                )

        # Rule Check 6: Player is not currently on loan
        if player.get("on_loan", False):
            raise AppException(
                status_code=409,
                code="PLAYER_ON_LOAN",
                message=f"Player {player_id} is currently on loan.",
                details={"player_id": player_id},
            )

        # Rule Check 7: destination squad count + 1 <= max_squad_size
        max_squad = league.get("max_squad_size", 25)
        if action_type in ["transfer", "loan"]:
            dest_count = sum(1 for p in state.players.values() if p.get("squad_id") == to_sq_id)
            if dest_count + 1 > max_squad:
                raise AppException(
                    status_code=409,
                    code="SQUAD_FULL",
                    message=f"Destination squad {to_sq_id} is full ({dest_count}/{max_squad}).",
                    details={"squad_id": to_sq_id, "current_count": dest_count, "max_squad_size": max_squad},
                )

        # Rule Check 8: from squad still has >= required count for player's position
        req_positions = league.get("required_positions", {})
        pos = player.get("position")
        if pos and pos in req_positions:
            min_req = req_positions[pos]
            from_pos_count = sum(
                1 for p in state.players.values()
                if p.get("squad_id") == from_sq_id and p.get("position") == pos
            )
            if from_pos_count - 1 < min_req:
                raise AppException(
                    status_code=409,
                    code="MIN_POSITION_VIOLATION",
                    message=f"Transfer would violate minimum position count for {pos}.",
                    details={"position": pos, "remaining": from_pos_count - 1, "required": min_req},
                )

        # Check for in-progress match (Edge Case 6)
        in_progress_matches = league.get("matches_in_progress", [])
        blocking_match_id = None
        transfer_state = "active"
        for m in in_progress_matches:
            if from_sq_id in [m.get("home_squad_id"), m.get("away_squad_id")]:
                transfer_state = "deferred_until_match_end"
                blocking_match_id = m.get("match_id")
                break

        # Apply state changes
        audit_id = state.next_audit_id()
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        registration = None
        if action_type == "transfer":
            if transfer_state == "active":
                player["squad_id"] = to_sq_id
                player["role"] = "substitute"
            registration = {
                "player_id": player_id,
                "league_id": league_id,
                "squad_id": to_sq_id,
                "parent_squad_id": None,
                "registration_type": "transfer",
                "start_date": eff_date,
                "loan_end_date": None,
                "role": "substitute",
            }
        elif action_type == "loan":
            if transfer_state == "active":
                player["squad_id"] = to_sq_id
                player["parent_squad_id"] = from_sq_id
                player["on_loan"] = True
                player["loan_end_date"] = loan_end
                player["role"] = "substitute"
            registration = {
                "player_id": player_id,
                "league_id": league_id,
                "squad_id": to_sq_id,
                "parent_squad_id": from_sq_id,
                "registration_type": "loan",
                "start_date": eff_date,
                "loan_end_date": loan_end,
                "role": "substitute",
            }
        elif action_type == "release":
            if transfer_state == "active":
                player["squad_id"] = None
                player["role"] = "substitute"
            registration = None

        audit_entry = {
            "audit_id": audit_id,
            "action": action_type,
            "player_id": player_id,
            "league_id": league_id,
            "from_squad_id": from_sq_id,
            "to_squad_id": to_sq_id,
            "effective_date": eff_date,
            "state": transfer_state,
            "who": who,
            "when": now_str,
            "why": reason,
        }
        state.roster_history.setdefault(player_id, []).append(audit_entry)

        resp = {
            "request_id": req_id,
            "status": "accepted",
            "state": transfer_state,
            "blocking_match_id": blocking_match_id,
            "registration": registration,
            "audit_entry": audit_entry,
        }
        state.transfer_responses[req_id] = {"body": body, "response": resp}
        return 201, resp


def get_roster_history(player_id: str, as_of: Optional[str] = None) -> Dict[str, Any]:
    with state.lock:
        if player_id not in state.players:
            raise AppException(
                status_code=404,
                code="PLAYER_NOT_FOUND",
                message=f"Player {player_id} not found.",
                details={"player_id": player_id},
            )
        player = state.players[player_id]
        history = list(state.roster_history.get(player_id, []))
        league_id = player.get("league_id")

        if not as_of:
            as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Auto-return of loans: The day after loan_end_date the player is back with lender
        # Check if an active loan expired by as_of
        for entry in list(history):
            if entry["action"] == "loan":
                loan_end = entry.get("effective_date")  # or from loan registration
                # Find corresponding registration from responses
                loan_end_val = player.get("loan_end_date")
                if loan_end_val and as_of > loan_end_val:
                    # Check if loan_return already in history
                    has_return = any(h["action"] == "loan_return" for h in history)
                    if not has_return:
                        return_id = state.next_audit_id()
                        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                        ret_entry = {
                            "audit_id": return_id,
                            "action": "loan_return",
                            "player_id": player_id,
                            "league_id": league_id,
                            "from_squad_id": entry["to_squad_id"],
                            "to_squad_id": entry["from_squad_id"],
                            "effective_date": loan_end_val,
                            "state": "active",
                            "who": "system",
                            "when": now_str,
                            "why": "Automatic loan return",
                        }
                        history.append(ret_entry)
                        state.roster_history[player_id].append(ret_entry)
                        player["squad_id"] = entry["from_squad_id"]
                        player["parent_squad_id"] = None
                        player["on_loan"] = False
                        player["role"] = "substitute"

        return {
            "player_id": player_id,
            "as_of": as_of,
            "league_id": league_id,
            "current_squad_id": player.get("squad_id"),
            "parent_squad_id": player.get("parent_squad_id"),
            "history": history,
        }
