import io
import json
import os
import threading
import time
from urllib.error import URLError

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient

from cobri.config import Settings
from Cobri.backend.src.cobri.identity.auth import TokenVerifier
from Cobri.backend.src.cobri.main import create_app

ISSUER = "https://identity.example.test"
AUDIENCE = "cobri-api"
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for name in os.environ:
        if name.startswith("COBRI_"):
            monkeypatch.delenv(name)


@pytest.fixture(scope="module")
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def settings(**overrides):
    values = {
        "auth_issuer": ISSUER,
        "auth_audience": AUDIENCE,
        "auth_jwks_url": JWKS_URL,
    }
    return Settings(_env_file=None, **(values | overrides))


def jwk(key, *, algorithm="RS256", kid="key-1"):
    converter = jwt.algorithms.RSAAlgorithm if algorithm == "RS256" else jwt.algorithms.ECAlgorithm
    value = json.loads(converter.to_jwk(key.public_key()))
    return value | {"kid": kid, "alg": algorithm, "use": "sig"}


def token(key, *, algorithm="RS256", kid="key-1", claims=None, omit=()):
    payload = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "learner-123",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()) - 1,
    } | (claims or {})
    for name in omit:
        payload.pop(name, None)
    return jwt.encode(payload, key, algorithm=algorithm, headers={"kid": kid})


def mock_jwks(monkeypatch, *documents):
    calls = []

    def open_url(request, **kwargs):
        calls.append((request.full_url, kwargs))
        document = documents[min(len(calls) - 1, len(documents) - 1)]
        if isinstance(document, Exception):
            raise document
        data = document if isinstance(document, bytes) else json.dumps(document).encode()
        return io.BytesIO(data)

    monkeypatch.setattr("jwt.jwks_client.urllib.request.urlopen", open_url)
    return calls


def assert_unauthorized(verifier, access_token):
    with pytest.raises(HTTPException) as error:
        verifier.verify(access_token)
    assert error.value.status_code == 401
    assert error.value.headers == {"WWW-Authenticate": "Bearer"}


def test_real_signature_and_principal_and_jwks_cache(monkeypatch, rsa_key):
    calls = mock_jwks(monkeypatch, {"keys": [jwk(rsa_key)]})
    verifier = TokenVerifier(settings())
    access_token = token(rsa_key)
    principal = verifier.verify(access_token)
    assert principal.model_dump() == {"issuer": ISSUER, "subject": "learner-123"}
    assert verifier.verify(access_token) == principal
    assert len(calls) == 1
    assert calls[0][0] == JWKS_URL
    assert calls[0][1]["timeout"] == 5


def test_expired_key_cache_is_refetched(monkeypatch, rsa_key):
    calls = mock_jwks(monkeypatch, {"keys": [jwk(rsa_key)]})
    verifier = TokenVerifier(settings(auth_jwks_cache_seconds=1))
    verifier.verify(token(rsa_key))
    # Advance only PyJWT's cache clock; JWT claim verification retains real UTC time.
    now = time.monotonic()
    monkeypatch.setattr("jwt.jwk_set_cache.time.monotonic", lambda: now + 2)
    verifier.verify(token(rsa_key))
    assert len(calls) == 2


def test_rotated_key_is_loaded_after_cache_miss(monkeypatch, rsa_key):
    calls = mock_jwks(
        monkeypatch,
        {"keys": [jwk(rsa_key, kid="old-key")]},
        {"keys": [jwk(rsa_key, kid="new-key")]},
    )
    principal = TokenVerifier(settings()).verify(token(rsa_key, kid="new-key"))
    assert principal.subject == "learner-123"
    assert len(calls) == 2


def test_unknown_key_is_401_after_bounded_refresh(monkeypatch, rsa_key):
    calls = mock_jwks(monkeypatch, {"keys": [jwk(rsa_key)]})
    assert_unauthorized(TokenVerifier(settings()), token(rsa_key, kid="unknown"))
    assert len(calls) == 2


def test_es256_requires_explicit_configuration(monkeypatch):
    key = ec.generate_private_key(ec.SECP256R1())
    calls = mock_jwks(monkeypatch, {"keys": [jwk(key, algorithm="ES256")]})
    access_token = token(key, algorithm="ES256")
    assert_unauthorized(TokenVerifier(settings()), access_token)
    assert not calls
    assert TokenVerifier(settings(auth_algorithms=["ES256"])).verify(access_token).subject


@pytest.mark.parametrize(
    "claims",
    [
        {"exp": 1},
        {"iss": "https://other.example.test"},
        {"aud": "other-api"},
        {"sub": ""},
        {"sub": 42},
        {"nbf": 9999999999},
        {"iat": 9999999999},
    ],
)
def test_bad_claims_fail_verification(monkeypatch, rsa_key, claims):
    mock_jwks(monkeypatch, {"keys": [jwk(rsa_key)]})
    assert_unauthorized(TokenVerifier(settings()), token(rsa_key, claims=claims))


@pytest.mark.parametrize("claim", ["iss", "aud", "sub", "exp"])
def test_required_claims_cannot_be_omitted(monkeypatch, rsa_key, claim):
    mock_jwks(monkeypatch, {"keys": [jwk(rsa_key)]})
    assert_unauthorized(TokenVerifier(settings()), token(rsa_key, omit=[claim]))


def test_wrong_signature_fails(monkeypatch, rsa_key):
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    mock_jwks(monkeypatch, {"keys": [jwk(rsa_key)]})
    assert_unauthorized(TokenVerifier(settings()), token(wrong_key))


def test_hmac_cannot_expand_algorithm_allowlist(monkeypatch):
    calls = mock_jwks(monkeypatch, {})
    access_token = token("not-a-real-secret-but-long-enough-for-hmac", algorithm="HS256")
    assert_unauthorized(TokenVerifier(settings()), access_token)
    assert not calls


@pytest.mark.parametrize("access_token", ["", "not-a-jwt", "x" * 16385])
def test_malformed_tokens_are_401(access_token):
    assert_unauthorized(TokenVerifier(settings()), access_token)


@pytest.mark.parametrize(
    "document",
    [
        URLError("provider unavailable"),
        b"not json",
        [],
        {"keys": []},
        {"keys": [None]},
    ],
)
def test_jwks_infrastructure_failure_is_503(monkeypatch, rsa_key, document):
    mock_jwks(monkeypatch, document)
    with pytest.raises(HTTPException) as error:
        TokenVerifier(settings()).verify(token(rsa_key))
    assert error.value.status_code == 503
    assert error.value.detail["code"] == "authentication_unavailable"


def test_unknown_keys_share_a_bounded_forced_refresh(monkeypatch, rsa_key):
    calls = mock_jwks(monkeypatch, {"keys": [jwk(rsa_key)]})
    verifier = TokenVerifier(settings())
    assert_unauthorized(verifier, token(rsa_key, kid="unknown-1"))
    assert_unauthorized(verifier, token(rsa_key, kid="unknown-2"))
    assert len(calls) == 2
    assert verifier.verify(token(rsa_key)).subject == "learner-123"
    assert len(calls) == 2


def test_missing_auth_configuration_is_503():
    with pytest.raises(HTTPException) as error:
        TokenVerifier(Settings(_env_file=None)).verify("unverified-token")
    assert error.value.status_code == 503


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Basic abc"}])
def test_http_requires_bearer_authentication(headers):
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_http_runs_crypto_in_worker_thread_and_returns_verified_identity(monkeypatch, rsa_key):
    mock_jwks(monkeypatch, {"keys": [jwk(rsa_key)]})
    app = create_app(settings())
    threads = []
    real_verify = app.state.token_verifier.verify

    def recording_verify(value):
        threads.append(threading.current_thread().name)
        return real_verify(value)

    monkeypatch.setattr(app.state.token_verifier, "verify", recording_verify)
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token(rsa_key)}"}
        )
    assert response.status_code == 200
    assert response.json() == {"issuer": ISSUER, "subject": "learner-123"}
    assert threads and all("worker" in name.lower() for name in threads)
