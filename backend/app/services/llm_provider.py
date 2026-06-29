from abc import ABC, abstractmethod

from openai import OpenAI

from app.core.config import settings
from app.core.system_prompt import AKON_SYSTEM_PROMPT


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
        memory_note = ""

        if memory_context:
            memory_note = (
                "\n\nI’m also taking into account what you’ve asked me to remember."
            )

        if detected_emotion == "angry":
            return (
                "I hear the frustration. Let’s cut the noise and deal with the next useful step. "
                "Tell me exactly what failed, what you expected to happen, and what actually happened."
                f"{memory_note}"
            )

        if detected_emotion in {"anxious", "overwhelmed", "stressed"}:
            return (
                "It sounds like your mind is carrying too much at once. "
                "Let’s slow it down and choose one small step. "
                "What is the one thing you need to handle first?"
                f"{memory_note}"
            )

        if detected_emotion in {"sad", "lonely"}:
            return (
                "That sounds painful, and I won’t pretend it is small. "
                "But we can separate what hurts from what you can do next. "
                "What happened that made you feel this way?"
                f"{memory_note}"
            )

        if detected_emotion == "confused":
            return (
                "That sounds unclear from the inside. Let's untangle it gently. "
                "What is the part that feels most confusing right now?"
                f"{memory_note}"
            )

        if detected_emotion in {"hopeful", "calm"}:
            return (
                "There is something steady in that. Let's use it carefully. "
                "What would feel like the next honest step from here?"
                f"{memory_note}"
            )

        return (
            "I’m here with you. Tell me what is going on, and I’ll help you think through it "
            "clearly, step by step, without judgment and without rushing you."
            f"{memory_note}"
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
