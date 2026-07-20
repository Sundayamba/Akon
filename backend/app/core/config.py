from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


AppEnvironment = Literal["development", "test", "production"]
AIProvider = Literal["mock", "openai", "gemini"]


DEFAULT_DEV_SECRET = "change-this-dev-secret-before-production"


class Settings(BaseSettings):
    app_name: str = "Akon"
    app_env: AppEnvironment = "development"
    api_version: str = "0.5.7"

    secret_key: str = DEFAULT_DEV_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    auth_rate_limit_max_attempts: int = 5
    auth_rate_limit_window_seconds: int = 60

    default_ai_provider: AIProvider = "mock"
    allow_ai_fallback: bool = True

    openai_api_key: str | None = None
    openai_model: str = "gpt-5.5"
    openai_timeout_seconds: float = 30.0
    openai_max_output_tokens: int = 900

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_max_output_tokens: int = 1200

    database_url: str = "sqlite:///./akon.db"

    public_frontend_url: str | None = None
    cors_allowed_origins: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:5173,"
        "http://127.0.0.1:5173"
    )
    trusted_hosts: str = "localhost,127.0.0.1,testserver,*.onrender.com"
    expose_docs: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        origins = [
            origin.strip().rstrip("/")
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]

        if self.public_frontend_url:
            origins.append(self.public_frontend_url.strip().rstrip("/"))

        return sorted(set(origins))

    @property
    def trusted_hosts_list(self) -> list[str]:
        return [
            host.strip()
            for host in self.trusted_hosts.split(",")
            if host.strip()
        ]

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_app_env(cls, value: str) -> str:
        normalized = str(value).lower().strip()

        if normalized not in {"development", "test", "production"}:
            raise ValueError(
                "APP_ENV must be one of: development, test, production."
            )

        return normalized

    @field_validator("default_ai_provider", mode="before")
    @classmethod
    def normalize_default_ai_provider(cls, value: str) -> str:
        normalized = str(value).lower().strip()

        if normalized not in {"mock", "openai", "gemini"}:
            raise ValueError(
                "DEFAULT_AI_PROVIDER must be one of: mock, openai, gemini."
            )

        return normalized

    @field_validator("api_version", mode="before")
    @classmethod
    def normalize_api_version(cls, value: str) -> str:
        normalized = str(value).strip()

        if not normalized:
            raise ValueError("API_VERSION cannot be empty.")

        return normalized

    @field_validator("openai_model", mode="before")
    @classmethod
    def normalize_openai_model(cls, value: str) -> str:
        normalized = str(value).strip()

        if not normalized:
            raise ValueError("OPENAI_MODEL cannot be empty.")

        return normalized

    @field_validator("gemini_model", mode="before")
    @classmethod
    def normalize_gemini_model(cls, value: str) -> str:
        normalized = str(value).strip()

        if not normalized:
            raise ValueError("GEMINI_MODEL cannot be empty.")

        return normalized

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def normalize_openai_api_key(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()
        return normalized or None

    @field_validator("gemini_api_key", mode="before")
    @classmethod
    def normalize_gemini_api_key(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()
        return normalized or None

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        normalized = str(value).strip()

        if not normalized:
            raise ValueError("DATABASE_URL cannot be empty.")

        if normalized.startswith("postgres://"):
            normalized = normalized.replace(
                "postgres://",
                "postgresql://",
                1,
            )

        return normalized

    @field_validator("public_frontend_url", mode="before")
    @classmethod
    def normalize_public_frontend_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip().rstrip("/")
        return normalized or None

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def normalize_cors_allowed_origins(cls, value: str) -> str:
        normalized = str(value).strip()

        if not normalized:
            raise ValueError("CORS_ALLOWED_ORIGINS cannot be empty.")

        return normalized

    @field_validator("trusted_hosts", mode="before")
    @classmethod
    def normalize_trusted_hosts(cls, value: str) -> str:
        normalized = str(value).strip()

        if not normalized:
            raise ValueError("TRUSTED_HOSTS cannot be empty.")

        return normalized

    @model_validator(mode="after")
    def validate_runtime_configuration(self) -> "Settings":
        if self.access_token_expire_minutes <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0.")

        if self.auth_rate_limit_max_attempts <= 0:
            raise ValueError("AUTH_RATE_LIMIT_MAX_ATTEMPTS must be greater than 0.")

        if self.auth_rate_limit_window_seconds <= 0:
            raise ValueError("AUTH_RATE_LIMIT_WINDOW_SECONDS must be greater than 0.")

        if self.openai_timeout_seconds <= 0:
            raise ValueError("OPENAI_TIMEOUT_SECONDS must be greater than 0.")

        if self.openai_max_output_tokens <= 0:
            raise ValueError("OPENAI_MAX_OUTPUT_TOKENS must be greater than 0.")

        if self.gemini_max_output_tokens <= 0:
            raise ValueError("GEMINI_MAX_OUTPUT_TOKENS must be greater than 0.")

        if self.default_ai_provider == "openai" and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when DEFAULT_AI_PROVIDER=openai."
            )

        if self.default_ai_provider == "gemini" and not self.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is required when DEFAULT_AI_PROVIDER=gemini."
            )

        if self.app_env == "production":
            if self.database_url.startswith("sqlite"):
                raise ValueError(
                    "Production requires a persistent PostgreSQL DATABASE_URL. "
                    "SQLite storage can be lost during redeployment."
                )

            if self.secret_key == DEFAULT_DEV_SECRET:
                raise ValueError(
                    "SECRET_KEY must be changed before running in production."
                )

            if self.default_ai_provider == "mock":
                raise ValueError(
                    "DEFAULT_AI_PROVIDER=mock is not allowed in production."
                )

            if "*" in self.cors_allowed_origins_list:
                raise ValueError(
                    "Wildcard CORS origins are not allowed in production."
                )

            if not self.public_frontend_url:
                raise ValueError(
                    "PUBLIC_FRONTEND_URL is required in production."
                )

            if not self.public_frontend_url.startswith(("https://", "http://")):
                raise ValueError(
                    "PUBLIC_FRONTEND_URL must start with http:// or https://."
                )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
