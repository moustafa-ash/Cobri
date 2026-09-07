"""Application settings; secrets stay in environment variables or the ignored .env."""

from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="COBRI_",
        env_file=ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Cobri", min_length=1, max_length=100)
    auth_issuer: str | None = None
    auth_audience: str | None = None
    auth_jwks_url: str | None = None
    auth_algorithms: list[Literal["RS256", "ES256"]] = Field(
        default_factory=lambda: ["RS256"], min_length=1, max_length=2
    )
    auth_jwks_timeout_seconds: float = Field(default=5, gt=0, le=30)
    auth_jwks_cache_seconds: int = Field(default=300, ge=1, le=3600)
    auth_clock_skew_seconds: int = Field(default=0, ge=0, le=120)

    @field_validator("auth_issuer", "auth_audience", "auth_jwks_url", mode="before")
    @classmethod
    def blank_auth_is_unconfigured(cls, value: object) -> object:
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("auth_issuer", "auth_jwks_url")
    @classmethod
    def require_trusted_https_url(cls, value: str | None) -> str | None:
        if value is not None:
            parsed = urlsplit(value)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.fragment
                or parsed.query
                or any(character.isspace() for character in value)
            ):
                raise ValueError("Use a trusted HTTPS URL without credentials, query, or fragment")
        return value

    @model_validator(mode="after")
    def require_complete_auth_configuration(self) -> Self:
        configured = (self.auth_issuer, self.auth_audience, self.auth_jwks_url)
        if any(configured) and not all(configured):
            raise ValueError("Configure auth_issuer, auth_audience, and auth_jwks_url together")
        if len(set(self.auth_algorithms)) != len(self.auth_algorithms):
            raise ValueError("auth_algorithms must not contain duplicates")
        return self

    @property
    def auth_configured(self) -> bool:
        return bool(self.auth_issuer and self.auth_audience and self.auth_jwks_url)
