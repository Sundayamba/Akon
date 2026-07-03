from app.core.config import settings


def _provider_configured() -> bool:
    if settings.default_ai_provider == "mock":
        return True

    if settings.default_ai_provider == "openai":
        return bool(settings.openai_api_key)

    if settings.default_ai_provider == "gemini":
        return bool(settings.gemini_api_key)

    return False


def root() -> dict[str, str]:
    return {
        "service": "akon-api",
        "name": settings.app_name,
        "version": settings.api_version,
        "environment": settings.app_env,
        "status": "ok",
    }


def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "akon-api",
    }


def version() -> dict[str, str | bool]:
    return {
        "service": "akon-api",
        "name": settings.app_name,
        "version": settings.api_version,
        "environment": settings.app_env,
        "ai_provider": settings.default_ai_provider,
        "ai_fallback_enabled": settings.allow_ai_fallback,
    }


def readiness() -> dict[str, str | bool | list[str]]:
    provider_ready = _provider_configured()

    return {
        "status": "ready" if provider_ready else "degraded",
        "service": "akon-api",
        "version": settings.api_version,
        "environment": settings.app_env,
        "database": "configured",
        "ai_provider": settings.default_ai_provider,
        "ai_provider_configured": provider_ready,
        "ai_fallback_enabled": settings.allow_ai_fallback,
        "cors_origins": settings.cors_allowed_origins_list,
    }