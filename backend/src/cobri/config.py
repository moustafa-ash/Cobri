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
    database_url: str = "sqlite+aiosqlite:///./.data/cobri.db"
    auto_create_schema: bool = True
    worker_poll_seconds: float = Field(default=1.0, gt=0, le=60)
    worker_lease_seconds: int = Field(default=60, ge=5, le=3600)
    worker_max_attempts: int = Field(default=3, ge=1, le=20)
    content_root: Path = Path(__file__).resolve().parents[3] / "content-packages"
    sandbox_enabled: bool = False
    sandbox_image: str = (
        "python:3.12-slim-bookworm@sha256:"
        "782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254"
    )
    sandbox_timeout_seconds: float = Field(default=3, gt=0, le=30)
    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-20b"
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openrouter/free"
    model_timeout_seconds: float = Field(default=30, gt=0, le=120)

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
        if self.sandbox_enabled and "@sha256:" not in self.sandbox_image:
            raise ValueError("sandbox_image must be pinned by digest when sandboxing is enabled")
        return self

    @property
    def auth_configured(self) -> bool:
        return bool(self.auth_issuer and self.auth_audience and self.auth_jwks_url)

    @property
    def model_configured(self) -> bool:
        return bool(self.groq_api_key or self.openrouter_api_key)
