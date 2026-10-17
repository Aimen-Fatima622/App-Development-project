"""Offline synchronization and conflict resolution engine per Section 5.14."""
from typing import Any, Dict, List, Optional
from app.crypto import canonical
from app.errors import AppException, validation_error
from app.roster import process_transfer
from app.scoring import append_event, project_score
from app.state import state


def process_offline_sync(body: Dict[str, Any]) -> Dict[str, Any]:
    device_id = body.get("device_id")
    actions = body.get("actions")

    bad_fields = []
    if not device_id or not isinstance(device_id, str):
        bad_fields.append("device_id")
    if not isinstance(actions, list) or len(actions) < 1 or len(actions) > 100:
        bad_fields.append("actions")

    if bad_fields:
        raise validation_error("Validation failed for offline-sync.", fields=bad_fields)

    # Attach original index to preserve request order in final response
    indexed_actions = list(enumerate(actions))
    # Sort by queued_at ascending (ties: array order)
    indexed_actions.sort(key=lambda item: (item[1].get("queued_at", ""), item[0]))

    results_by_index: Dict[int, Dict[str, Any]] = {}
    applied_count = 0
    rejected_count = 0
    duplicate_count = 0

    with state.lock:
        for proc_order, (orig_idx, act) in enumerate(indexed_actions, start=1):
            act_id = act.get("action_id")
            act_type = act.get("type")
            base_ver = act.get("base_version")
            payload = act.get("payload", {})

            act_key = f"{device_id}:{act_id}"

            # Check if (device_id, action_id) already processed before
            if act_key in state.offline_actions:
                duplicate_count += 1
                stored_res = dict(state.offline_actions[act_key])
                stored_res["processed_order"] = proc_order
                results_by_index[orig_idx] = stored_res
                continue

            # Determine current server version for the resource
            curr_ver = 0
            if act_type == "score_event":
                mid = payload.get("match_id")
                if not mid or mid not in state.matches:
                    rejected_count += 1
                    err_res = {
                        "action_id": act_id,
                        "status": "rejected",
                        "resolution": "server_wins",
                        "error_code": "MATCH_NOT_FOUND",
                        "processed_order": proc_order,
                        "server_version": 0,
                        "signature": None,
                    }
                    state.offline_actions[act_key] = err_res
                    results_by_index[orig_idx] = err_res
                    continue
                curr_ver = len(state.match_events.get(mid, []))
            elif act_type == "roster_transfer":
                pid = payload.get("player_id")
                if not pid or pid not in state.players:
                    rejected_count += 1
                    err_res = {
                        "action_id": act_id,
                        "status": "rejected",
                        "resolution": "server_wins",
                        "error_code": "PLAYER_NOT_FOUND",
                        "processed_order": proc_order,
                        "server_version": 0,
                        "signature": None,
                    }
                    state.offline_actions[act_key] = err_res
                    results_by_index[orig_idx] = err_res
                    continue
                curr_ver = len(state.roster_history.get(pid, []))

            # Check base_version > current_version
            if isinstance(base_ver, int) and base_ver > curr_ver:
                rejected_count += 1
                err_res = {
                    "action_id": act_id,
                    "status": "rejected",
                    "resolution": "server_wins",
                    "error_code": "INVALID_BASE_VERSION",
                    "processed_order": proc_order,
                    "server_version": curr_ver,
                    "signature": None,
                }
                state.offline_actions[act_key] = err_res
                results_by_index[orig_idx] = err_res
                continue

            # Try to apply action
            try:
                sig = None
                new_ver = curr_ver
                if act_type == "score_event":
                    st_code, evt_resp = append_event(payload)
                    sig = evt_resp.get("signature")
                    mid = payload.get("match_id")
                    new_ver = len(state.match_events.get(mid, []))
                elif act_type == "roster_transfer":
                    st_code, tr_resp = process_transfer(payload)
                    pid = payload.get("player_id")
                    new_ver = len(state.roster_history.get(pid, []))
                else:
                    raise AppException(status_code=400, code="VALIDATION_ERROR", message="Unknown action type.")

                resolution = "appended" if base_ver == curr_ver else "rebased_append"
                applied_count += 1
                succ_res = {
                    "action_id": act_id,
                    "status": "applied",
                    "resolution": resolution,
                    "error_code": None,
                    "processed_order": proc_order,
                    "server_version": new_ver,
                    "signature": sig,
                }
                state.offline_actions[act_key] = succ_res
                results_by_index[orig_idx] = succ_res

            except AppException as ex:
                rejected_count += 1
                err_res = {
                    "action_id": act_id,
                    "status": "rejected",
                    "resolution": "server_wins",
                    "error_code": ex.code,
                    "processed_order": proc_order,
                    "server_version": curr_ver,
                    "signature": None,
                }
                state.offline_actions[act_key] = err_res
                results_by_index[orig_idx] = err_res

    # Assemble response in request order
    final_results = [results_by_index[i] for i in range(len(actions))]

    return {
        "device_id": device_id,
        "results": final_results,
        "summary": {
            "applied": applied_count,
            "rejected": rejected_count,
            "duplicate": duplicate_count,
        },
    }
