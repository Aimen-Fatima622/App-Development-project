"""Custom fixture and bracket scheduling engine per Section 5.7 and Section 6.
Pure computation — third-party fixture libraries prohibited.
"""
import math
from typing import Any, Dict, List, Optional, Set, Tuple
from app.errors import AppException, validation_error


# --- Round Robin ---

def generate_round_robin(teams: List[str], params: Dict[str, Any]) -> Dict[str, Any]:
    n = len(teams)
    if n < 2 or n > 40:
        raise validation_error("Round-robin requires 2 to 40 teams.", fields=["teams"])

    legs = params.get("legs", 1)
    if legs not in [1, 2]:
        raise validation_error("legs must be 1 or 2.", fields=["params.legs"])

    withdrawals = params.get("withdrawals", [])
    withdrawal_policy = params.get("withdrawal_policy", "forfeit_remaining")
    if withdrawal_policy not in ["forfeit_remaining", "void_all"]:
        raise validation_error("Invalid withdrawal_policy.", fields=["params.withdrawal_policy"])

    rounds_per_leg = n if n % 2 != 0 else n - 1
    total_round_count = rounds_per_leg * legs

    # Validate withdrawals
    team_set = set(teams)
    withdrawn_map: Dict[str, int] = {}
    for w in withdrawals:
        t_id = w.get("team_id")
        ar = w.get("after_round")
        if t_id not in team_set:
            raise validation_error(f"Unknown withdrawal team {t_id}", fields=["params.withdrawals"])
        if not isinstance(ar, int) or ar < 0 or ar > total_round_count:
            raise validation_error(f"Invalid after_round {ar}", fields=["params.withdrawals"])
        withdrawn_map[t_id] = ar

    # Circle method setup
    team_list = list(teams)
    has_dummy = False
    if n % 2 != 0:
        has_dummy = True
        team_list.append("__DUMMY__")
    
    m = len(team_list)
    half = m // 2

    rounds_out = []
    total_matches = 0
    scheduled_count = 0
    forfeit_count = 0
    voided_count = 0

    # Circle method rotation
    rotation = list(team_list)
    for leg in range(1, legs + 1):
        for r_in_leg in range(1, rounds_per_leg + 1):
            global_round = (leg - 1) * rounds_per_leg + r_in_leg
            matches_this_round = []
            byes_this_round = []

            for i in range(half):
                t1 = rotation[i]
                t2 = rotation[m - 1 - i]

                # Decide home and away
                if i == 0:
                    if r_in_leg % 2 == 1:
                        h, a = t1, t2
                    else:
                        h, a = t2, t1
                else:
                    if (i + r_in_leg) % 2 == 1:
                        h, a = t1, t2
                    else:
                        h, a = t2, t1

                # If leg 2, swap home and away to achieve exact balanced pairs
                if leg == 2:
                    h, a = a, h

                if h == "__DUMMY__":
                    byes_this_round.append(a)
                elif a == "__DUMMY__":
                    byes_this_round.append(h)
                else:
                    match_index = len(matches_this_round) + 1
                    match_id = f"RR-L{leg}-R{global_round}-M{match_index}"
                    status = "scheduled"
                    awarded_to = None

                    # Check withdrawal rules
                    h_withdrawn = h in withdrawn_map
                    a_withdrawn = a in withdrawn_map
                    h_ar = withdrawn_map.get(h, 999999)
                    a_ar = withdrawn_map.get(a, 999999)

                    if withdrawal_policy == "void_all":
                        if h_withdrawn or a_withdrawn:
                            status = "voided"
                            awarded_to = None
                    elif withdrawal_policy == "forfeit_remaining":
                        h_forfeits = h_withdrawn and global_round > h_ar
                        a_forfeits = a_withdrawn and global_round > a_ar
                        if h_forfeits and a_forfeits:
                            status = "voided"
                            awarded_to = None
                        elif h_forfeits:
                            status = "forfeit"
                            awarded_to = a
                        elif a_forfeits:
                            status = "forfeit"
                            awarded_to = h

                    total_matches += 1
                    if status == "scheduled":
                        scheduled_count += 1
                    elif status == "forfeit":
                        forfeit_count += 1
                    elif status == "voided":
                        voided_count += 1

                    matches_this_round.append({
                        "match_id": match_id,
                        "leg": leg,
                        "home": h,
                        "away": a,
                        "status": status,
                        "awarded_to": awarded_to,
                    })

            rounds_out.append({
                "round": global_round,
                "matches": matches_this_round,
                "byes": byes_this_round,
            })

            # Rotate: keep rotation[0], rotate rotation[1:]
            rotation = [rotation[0]] + [rotation[-1]] + rotation[1:-1]

    return {
        "format": "round_robin",
        "legs": legs,
        "team_count": n,
        "round_count": total_round_count,
        "rounds": rounds_out,
        "summary": {
            "total": total_matches,
            "scheduled": scheduled_count,
            "forfeit": forfeit_count,
            "voided": voided_count,
        },
    }


# --- Swiss System ---

def generate_swiss(teams: List[str], params: Dict[str, Any]) -> Dict[str, Any]:
    n = len(teams)
    if n < 2 or n > 64:
        raise validation_error("Swiss format requires 2 to 64 teams.", fields=["teams"])

    default_total = math.ceil(math.log2(n))
    total_rounds = params.get("total_rounds", default_total)
    round_to_pair = params.get("round", 1)

    if not isinstance(total_rounds, int) or total_rounds < 1 or total_rounds >= n:
        raise validation_error("total_rounds must be 1..n-1", fields=["params.total_rounds"])
    if not isinstance(round_to_pair, int) or round_to_pair < 1 or round_to_pair > total_rounds:
        raise validation_error("round must be 1..total_rounds", fields=["params.round"])

    history = params.get("history", [])
    if len(history) != round_to_pair - 1:
        raise validation_error("history must contain exactly 1..round-1", fields=["params.history"])

    # Calculate scores, buchholz, previous opponents, and byes received
    scores: Dict[str, float] = {t: 0.0 for t in teams}
    byes_received: Set[str] = set()
    opponents_played: Dict[str, Set[str]] = {t: set() for t in teams}

    for h_round in history:
        b_team = h_round.get("bye")
        if b_team:
            byes_received.add(b_team)
            scores[b_team] += 1.0

        for m in h_round.get("matches", []):
            h = m["home"]
            a = m["away"]
            res = m["result"]
            opponents_played[h].add(a)
            opponents_played[a].add(h)
            if res == "home":
                scores[h] += 1.0
            elif res == "away":
                scores[a] += 1.0
            elif res == "draw":
                scores[h] += 0.5
                scores[a] += 0.5

    # Calculate Buchholz
    buchholz: Dict[str, float] = {}
    for t in teams:
        buchholz[t] = sum(scores[opp] for opp in opponents_played[t])

    # Build standings sorted by score desc, buchholz desc, seed asc
    team_indices = {t: idx for idx, t in enumerate(teams)}
    sorted_teams = sorted(
        teams,
        key=lambda t: (-scores[t], -buchholz[t], team_indices[t]),
    )

    standings = []
    for rank, t in enumerate(sorted_teams, start=1):
        standings.append({
            "rank": rank,
            "team_id": t,
            "score": scores[t],
            "buchholz": buchholz[t],
        })

    # Pairing
    pairings = []
    bye_team: Optional[str] = None

    if round_to_pair == 1:
        m = n // 2
        if n % 2 != 0:
            bye_team = teams[-1]
        for i in range(m):
            home_t = teams[i]
            away_t = teams[i + m]
            pairings.append({
                "match_id": f"SW-R1-M{i + 1}",
                "home": home_t,
                "away": away_t,
            })
    else:
        # Rounds >= 2 with backtracking
        eligible_for_bye = []
        if n % 2 != 0:
            # Lowest scoring team that has not had a bye; tie -> lowest seed (largest index)
            eligible_for_bye = [t for t in sorted_teams if t not in byes_received]
            eligible_for_bye.sort(key=lambda t: (scores[t], -team_indices[t]))

        def try_pair_remaining(active_teams: List[str]) -> Optional[List[Tuple[str, str]]]:
            # Minimum |score difference| pairing with backtracking
            if not active_teams:
                return []

            first = active_teams[0]
            best_pairs = None
            min_cost = float("inf")

            # Try pairing first with each candidate
            candidates = [c for c in active_teams[1:] if c not in opponents_played[first]]
            # Sort candidates by |score difference|, then seed
            candidates.sort(key=lambda c: (abs(scores[first] - scores[c]), team_indices[c]))

            for cand in candidates:
                diff = abs(scores[first] - scores[cand])
                sub_teams = [t for t in active_teams[1:] if t != cand]
                res = try_pair_remaining(sub_teams)
                if res is not None:
                    # Calculate cost of this branch
                    current_cost = diff + sum(abs(scores[p1] - scores[p2]) for p1, p2 in res)
                    if current_cost < min_cost:
                        min_cost = current_cost
                        best_pairs = [(first, cand)] + res
                        # If zero difference, can't get better than 0 for this pairing
                        if min_cost == 0:
                            break

            return best_pairs

        success = False
        if n % 2 != 0:
            for b_cand in eligible_for_bye:
                active = [t for t in sorted_teams if t != b_cand]
                pairs = try_pair_remaining(active)
                if pairs is not None:
                    bye_team = b_cand
                    success = True
                    for idx, (h, a) in enumerate(pairs, start=1):
                        pairings.append({
                            "match_id": f"SW-R{round_to_pair}-M{idx}",
                            "home": h,
                            "away": a,
                        })
                    break
        else:
            pairs = try_pair_remaining(sorted_teams)
            if pairs is not None:
                success = True
                for idx, (h, a) in enumerate(pairs, start=1):
                    pairings.append({
                        "match_id": f"SW-R{round_to_pair}-M{idx}",
                        "home": h,
                        "away": a,
                    })

        if not success:
            raise AppException(
                status_code=409,
                code="NO_VALID_PAIRING",
                message="No rematch-free pairing exists for Swiss round.",
                details={"round": round_to_pair},
            )

    return {
        "format": "swiss",
        "round": round_to_pair,
        "total_rounds": total_rounds,
        "pairings": pairings,
        "bye": bye_team,
        "standings": standings,
    }


# --- Single Elimination ---

def get_bracket_order(k: int) -> List[int]:
    """Recursive bracket seed order: order(2) = [1,2], order(2k) = for s in order(k): [s, 2k + 1 - s]."""
    if k <= 2:
        return [1, 2]
    prev = get_bracket_order(k // 2)
    order = []
    for s in prev:
        order.append(s)
        order.append(k + 1 - s)
    return order


def generate_single_elim(teams: List[str], params: Dict[str, Any]) -> Dict[str, Any]:
    n = len(teams)
    if n < 2 or n > 128:
        raise validation_error("Single elimination requires 2 to 128 teams.", fields=["teams"])

    third_place = params.get("third_place_match", False)
    results = params.get("results", [])

    k = 1
    while (1 << k) < n:
        k += 1
    B = 1 << k
    total_rounds = k

    # Seed map (1-indexed)
    seeds = {i + 1: teams[i] for i in range(n)}
    seed_order = get_bracket_order(B)

    # Initialize all matches
    matches_by_id: Dict[str, Dict[str, Any]] = {}
    rounds_out: List[Dict[str, Any]] = []

    for r in range(1, total_rounds + 1):
        num_matches = B // (1 << r)
        round_matches = []
        for i in range(1, num_matches + 1):
            mid = f"R{r}M{i}"
            match_data = {
                "match_id": mid,
                "bracket": "main",
                "round": r,
                "index": i,
                "home": None,
                "away": None,
                "home_seed": None,
                "away_seed": None,
                "bye": False,
                "winner": None,
                "loser": None,
                "winner_to": None,
                "loser_to": None,
            }
            if r < total_rounds:
                next_round = r + 1
                next_idx = math.ceil(i / 2)
                slot = "home" if i % 2 == 1 else "away"
                match_data["winner_to"] = {"match_id": f"R{next_round}M{next_idx}", "slot": slot}

            matches_by_id[mid] = match_data
            round_matches.append(match_data)
        rounds_out.append({"round": r, "matches": round_matches})

    # Third place match if requested
    if third_place and total_rounds >= 2:
        tp_match = {
            "match_id": "TP",
            "bracket": "third_place",
            "round": total_rounds,
            "index": 1,
            "home": None,
            "away": None,
            "home_seed": None,
            "away_seed": None,
            "bye": False,
            "winner": None,
            "loser": None,
            "winner_to": None,
            "loser_to": None,
        }
        matches_by_id["TP"] = tp_match
        # Semifinal matches loser_to points to TP
        sf_round = total_rounds - 1
        matches_by_id[f"R{sf_round}M1"]["loser_to"] = {"match_id": "TP", "slot": "home"}
        matches_by_id[f"R{sf_round}M2"]["loser_to"] = {"match_id": "TP", "slot": "away"}

    # Fill Round 1 from seed_order
    r1_count = B // 2
    for i in range(1, r1_count + 1):
        mid = f"R1M{i}"
        s1 = seed_order[2 * (i - 1)]
        s2 = seed_order[2 * (i - 1) + 1]
        m = matches_by_id[mid]

        t1 = seeds.get(s1)
        t2 = seeds.get(s2)

        if s1 <= s2:
            m["home"] = t1
            m["home_seed"] = s1
            m["away"] = t2
            m["away_seed"] = s2 if s2 <= n else None
        else:
            m["home"] = t2
            m["home_seed"] = s2
            m["away"] = t1
            m["away_seed"] = s1 if s1 <= n else None

        if m["away"] is None:
            m["bye"] = True
            m["winner"] = m["home"]
            # Propagate bye winner immediately
            if m["winner_to"]:
                w_mid = m["winner_to"]["match_id"]
                w_slot = m["winner_to"]["slot"]
                matches_by_id[w_mid][w_slot] = m["home"]

    # Apply results
    for res in results:
        mid = res.get("match_id")
        winner = res.get("winner")
        if mid not in matches_by_id:
            raise validation_error(f"Unknown match_id {mid}", fields=["params.results"])
        m = matches_by_id[mid]
        if winner not in [m["home"], m["away"]]:
            raise validation_error(f"Winner {winner} is not a participant in {mid}", fields=["params.results"])

        loser = m["away"] if winner == m["home"] else m["home"]
        m["winner"] = winner
        m["loser"] = loser

        if m["winner_to"]:
            w_mid = m["winner_to"]["match_id"]
            w_slot = m["winner_to"]["slot"]
            matches_by_id[w_mid][w_slot] = winner
        if m.get("loser_to"):
            l_mid = m["loser_to"]["match_id"]
            l_slot = m["loser_to"]["slot"]
            matches_by_id[l_mid][l_slot] = loser

    return {
        "format": "single_elim",
        "bracket_size": B,
        "rounds": rounds_out,
    }


# --- Double Elimination ---

def generate_double_elim(teams: List[str], params: Dict[str, Any]) -> Dict[str, Any]:
    n = len(teams)
    if n < 3 or n > 128:
        raise validation_error("Double elimination requires 3 to 128 teams.", fields=["teams"])

    bracket_reset = params.get("bracket_reset", True)
    results = params.get("results", [])

    k = 1
    while (1 << k) < n:
        k += 1
    B = 1 << k

    matches_by_id: Dict[str, Dict[str, Any]] = {}
    winners_rounds: List[Dict[str, Any]] = []
    losers_rounds: List[Dict[str, Any]] = []

    # 1. Winners Bracket
    for r in range(1, k + 1):
        count = B // (1 << r)
        r_matches = []
        for i in range(1, count + 1):
            mid = f"WR{r}M{i}"
            m_obj = {
                "match_id": mid,
                "bracket": "winners",
                "round": r,
                "index": i,
                "home": None,
                "away": None,
                "home_seed": None,
                "away_seed": None,
                "bye": False,
                "winner": None,
                "loser": None,
                "winner_to": None,
                "loser_to": None,
            }
            matches_by_id[mid] = m_obj
            r_matches.append(m_obj)
        winners_rounds.append({"round": r, "matches": r_matches})

    # 2. Losers Bracket
    # Total losers rounds = 2 * (k - 1)
    total_lr = 2 * (k - 1)
    for lr in range(1, total_lr + 1):
        # Round 2j - 1 and 2j have B / (2^(j+1)) matches (j = (lr + 1) // 2)
        j = (lr + 1) // 2
        count = B // (1 << (j + 1))
        r_matches = []
        for i in range(1, count + 1):
            mid = f"LR{lr}M{i}"
            m_obj = {
                "match_id": mid,
                "bracket": "losers",
                "round": lr,
                "index": i,
                "home": None,
                "away": None,
                "home_seed": None,
                "away_seed": None,
                "bye": False,
                "winner": None,
                "loser": None,
                "winner_to": None,
                "loser_to": None,
            }
            matches_by_id[mid] = m_obj
            r_matches.append(m_obj)
        losers_rounds.append({"round": lr, "matches": r_matches})

    # 3. Grand Finals
    gf1 = {
        "match_id": "GF1",
        "bracket": "grand_final",
        "round": 1,
        "index": 1,
        "home": None,
        "away": None,
        "home_seed": None,
        "away_seed": None,
        "bye": False,
        "winner": None,
        "loser": None,
        "winner_to": None,
        "loser_to": None,
    }
    matches_by_id["GF1"] = gf1
    grand_finals = [gf1]

    gf2 = None
    if bracket_reset:
        gf2 = {
            "match_id": "GF2",
            "bracket": "grand_final",
            "round": 2,
            "index": 1,
            "home": None,
            "away": None,
            "home_seed": None,
            "away_seed": None,
            "conditional": True,
            "required": None,
            "bye": False,
            "winner": None,
            "loser": None,
            "winner_to": None,
            "loser_to": None,
        }
        matches_by_id["GF2"] = gf2
        grand_finals.append(gf2)

    # 4. Routing
    # Winners advancement
    for r in range(1, k):
        count = B // (1 << r)
        for i in range(1, count + 1):
            mid = f"WR{r}M{i}"
            next_mid = f"WR{r+1}M{math.ceil(i/2)}"
            slot = "home" if i % 2 == 1 else "away"
            matches_by_id[mid]["winner_to"] = {"match_id": next_mid, "slot": slot}

    # WR final winner -> GF1.home
    matches_by_id[f"WR{k}M1"]["winner_to"] = {"match_id": "GF1", "slot": "home"}

    # Losers advancement
    for lr in range(1, total_lr):
        count = len(losers_rounds[lr - 1]["matches"])
        for i in range(1, count + 1):
            mid = f"LR{lr}M{i}"
            if lr % 2 == 1:
                # Odd losers round -> feeds same round count in even round
                next_mid = f"LR{lr+1}M{i}"
                matches_by_id[mid]["winner_to"] = {"match_id": next_mid, "slot": "home"}
            else:
                # Even losers round -> feeds half count in next odd round
                next_mid = f"LR{lr+1}M{math.ceil(i/2)}"
                slot = "home" if i % 2 == 1 else "away"
                matches_by_id[mid]["winner_to"] = {"match_id": next_mid, "slot": slot}

    # LB final winner -> GF1.away
    matches_by_id[f"LR{total_lr}M1"]["winner_to"] = {"match_id": "GF1", "slot": "away"}

    # Drops from Winners into Losers:
    # WR1 losers drop into LR1
    wr1_count = B // 2
    for i in range(1, wr1_count + 1):
        mid = f"WR1M{i}"
        target_lr = 1
        target_idx = math.ceil(i / 2)
        slot = "home" if i % 2 == 1 else "away"
        matches_by_id[mid]["loser_to"] = {"match_id": f"LR{target_lr}M{target_idx}", "slot": slot}

    # WRr (r >= 2) losers drop into LR(2r - 2)
    for r in range(2, k):
        count = B // (1 << r)
        target_lr = 2 * r - 2
        for i in range(1, count + 1):
            mid = f"WR{r}M{i}"
            matches_by_id[mid]["loser_to"] = {"match_id": f"LR{target_lr}M{i}", "slot": "away"}

    # WR final loser -> LB final (LR{total_lr}M1) away
    matches_by_id[f"WR{k}M1"]["loser_to"] = {"match_id": f"LR{total_lr}M1", "slot": "away"}

    # 5. Populate WR1
    seeds = {i + 1: teams[i] for i in range(n)}
    seed_order = get_bracket_order(B)
    for i in range(1, wr1_count + 1):
        mid = f"WR1M{i}"
        s1 = seed_order[2 * (i - 1)]
        s2 = seed_order[2 * (i - 1) + 1]
        m = matches_by_id[mid]
        t1 = seeds.get(s1)
        t2 = seeds.get(s2)

        if s1 <= s2:
            m["home"] = t1
            m["home_seed"] = s1
            m["away"] = t2
            m["away_seed"] = s2 if s2 <= n else None
        else:
            m["home"] = t2
            m["home_seed"] = s2
            m["away"] = t1
            m["away_seed"] = s1 if s1 <= n else None

        if m["away"] is None:
            m["bye"] = True
            m["winner"] = m["home"]
            if m["winner_to"]:
                w_mid = m["winner_to"]["match_id"]
                w_slot = m["winner_to"]["slot"]
                matches_by_id[w_mid][w_slot] = m["home"]

    # 6. Apply Results
    for res in results:
        mid = res.get("match_id")
        winner = res.get("winner")
        if mid not in matches_by_id:
            raise validation_error(f"Unknown match_id {mid}", fields=["params.results"])
        m = matches_by_id[mid]
        if winner not in [m["home"], m["away"]]:
            raise validation_error(f"Winner {winner} is not a participant in {mid}", fields=["params.results"])

        loser = m["away"] if winner == m["home"] else m["home"]
        m["winner"] = winner
        m["loser"] = loser

        if m["winner_to"]:
            w_mid = m["winner_to"]["match_id"]
            w_slot = m["winner_to"]["slot"]
            matches_by_id[w_mid][w_slot] = winner
        if m.get("loser_to"):
            l_mid = m["loser_to"]["match_id"]
            l_slot = m["loser_to"]["slot"]
            matches_by_id[l_mid][l_slot] = loser

        # Bracket reset check on GF1
        if mid == "GF1" and gf2:
            gf2["home"] = m["home"]
            gf2["away"] = m["away"]
            if winner == m["away"]:  # Losers bracket champion won GF1
                gf2["required"] = True
            else:
                gf2["required"] = False

    return {
        "format": "double_elim",
        "bracket_size": B,
        "bracket_reset": bracket_reset,
        "winners": winners_rounds,
        "losers": losers_rounds,
        "grand_final": grand_finals,
    }
