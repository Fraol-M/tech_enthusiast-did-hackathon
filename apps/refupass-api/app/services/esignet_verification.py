from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import uuid4

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ..config import Settings


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _request_time() -> str:
    timestamp = datetime.now(UTC)
    return timestamp.strftime("%Y-%m-%dT%H:%M:%S.") + f"{timestamp.microsecond // 1000:03d}Z"


def _format_esignet_errors(payload: dict) -> str:
    errors = payload.get("errors") or []
    if not errors:
        return "Unknown eSignet error."
    messages = []
    for error in errors:
        code = error.get("errorCode")
        message = error.get("message") or error.get("errorMessage") or "Unknown error"
        messages.append(f"{code}: {message}" if code else message)
    return "; ".join(messages)


def _generate_client_material() -> tuple[str, str, dict[str, str]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    modulus = public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")
    exponent = public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big")
    modulus_b64 = _base64url(modulus)
    client_id = modulus_b64[2:50] if len(modulus_b64) > 50 else modulus_b64
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_jwk = {
        "kty": "RSA",
        "e": _base64url(exponent),
        "n": modulus_b64,
    }
    return client_id, private_pem, public_jwk


def _generate_pkce_pair() -> tuple[str, str]:
    code_verifier = _base64url(secrets.token_bytes(32))
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = _base64url(digest)
    return code_verifier, code_challenge


class ESignetVerificationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def start_verification(self, *, session_token: str) -> dict[str, str]:
        state = f"refupass-{uuid4().hex}"
        nonce = f"refupass-{uuid4().hex}"

        async with httpx.AsyncClient(timeout=20.0) as client:
            csrf_response = await client.get(f"{self.settings.esignet_api_url}/v1/esignet/csrf/token")
            csrf_response.raise_for_status()
            csrf_token = csrf_response.json().get("token")
            if not csrf_token:
                raise RuntimeError("Could not fetch the eSignet CSRF token.")

            headers = {"X-XSRF-TOKEN": csrf_token}
            last_error_message = "Could not create the eSignet client for RefuPass verification."
            max_attempts = 5
            for _ in range(max_attempts):
                client_id, private_key_pem, public_jwk = _generate_client_material()
                code_verifier, code_challenge = _generate_pkce_pair()
                client_body = {
                    "requestTime": _request_time(),
                    "request": {
                        "clientId": client_id,
                        "clientName": self.settings.esignet_client_name,
                        "publicKey": public_jwk,
                        "relyingPartyId": "mock-relying-party-id",
                        "userClaims": ["name", "email", "gender", "phone_number", "picture", "birthdate"],
                        "authContextRefs": [
                            "mosip:idp:acr:generated-code",
                            "mosip:idp:acr:password",
                            "mosip:idp:acr:linked-wallet",
                        ],
                        "logoUri": self.settings.esignet_client_logo_url,
                        "redirectUris": [self.settings.esignet_callback_url],
                        "grantTypes": ["authorization_code"],
                        "clientAuthMethods": ["private_key_jwt"],
                        "additionalConfig": {
                            "userinfo_response_type": "JWS",
                            "purpose": {"type": "verify"},
                            "signup_banner_required": True,
                            "forgot_pwd_link_required": True,
                            "consent_expire_in_mins": 20,
                        },
                    },
                }
                create_response = await client.post(
                    f"{self.settings.esignet_api_url}/v1/esignet/client-mgmt/client",
                    headers=headers,
                    json=client_body,
                )
                create_response.raise_for_status()
                create_payload = create_response.json()
                if create_payload.get("errors"):
                    last_error_message = _format_esignet_errors(create_payload)
                    continue

                oauth_check_body = {
                    "requestTime": _request_time(),
                    "request": {
                        "clientId": client_id,
                        "scope": "openid profile",
                        "responseType": "code",
                        "redirectUri": self.settings.esignet_callback_url,
                        "display": "popup",
                        "prompt": "login",
                        "acrValues": "mosip:idp:acr:generated-code",
                        "claims": {
                            "userinfo": {
                                "given_name": {"essential": True},
                                "phone_number": {"essential": False},
                                "email": {"essential": True},
                                "picture": {"essential": False},
                                "gender": {"essential": False},
                                "birthdate": {"essential": False},
                                "address": {"essential": False},
                            },
                            "id_token": {},
                        },
                        "nonce": nonce,
                        "state": state,
                        "claimsLocales": "en",
                        "codeChallenge": code_challenge,
                        "codeChallengeMethod": "S256",
                    },
                }
                oauth_check_response = await client.post(
                    f"{self.settings.esignet_api_url}/v1/esignet/authorization/v3/oauth-details",
                    headers=headers,
                    json=oauth_check_body,
                )
                oauth_check_response.raise_for_status()
                oauth_check_payload = oauth_check_response.json()
                if oauth_check_payload.get("errors"):
                    last_error_message = _format_esignet_errors(oauth_check_payload)
                    continue

                if oauth_check_payload.get("response", {}).get("transactionId"):
                    authorize_url = f"{self.settings.esignet_ui_url}/authorize?{urlencode({'nonce': nonce,'state': state,'client_id': client_id,'redirect_uri': self.settings.esignet_callback_url,'scope': 'openid profile','response_type': 'code','acr_values': 'mosip:idp:acr:generated-code','claims_locales': 'en','ui_locales': 'en-IN','code_challenge': code_challenge,'code_challenge_method': 'S256'})}"
                    return {
                        "session_token": session_token,
                        "state": state,
                        "nonce": nonce,
                        "client_id": client_id,
                        "private_key_pem": private_key_pem,
                        "code_verifier": code_verifier,
                        "authorize_url": authorize_url,
                    }

            raise RuntimeError(
                "Could not create a browser-usable eSignet client for RefuPass verification. "
                f"eSignet said: {last_error_message}"
            )

    async def complete_verification(
        self,
        *,
        client_id: str,
        private_key_pem: str,
        code_verifier: str,
        code: str,
    ) -> dict[str, str]:
        openid_config_url = f"{self.settings.esignet_ui_url}/.well-known/openid-configuration"
        async with httpx.AsyncClient(timeout=20.0) as client:
            openid_response = await client.get(openid_config_url)
            openid_response.raise_for_status()
            openid_config = openid_response.json()
            token_endpoint = openid_config.get("token_endpoint")
            userinfo_endpoint = openid_config.get("userinfo_endpoint")
            if not token_endpoint:
                raise RuntimeError("eSignet openid configuration is missing the token endpoint.")

            now = datetime.now(UTC)
            client_assertion = jwt.encode(
                {
                    "iss": client_id,
                    "sub": client_id,
                    "aud": token_endpoint,
                    "jti": str(uuid4()),
                    "iat": int(now.timestamp()),
                    "exp": int((now + timedelta(minutes=5)).timestamp()),
                },
                private_key_pem,
                algorithm="RS256",
            )
            token_response = await client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.settings.esignet_callback_url,
                    "client_id": client_id,
                    "code_verifier": code_verifier,
                    "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                    "client_assertion": client_assertion,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            token_response.raise_for_status()
            token_payload = token_response.json()

            verified_subject = None
            id_token = token_payload.get("id_token")
            if id_token:
                claims = jwt.decode(
                    id_token,
                    options={
                        "verify_signature": False,
                        "verify_aud": False,
                        "verify_exp": False,
                    },
                )
                verified_subject = claims.get("sub")

            if not verified_subject and token_payload.get("access_token") and userinfo_endpoint:
                userinfo_response = await client.get(
                    userinfo_endpoint,
                    headers={"Authorization": f"Bearer {token_payload['access_token']}"},
                )
                userinfo_response.raise_for_status()
                content_type = userinfo_response.headers.get("content-type", "")
                if "application/json" in content_type:
                    userinfo = userinfo_response.json()
                else:
                    userinfo = jwt.decode(
                        userinfo_response.text,
                        options={
                            "verify_signature": False,
                            "verify_aud": False,
                            "verify_exp": False,
                        },
                    )
                verified_subject = verified_subject or userinfo.get("sub")

        if not verified_subject:
            raise RuntimeError("eSignet verification completed but no subject identifier was returned.")

        return {
            "auth_subject": str(verified_subject),
            "identity_provider": "local_esignet_mock",
        }
