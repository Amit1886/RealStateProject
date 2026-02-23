from __future__ import annotations

import hmac
import os
import time
from hashlib import sha256
from typing import Optional


def env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


def _hmac_sha256_hex(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), payload, sha256).hexdigest()


def verify_razorpay_webhook(*, raw_body: bytes, signature: str, secret: str) -> bool:
    if not signature or not secret:
        return False
    expected = _hmac_sha256_hex(secret, raw_body or b"")
    return hmac.compare_digest(expected, signature.strip())


def verify_stripe_webhook(
    *,
    raw_body: bytes,
    stripe_signature_header: str,
    secret: str,
    tolerance_seconds: int = 300,
    now_ts: Optional[int] = None,
) -> bool:
    if not stripe_signature_header or not secret:
        return False

    parts = {}
    for item in stripe_signature_header.split(","):
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        parts.setdefault(k.strip(), []).append(v.strip())

    ts_vals = parts.get("t") or []
    v1_vals = parts.get("v1") or []
    if not ts_vals or not v1_vals:
        return False

    try:
        ts = int(ts_vals[0])
    except ValueError:
        return False

    current = int(now_ts if now_ts is not None else time.time())
    if tolerance_seconds is not None and abs(current - ts) > int(tolerance_seconds):
        return False

    try:
        signed_payload = f"{ts}.".encode("utf-8") + (raw_body or b"")
    except Exception:
        return False

    expected = _hmac_sha256_hex(secret, signed_payload)
    return any(hmac.compare_digest(expected, sig) for sig in v1_vals)

