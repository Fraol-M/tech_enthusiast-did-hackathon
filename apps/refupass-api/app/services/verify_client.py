from __future__ import annotations

import json
from typing import Any

import httpx

from ..config import Settings


class InjiVerifyClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def verify(self, credential: dict[str, Any] | str) -> dict[str, Any]:
        mode = self.settings.inji_verify_mode.lower()
        if mode == "passthrough":
            return await self._passthrough(credential)
        return self._stub(credential)

    def _stub(self, credential: dict[str, Any] | str) -> dict[str, Any]:
        if isinstance(credential, str):
            return {
                "cryptographicStatus": "invalid",
                "details": {
                    "mode": "stub",
                    "error": "Stub mode only supports JSON credential payloads.",
                },
            }

        proof = credential.get("proof")
        types = credential.get("type") or []
        is_valid = bool(proof) and "VerifiableCredential" in types
        return {
            "cryptographicStatus": "valid" if is_valid else "invalid",
            "details": {
                "mode": "stub",
                "hasProof": bool(proof),
                "types": types,
                "expirationDate": credential.get("expirationDate"),
            },
        }

    async def _passthrough(self, credential: dict[str, Any] | str) -> dict[str, Any]:
        verifiable_credential = credential if isinstance(credential, str) else json.dumps(credential)
        request_payload = {
            "verifiableCredential": verifiable_credential,
            "includeClaims": True,
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                response = await client.post(f"{self.settings.inji_verify_api_url}/v2/vc-verification", json=request_payload)
                data = response.json() if response.content else {}
                if response.is_success and self._is_success_response(data):
                    return {
                        "cryptographicStatus": "valid",
                        "details": {
                            "mode": "passthrough",
                            "claims": data.get("claims", {}),
                            "rawResponse": data,
                        },
                    }
                last_error = {"status": response.status_code, "body": data if response.content else response.text}
            except httpx.HTTPError as exc:
                last_error = {"error": str(exc)}

        return {
            "cryptographicStatus": "invalid",
            "details": {
                "mode": "passthrough",
                "error": "Inji Verify request failed",
                "lastAttempt": last_error,
            },
        }

    @staticmethod
    def _is_success_response(data: Any) -> bool:
        if isinstance(data, dict):
            if "allChecksSuccessful" in data:
                return bool(data.get("allChecksSuccessful"))
            for key in ("verificationStatus", "status", "result"):
                value = data.get(key)
                if isinstance(value, str):
                    normalized = value.strip().lower()
                    if normalized in {"success", "valid", "verified"}:
                        return True
        return False
