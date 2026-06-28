import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.services.llm_provider import LLMProviderError, OpenAILLMProvider


def main() -> None:
    if not settings.openai_api_key:
        print("OPENAI_API_KEY is missing.")
        print("Add your key to backend/.env first.")
        return

    provider = OpenAILLMProvider()

    try:
        reply = provider.generate_reply(
            message=(
                "Hello Akon. Reply in one short paragraph and confirm that the real "
                "OpenAI provider is working."
            ),
            safety_level="S0",
            detected_emotion=None,
            memory_context="No relevant saved memory.",
        )
    except LLMProviderError as exc:
        print("OpenAI smoke test failed.")
        print(str(exc))
        return

    print("OpenAI smoke test passed.")
    print()
    print(reply)


if __name__ == "__main__":
    main()