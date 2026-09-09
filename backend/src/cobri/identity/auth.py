"""Verify externally issued JWTs; this module never issues tokens or creates users."""

from threading import Lock
from time import monotonic
from typing import Annotated

import jwt
from fastapi import HTTPException, Request, Security, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from cobri.config import Settings

bearer = HTTPBearer(auto_error=False)


class Principal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issuer: str = Field(min_length=1)
    subject: str = Field(min_length=1)


def authentication_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"code": "authentication_unavailable", "message": "Authentication is unavailable"},
    )


def invalid_token() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "invalid_token", "message": "Invalid or expired access token"},
        headers={"WWW-Authenticate": "Bearer"},
    )


class TokenVerifier:
    """Synchronous crypto/JWKS boundary; call through a threadpool from async code.

    Cache the full key set for a finite TTL, not individual keys indefinitely.
    An unknown kid causes at most one forced refresh for that verification.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = Lock()
        self._last_forced_refresh = 0.0
        self._forced_refresh_cooldown = min(30, settings.auth_jwks_cache_seconds)
        self._jwks = (
            jwt.PyJWKClient(
                settings.auth_jwks_url,
                cache_keys=False,
                cache_jwk_set=True,
                lifespan=settings.auth_jwks_cache_seconds,
                timeout=settings.auth_jwks_timeout_seconds,
            )
            if settings.auth_configured
            else None
        )

    def _signing_keys(self, *, refresh: bool = False) -> list[jwt.PyJWK]:
        assert self._jwks is not None
        try:
            return self._jwks.get_signing_keys(refresh=refresh)
        except (jwt.PyJWTError, OSError, ValueError, TypeError, KeyError, AttributeError):
            # Do not expose provider responses, token data, or internal URLs.
            raise authentication_unavailable() from None

    @staticmethod
    def _matching_key(keys: list[jwt.PyJWK], key_id: str) -> jwt.PyJWK | None:
        matches = [key for key in keys if key.key_id == key_id]
        if len(matches) > 1:
            raise authentication_unavailable()
        return matches[0] if matches else None

    def _key_for(self, key_id: str) -> jwt.PyJWK:
        # Known cached keys do not wait behind a provider request for an unknown kid.
        key = self._matching_key(self._signing_keys(), key_id)
        if key is not None:
            return key
        with self._lock:
            # Another request may have refreshed while this request waited.
            key = self._matching_key(self._signing_keys(), key_id)
            if key is not None:
                return key
            now = monotonic()
            if now - self._last_forced_refresh < self._forced_refresh_cooldown:
                raise invalid_token()
            self._last_forced_refresh = now
            key = self._matching_key(self._signing_keys(refresh=True), key_id)
            if key is not None:
                return key
        raise invalid_token()

    def verify(self, token: str) -> Principal:
        if self._jwks is None:
            raise authentication_unavailable()
        if not token or len(token) > 16384:
            raise invalid_token()
        try:
            header = jwt.get_unverified_header(token)
            # The header may select a key, but it cannot expand configured algorithms.
            algorithm = header.get("alg")
            key_id = header.get("kid")
            if (
                algorithm not in self.settings.auth_algorithms
                or not isinstance(key_id, str)
                or not key_id
                or len(key_id) > 256
            ):
                raise invalid_token()
            key = self._key_for(key_id)
            if key.algorithm_name != algorithm:
                raise invalid_token()
            claims = jwt.decode(
                token,
                key.key,
                algorithms=self.settings.auth_algorithms,
                audience=self.settings.auth_audience,
                issuer=self.settings.auth_issuer,
                leeway=self.settings.auth_clock_skew_seconds,
                options={
                    "require": ["iss", "aud", "sub", "exp"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_iss": True,
                    "verify_aud": True,
                    "verify_sub": True,
                },
            )
            return Principal(issuer=claims["iss"], subject=claims["sub"])
        except (jwt.InvalidTokenError, jwt.InvalidKeyError, ValidationError, TypeError, ValueError):
            raise invalid_token() from None


async def get_current_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer)],
) -> Principal:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "authentication_required",
                "message": "A bearer access token is required",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    verifier: TokenVerifier = request.app.state.token_verifier
    return await run_in_threadpool(verifier.verify, credentials.credentials)
