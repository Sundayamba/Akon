from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Akon"
    app_env: str = "development"

    default_ai_provider: str = "mock"

    openai_api_key: str | None = None
    openai_model: str = "gpt-5.5"
    openai_timeout_seconds: float = 30.0
    openai_max_output_tokens: int = 700

    gemini_api_key: str | None = None
    gemini_model: str | None = None

    database_url: str = "sqlite:///./akon.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()