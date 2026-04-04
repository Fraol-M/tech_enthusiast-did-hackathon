from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


def _canonical_payload(payload: dict[str, Any]) -> bytes:
    unsigned_payload = {key: value for key, value in payload.items() if key != "signature"}
    return json.dumps(unsigned_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sign_pass_payload(payload: dict[str, Any], secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), _canonical_payload(payload), hashlib.sha256).hexdigest()


def attach_signature(payload: dict[str, Any], secret: str) -> dict[str, Any]:
    signed_payload = dict(payload)
    signed_payload["signature"] = sign_pass_payload(signed_payload, secret)
    return signed_payload


def verify_pass_payload(payload: dict[str, Any], secret: str) -> bool:
    provided_signature = payload.get("signature")
    if not isinstance(provided_signature, str) or not provided_signature:
        return False
    expected_signature = sign_pass_payload(payload, secret)
    return hmac.compare_digest(provided_signature, expected_signature)
