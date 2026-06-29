from abc import ABC, abstractmethod

from openai import OpenAI

from app.core.config import settings
from app.core.system_prompt import AKON_SYSTEM_PROMPT
from app.services.support_strategy_service import build_support_reply


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider fails."""


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_reply(
        self,
        message: str,
        safety_level: str,
        detected_emotion: str | None,
        memory_context: str | None = None,
    ) -> str:
        raise NotImplementedError


class MockLLMProvider(BaseLLMProvider):
    def generate_reply(
        self,
        message: str,
        safety_level: str,
        detected_emotion: str | None,
        memory_context: str | None = None,
    ) -> str:
        return build_support_reply(
            user_message=message,
            detected_emotion=detected_emotion,
            safety_level=safety_level,
            memory_context=memory_context,
        )


class OpenAILLMProvider(BaseLLMProvider):
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise LLMProviderError("OPENAI_API_KEY is missing.")

        self.client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
        )
        self.model = settings.openai_model

    def generate_reply(
        self,
        message: str,
        safety_level: str,
        detected_emotion: str | None,
        memory_context: str | None = None,
    ) -> str:
        memory_block = memory_context or "No relevant saved memory."

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=AKON_SYSTEM_PROMPT,
                input=(
                    f"Safety level: {safety_level}\n"
                    f"Detected emotion: {detected_emotion or 'none'}\n\n"
                    f"Relevant saved memory:\n{memory_block}\n\n"
                    f"User message:\n{message}"
                ),
                max_output_tokens=settings.openai_max_output_tokens,
            )

            reply = getattr(response, "output_text", None)

            if not reply:
                raise LLMProviderError("OpenAI response did not include output_text.")

            return reply.strip()

        except Exception as exc:
            raise LLMProviderError(f"OpenAI provider failed: {exc}") from exc


def get_llm_provider() -> BaseLLMProvider:
    provider = settings.default_ai_provider.lower().strip()

    if provider == "mock":
        return MockLLMProvider()

    if provider == "openai":
        return OpenAILLMProvider()

    raise LLMProviderError(f"Unsupported AI provider: {settings.default_ai_provider}")
