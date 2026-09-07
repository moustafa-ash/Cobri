from pathlib import Path

import pytest
from pydantic import ValidationError

from cobri.config import ROOT_ENV_FILE, Settings


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    import os

    for name in os.environ:
        if name.startswith("COBRI_"):
            monkeypatch.delenv(name)


def configured_values():
    return {
        "auth_issuer": "https://identity.example.test",
        "auth_audience": "cobri-api",
        "auth_jwks_url": "https://identity.example.test/.well-known/jwks.json",
    }


def test_defaults_and_blank_auth_settings():
    settings = Settings(_env_file=None, auth_issuer=" ", auth_audience="", auth_jwks_url="")
    assert settings.app_name == "Cobri"
    assert settings.auth_algorithms == ["RS256"]
    assert not settings.auth_configured


def test_complete_auth_configuration():
    assert Settings(_env_file=None, **configured_values()).auth_configured


def test_partial_auth_configuration_fails():
    with pytest.raises(ValidationError, match="Configure auth_issuer"):
        Settings(_env_file=None, auth_issuer="https://identity.example.test")


@pytest.mark.parametrize(
    "url",
    [
        "http://identity.example.test/jwks",
        "file:///tmp/keys.json",
        "https:///missing-host",
        "https://user:password@identity.example.test/jwks",
        "https://identity.example.test/jwks#fragment",
        "https://identity.example.test/jwks?secret=value",
        "https://identity.example.test/a b",
    ],
)
def test_jwks_url_must_be_trusted_https(url):
    values = configured_values() | {"auth_jwks_url": url}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


@pytest.mark.parametrize(
    "overrides",
    [
        {"auth_algorithms": []},
        {"auth_algorithms": ["HS256"]},
        {"auth_algorithms": ["RS256", "RS256"]},
        {"auth_jwks_timeout_seconds": 0},
        {"auth_jwks_timeout_seconds": 31},
        {"auth_jwks_cache_seconds": 0},
        {"auth_jwks_cache_seconds": 3601},
        {"auth_clock_skew_seconds": -1},
        {"auth_clock_skew_seconds": 121},
    ],
)
def test_unsafe_configuration_fails(overrides):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **overrides)


def test_environment_overrides_dotenv_and_reserved_fields_are_ignored(tmp_path, monkeypatch):
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "COBRI_APP_NAME=From file\nCOBRI_DATABASE_URL=postgresql://future\n"
        "GROQ_API_KEY=not-a-real-secret\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("COBRI_APP_NAME", "From environment")
    monkeypatch.setenv("COBRI_AUTH_ALGORITHMS", '["RS256", "ES256"]')
    settings = Settings(_env_file=dotenv)
    assert settings.app_name == "From environment"
    assert settings.auth_algorithms == ["RS256", "ES256"]


def test_default_dotenv_location_does_not_depend_on_cwd(tmp_path, monkeypatch):
    expected = Path(__file__).resolve().parents[2] / ".env"
    monkeypatch.chdir(tmp_path)
    assert ROOT_ENV_FILE == expected
    assert Settings.model_config["env_file"] == expected
