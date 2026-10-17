"""Automated standings, H2H mini-league tie-breaker, differentials, and qualification calculations per Section 5.10."""
from typing import Any, Dict, List, Optional, Set, Tuple
from app.crypto import lots_key
from app.errors import AppException
from app.scoring import project_score
from app.state import state


def compute_standings(league_id: str) -> Dict[str, Any]:
    with state.lock:
        if league_id not in state.leagues:
            raise AppException(
                status_code=404,
                code="LEAGUE_NOT_FOUND",
                message=f"League {league_id} not found.",
                details={"league_id": league_id},
            )
        league = state.leagues[league_id]
        sport = state.sports[league["sport_id"]]

    teams = list(league["teams"])
    fixtures = league["fixtures"]
    points_cfg = league["points"]
    win_pts = points_cfg.get("win", 3)
    draw_pts = points_cfg.get("draw", 1)
    loss_pts = points_cfg.get("loss", 0)
    tb_order = list(league.get("tie_break_order", []))
    if "draw_lots" in tb_order:
        tb_order.remove("draw_lots")
    tb_order.append("draw_lots")

    qual_spots = league["qualification"]["spots"]
    lots_seed = league.get("lots_seed", state.seed)

    scoring_model = sport.get("scoring_model")
    periods = sport.get("periods", {})
    bpo = periods.get("balls_per_over", 6)
    overs_per_innings = periods.get("overs_per_innings", 20)
    wickets_per_innings = periods.get("wickets_per_innings", 10)

    # Initialize team records
    team_data: Dict[str, Dict[str, Any]] = {
        t: {
            "team_id": t,
            "played": 0,
            "won": 0,
            "drawn": 0,
            "lost": 0,
            "scored": 0,
            "conceded": 0,
            "diff": 0.0 if scoring_model == "innings" else 0,
            "points": 0,
            "fair_play": 0,
            # Innings metrics
            "runs_scored": 0,
            "overs_faced": 0.0,
            "runs_conceded": 0,
            "overs_bowled": 0.0,
        }
        for t in teams
    }

    # Initialize H2H matrix for every ordered pair
    h2h: Dict[str, Dict[str, Dict[str, int]]] = {
        a: {b: {"played": 0, "points": 0, "scored": 0, "conceded": 0} for b in teams}
        for a in teams
    }

    # Count remaining fixtures per team
    remaining_fixtures: Dict[str, int] = {t: 0 for t in teams}

    # Completed match results for H2H calculations
    completed_matches: List[Dict[str, Any]] = []

    for f in fixtures:
        mid = f["match_id"]
        proj = project_score(mid)
        status = proj["status"]
        outcome = proj["outcome"]

        h_id = proj["home"]["team_id"]
        a_id = proj["away"]["team_id"]

        if status == "completed" and outcome != "undecided":
            h_score = proj["home"]["score"]
            a_score = proj["away"]["score"]
            h_fair = proj["home"]["fair_play"]
            a_fair = proj["away"]["fair_play"]

            # Update played, fair_play
            team_data[h_id]["played"] += 1
            team_data[a_id]["played"] += 1
            team_data[h_id]["fair_play"] += h_fair
            team_data[a_id]["fair_play"] += a_fair

            # Scored / Conceded
            team_data[h_id]["scored"] += h_score
            team_data[h_id]["conceded"] += a_score
            team_data[a_id]["scored"] += a_score
            team_data[a_id]["conceded"] += h_score

            # Outcome points
            h_pts = 0
            a_pts = 0
            if outcome == "home_win":
                team_data[h_id]["won"] += 1
                team_data[a_id]["lost"] += 1
                h_pts = win_pts
                a_pts = loss_pts
            elif outcome == "away_win":
                team_data[a_id]["won"] += 1
                team_data[h_id]["lost"] += 1
                a_pts = win_pts
                h_pts = loss_pts
            elif outcome == "draw":
                team_data[h_id]["drawn"] += 1
                team_data[a_id]["drawn"] += 1
                h_pts = draw_pts
                a_pts = draw_pts

            team_data[h_id]["points"] += h_pts
            team_data[a_id]["points"] += a_pts

            # H2H matrix
            h2h[h_id][a_id]["played"] += 1
            h2h[h_id][a_id]["points"] += h_pts
            h2h[h_id][a_id]["scored"] += h_score
            h2h[h_id][a_id]["conceded"] += a_score

            h2h[a_id][h_id]["played"] += 1
            h2h[a_id][h_id]["points"] += a_pts
            h2h[a_id][h_id]["scored"] += a_score
            h2h[a_id][h_id]["conceded"] += h_score

            # Innings overs calculation
            if scoring_model == "innings":
                h_balls = proj["home"]["balls"] or 0
                h_w = proj["home"]["wickets"] or 0
                a_balls = proj["away"]["balls"] or 0
                a_w = proj["away"]["wickets"] or 0

                h_overs = float(overs_per_innings) if h_w >= wickets_per_innings else (h_balls / float(bpo))
                a_overs = float(overs_per_innings) if a_w >= wickets_per_innings else (a_balls / float(bpo))

                team_data[h_id]["runs_scored"] += h_score
                team_data[h_id]["overs_faced"] += h_overs
                team_data[h_id]["runs_conceded"] += a_score
                team_data[h_id]["overs_bowled"] += a_overs

                team_data[a_id]["runs_scored"] += a_score
                team_data[a_id]["overs_faced"] += a_overs
                team_data[a_id]["runs_conceded"] += h_score
                team_data[a_id]["overs_bowled"] += h_overs

            completed_matches.append({
                "home": h_id,
                "away": a_id,
                "h_score": h_score,
                "a_score": a_score,
                "h_pts": h_pts,
                "a_pts": a_pts,
                "h_overs": team_data[h_id].get("overs_faced", 0.0),
                "a_overs": team_data[a_id].get("overs_faced", 0.0),
            })
        else:
            remaining_fixtures[h_id] += 1
            remaining_fixtures[a_id] += 1

    # Compute overall differentials
    for t in teams:
        if scoring_model == "event":
            team_data[t]["diff"] = team_data[t]["scored"] - team_data[t]["conceded"]
        elif scoring_model == "round":
            team_data[t]["diff"] = team_data[t]["scored"] - team_data[t]["conceded"]
        elif scoring_model == "innings":
            r_scored = team_data[t]["runs_scored"]
            o_faced = team_data[t]["overs_faced"]
            r_conceded = team_data[t]["runs_conceded"]
            o_bowled = team_data[t]["overs_bowled"]
            rate_for = (r_scored / o_faced) if o_faced > 0 else 0.0
            rate_against = (r_conceded / o_bowled) if o_bowled > 0 else 0.0
            team_data[t]["diff"] = round(rate_for - rate_against, 3)

    # Qualification Status (Section 5.10)
    # W = win points, R(T) = remaining fixtures, max(T) = points(T) + W * R(T), k = qual_spots
    # clinched if fewer than k other teams X satisfy max(X) >= points(T)
    # eliminated if at least k other teams X satisfy points(X) > max(T)
    # otherwise still_possible
    qual_status: Dict[str, str] = {}
    for t in teams:
        p_t = team_data[t]["points"]
        max_t = p_t + win_pts * remaining_fixtures[t]

        # Count others with max(X) >= points(T)
        count_can_catch = sum(
            1 for x in teams if x != t and (team_data[x]["points"] + win_pts * remaining_fixtures[x]) >= p_t
        )
        if count_can_catch < qual_spots:
            qual_status[t] = "clinched"
            continue

        # Count others with points(X) > max(T)
        count_already_past = sum(
            1 for x in teams if x != t and team_data[x]["points"] > max_t
        )
        if count_already_past >= qual_spots:
            qual_status[t] = "eliminated"
        else:
            qual_status[t] = "still_possible"

    # Recursive Tied Group Resolution
    def get_criterion_value(t: str, criterion: str, current_group: List[str]) -> Any:
        if criterion == "h2h_points":
            # Points earned only in completed matches among current group
            pts = 0
            for opp in current_group:
                if opp != t:
                    pts += h2h[t][opp]["points"]
            return pts
        elif criterion == "h2h_diff":
            # Differential only among current group
            if scoring_model == "innings":
                # NRR among matches in current group
                sc = 0
                of = 0.0
                cc = 0
                ob = 0.0
                for opp in current_group:
                    if opp != t:
                        sc += h2h[t][opp]["scored"]
                        cc += h2h[t][opp]["conceded"]
                # Approximate from match overs
                rf = (sc / of) if of > 0 else 0.0
                ra = (cc / ob) if ob > 0 else 0.0
                return round(rf - ra, 3)
            else:
                diff_val = 0
                for opp in current_group:
                    if opp != t:
                        diff_val += (h2h[t][opp]["scored"] - h2h[t][opp]["conceded"])
                return diff_val
        elif criterion == "overall_diff":
            return team_data[t]["diff"]
        elif criterion == "scored":
            return team_data[t]["scored"]
        elif criterion == "fair_play":
            return team_data[t]["fair_play"]
        elif criterion == "draw_lots":
            # Ascending by SHA256 hex; smaller is better, so negate or sort asc
            return lots_key(lots_seed, league_id, t)
        return 0

    resolved_by_map: Dict[str, Optional[str]] = {t: None for t in teams}

    def resolve_group(group: List[str]) -> List[str]:
        if len(group) <= 1:
            return group

        for crit in tb_order:
            val_map: Dict[str, Any] = {}
            for t in group:
                val_map[t] = get_criterion_value(t, crit, group)

            all_vals = list(val_map.values())
            if all(v == all_vals[0] for v in all_vals):
                continue  # All tied on this criterion, move to next

            # Split group into sub-groups by value
            if crit == "draw_lots":
                # Ascending order
                unique_vals = sorted(set(all_vals))
            else:
                # Descending order (higher is better)
                unique_vals = sorted(set(all_vals), reverse=True)

            sub_groups = [[t for t in group if val_map[t] == uv] for uv in unique_vals]

            # Record resolution criterion for the top teams
            first_sub = sub_groups[0]
            for t in first_sub:
                if resolved_by_map[t] is None:
                    resolved_by_map[t] = crit

            resolved_full = []
            for sg in sub_groups:
                if len(sg) > 1:
                    resolved_full.extend(resolve_group(sg))
                else:
                    resolved_full.extend(sg)
            return resolved_full

        return group

    # 1. Group teams by points descending
    unique_points = sorted(set(team_data[t]["points"] for t in teams), reverse=True)
    final_ordered_teams: List[str] = []

    for pt in unique_points:
        pt_group = [t for t in teams if team_data[t]["points"] == pt]
        if len(pt_group) == 1:
            final_ordered_teams.append(pt_group[0])
        else:
            ordered_sub = resolve_group(pt_group)
            final_ordered_teams.extend(ordered_sub)

    # Build final table
    table = []
    for rank, t in enumerate(final_ordered_teams, start=1):
        td = team_data[t]
        table.append({
            "rank": rank,
            "team_id": t,
            "played": td["played"],
            "won": td["won"],
            "drawn": td["drawn"],
            "lost": td["lost"],
            "scored": td["scored"],
            "conceded": td["conceded"],
            "diff": td["diff"],
            "points": td["points"],
            "fair_play": td["fair_play"],
            "status": qual_status[t],
            "resolved_by": resolved_by_map[t],
        })

    return {
        "league_id": league_id,
        "sport_id": league["sport_id"],
        "qualification_spots": qual_spots,
        "table": table,
        "h2h": h2h,
    }
