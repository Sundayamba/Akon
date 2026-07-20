from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.services.akon_engine import generate_akon_reply
from app.services.safety_service import classify_safety


def main() -> None:
    if settings.default_ai_provider != "openai":
        raise RuntimeError(
            "DEFAULT_AI_PROVIDER must be set to openai before running this OpenAI smoke test. "
            "For Gemini or any active provider, run: python .\\scripts\\smoke_ai_provider.py"
        )

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    test_message = "Good morning Akon. Give me one short sentence to confirm you are working."

    safety_result = classify_safety(test_message)

    reply = generate_akon_reply(
        message=test_message,
        safety_result=safety_result,
        memory_context=None,
    )

    print("\n=== Akon OpenAI Smoke Test ===")
    print(f"Provider: {settings.default_ai_provider}")
    print(f"Model: {settings.openai_model}")
    print(f"Safety level: {safety_result['level']}")
    print("\nReply:")
    print(reply)
    print("\nOpenAI provider smoke test completed.")


if __name__ == "__main__":
    main()