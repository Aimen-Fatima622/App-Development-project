"""Cryptographic and hashing utilities per Section 5.3 and Appendix A."""
import hashlib
import hmac
import json
import os
from typing import Any


def get_salt() -> str:
    """Read DAY1_SALT only from environment variable at runtime."""
    return os.environ.get("DAY1_SALT", "")


def canonical(obj: Any) -> str:
    """Canonical JSON string of an object (Section 5.3).
    Recursively sorted keys, no whitespace separators, UTF-8 non-ASCII not escaped.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sign(salt: str, id_: str, payload_obj: Any) -> str:
    """HMAC-SHA256 signature for event records and receipts (Section 5.3, Appendix A)."""
    canonical_payload = canonical(payload_obj)
    msg = (id_ + "|" + canonical_payload).encode("utf-8")
    return hmac.new(salt.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def lots_key(seed: int, league_id: str, team_id: str) -> str:
    """Deterministic hash key for drawing-of-lots tie-break (Section 5.10, Appendix A)."""
    msg = f"{seed}|{league_id}|{team_id}".encode("utf-8")
    return hashlib.sha256(msg).hexdigest()
