from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.services.akon_engine import generate_akon_reply
from app.services.safety_service import classify_safety


def main() -> None:
    if settings.default_ai_provider == "mock":
        raise RuntimeError(
            "DEFAULT_AI_PROVIDER is currently mock. Set it to gemini or openai before running this smoke test."
        )

    if settings.default_ai_provider == "openai" and not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    if settings.default_ai_provider == "gemini" and not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is missing.")

    test_message = (
        "Good morning Akon. Give me one intelligent sentence to confirm the real AI provider is working."
    )

    safety_result = classify_safety(test_message)

    reply = generate_akon_reply(
        message=test_message,
        safety_result=safety_result,
        memory_context=None,
    )

    model = (
        settings.gemini_model
        if settings.default_ai_provider == "gemini"
        else settings.openai_model
    )

    print("\n=== Akon AI Provider Smoke Test ===")
    print(f"Provider: {settings.default_ai_provider}")
    print(f"Model: {model}")
    print(f"Fallback allowed: {settings.allow_ai_fallback}")
    print(f"Safety level: {safety_result['level']}")
    print("\nReply:")
    print(reply)
    print("\nAI provider smoke test completed.")


if __name__ == "__main__":
    main()