"""Multi-sport taxonomy and mystery-sport registration per Section 5.6."""
import re
from typing import Any, Dict, List
from app.errors import AppException, validation_error
from app.state import state


SPORT_ID_REGEX = re.compile(r"^[a-z0-9_-]{2,40}$")
EVENT_KEY_REGEX = re.compile(r"^[a-z0-9_]{1,40}$")
VALID_SCORING_MODELS = {"event", "innings", "round"}
VALID_OVERTIME_POLICIES = {"none", "extra_time", "shootout", "golden_score", "super_over"}
VALID_TIE_BREAKS = ["h2h_points", "h2h_diff", "overall_diff", "scored", "fair_play", "draw_lots"]


def validate_and_create_sport(body: Dict[str, Any]) -> Dict[str, Any]:
    bad_fields: List[str] = []

    # sport_id
    sport_id = body.get("sport_id")
    if not isinstance(sport_id, str) or not SPORT_ID_REGEX.match(sport_id):
        bad_fields.append("sport_id")

    # name
    name = body.get("name")
    if not isinstance(name, str) or len(name) < 1 or len(name) > 80:
        bad_fields.append("name")

    # scoring_model
    scoring_model = body.get("scoring_model")
    if scoring_model not in VALID_SCORING_MODELS:
        bad_fields.append("scoring_model")

    # periods
    periods = body.get("periods")
    if not isinstance(periods, dict):
        bad_fields.append("periods")
    else:
        if scoring_model == "event":
            count = periods.get("count")
            duration = periods.get("duration_minutes")
            if not isinstance(count, int) or count < 1 or isinstance(count, bool):
                bad_fields.append("periods.count")
            if not isinstance(duration, (int, float)) or duration < 1:
                bad_fields.append("periods.duration_minutes")
        elif scoring_model == "innings":
            for field in ["innings_per_team", "overs_per_innings", "balls_per_over", "wickets_per_innings"]:
                val = periods.get(field)
                if not isinstance(val, int) or val < 1 or isinstance(val, bool):
                    bad_fields.append(f"periods.{field}")
        elif scoring_model == "round":
            best_of = periods.get("best_of")
            if not isinstance(best_of, int) or best_of < 1 or best_of % 2 == 0 or isinstance(best_of, bool):
                bad_fields.append("periods.best_of")

    # scoring_events
    scoring_events = body.get("scoring_events")
    if not isinstance(scoring_events, dict) or len(scoring_events) < 1:
        bad_fields.append("scoring_events")
    else:
        for k, v in scoring_events.items():
            if not isinstance(k, str) or not EVENT_KEY_REGEX.match(k) or not isinstance(v, dict):
                bad_fields.append(f"scoring_events.{k}")
                continue
            if scoring_model == "event":
                pts = v.get("points")
                if not isinstance(pts, int) or pts < 1 or isinstance(pts, bool):
                    bad_fields.append(f"scoring_events.{k}.points")
            elif scoring_model == "innings":
                runs = v.get("runs")
                legal = v.get("legal_ball")
                wicket = v.get("wicket")
                if not isinstance(runs, int) or runs < 0 or isinstance(runs, bool):
                    bad_fields.append(f"scoring_events.{k}.runs")
                if not isinstance(legal, bool):
                    bad_fields.append(f"scoring_events.{k}.legal_ball")
                if not isinstance(wicket, bool):
                    bad_fields.append(f"scoring_events.{k}.wicket")
            elif scoring_model == "round":
                rounds = v.get("rounds")
                if not isinstance(rounds, int) or rounds < 1 or isinstance(rounds, bool):
                    bad_fields.append(f"scoring_events.{k}.rounds")

    # draw_allowed
    draw_allowed = body.get("draw_allowed")
    if not isinstance(draw_allowed, bool):
        bad_fields.append("draw_allowed")

    # overtime
    overtime = body.get("overtime")
    if not isinstance(overtime, dict) or overtime.get("policy") not in VALID_OVERTIME_POLICIES:
        bad_fields.append("overtime")
    elif "duration_minutes" in overtime:
        dur = overtime.get("duration_minutes")
        if not isinstance(dur, (int, float)) or dur < 0:
            bad_fields.append("overtime.duration_minutes")

    # tie_break_order
    tie_break_order = body.get("tie_break_order")
    if tie_break_order is not None:
        if not isinstance(tie_break_order, list):
            bad_fields.append("tie_break_order")
        else:
            seen = set()
            for item in tie_break_order:
                if item not in VALID_TIE_BREAKS or item in seen:
                    bad_fields.append("tie_break_order")
                    break
                seen.add(item)

    # roster
    roster = body.get("roster")
    if not isinstance(roster, dict):
        bad_fields.append("roster")
    else:
        min_sq = roster.get("min_squad_size")
        max_sq = roster.get("max_squad_size")
        req_pos = roster.get("required_positions")
        if not isinstance(min_sq, int) or min_sq < 1 or isinstance(min_sq, bool):
            bad_fields.append("roster.min_squad_size")
        if not isinstance(max_sq, int) or max_sq < 1 or isinstance(max_sq, bool):
            bad_fields.append("roster.max_squad_size")
        if isinstance(min_sq, int) and isinstance(max_sq, int) and min_sq > max_sq:
            bad_fields.append("roster.min_squad_size")
        if not isinstance(req_pos, dict):
            bad_fields.append("roster.required_positions")
        else:
            for pos, count in req_pos.items():
                if not isinstance(pos, str) or not isinstance(count, int) or count < 0 or isinstance(count, bool):
                    bad_fields.append(f"roster.required_positions.{pos}")

    if bad_fields:
        raise validation_error("Validation failed for sport creation.", fields=bad_fields)

    with state.lock:
        if sport_id in state.sports:
            raise AppException(
                status_code=409,
                code="SPORT_EXISTS",
                message=f"Sport {sport_id} already exists.",
                details={"sport_id": sport_id},
            )

        # Normalize tie_break_order: default is full list, draw_lots is always last
        tb_order = list(tie_break_order) if tie_break_order is not None else list(VALID_TIE_BREAKS)
        if "draw_lots" in tb_order:
            tb_order.remove("draw_lots")
        tb_order.append("draw_lots")

        stored_config = {
            "sport_id": sport_id,
            "name": name,
            "scoring_model": scoring_model,
            "periods": periods,
            "scoring_events": scoring_events,
            "draw_allowed": draw_allowed,
            "overtime": overtime,
            "tie_break_order": tb_order,
            "roster": roster,
        }
        state.sports[sport_id] = stored_config

        return {
            "sport_id": sport_id,
            "status": "created",
            "config": stored_config,
        }
