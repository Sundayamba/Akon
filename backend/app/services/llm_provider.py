from abc import ABC, abstractmethod
from typing import Literal

from openai import OpenAI

from app.core.config import settings
from app.core.system_prompt import AKON_SYSTEM_PROMPT
from app.services.support_strategy_service import build_support_reply


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider fails."""


ResponsePosture = Literal[
    "general",
    "learning",
    "research",
    "planning",
    "writing",
    "technical",
    "decision",
    "casual",
    "emotional_support",
]


POSTURE_INSTRUCTIONS: dict[ResponsePosture, str] = {
    "general": (
        "Answer the user's actual request directly and naturally. Be helpful, clear, "
        "and practical. Do not assume the user is emotionally distressed."
    ),
    "learning": (
        "Act like a clear tutor. Explain step by step, use simple examples, and help "
        "the user understand the topic. If the user asks for depth, expand. If not, "
        "keep it focused."
    ),
    "research": (
        "Act like a research assistant. Organize the answer clearly, separate facts "
        "from assumptions, and say when fresh verification is needed."
    ),
    "planning": (
        "Act like a practical planner. Give realistic priorities, steps, sequencing, "
        "constraints, and next actions."
    ),
    "writing": (
        "Act like a writing assistant. If the user asks for a message, email, caption, "
        "letter, speech, announcement, or wording, produce a usable draft immediately "
        "when enough context exists. Do not merely say you can help."
    ),
    "technical": (
        "Act like a technical assistant. Diagnose clearly, give exact commands, code, "
        "file-level guidance, or test steps when useful. Avoid unnecessary emotional language."
    ),
    "decision": (
        "Act like a decision assistant. Compare options, tradeoffs, risks, benefits, "
        "timing, and give a clear recommendation when enough information exists."
    ),
    "casual": (
        "Respond naturally and lightly. Treat the message as normal conversation, not "
        "as emotional support."
    ),
    "emotional_support": (
        "Respond with warm support. Validate briefly, avoid clinical language, and guide "
        "toward one clear next step."
    ),
}


def _normalize_message(message: str) -> str:
    return " ".join(message.lower().strip().split())


def _fallback_posture_from_message(message: str) -> ResponsePosture:
    """
    Lightweight fallback only.

    The Akon engine should normally pass response_posture explicitly. This exists
    so direct provider calls and tests still behave reasonably.
    """
    normalized = _normalize_message(message)

    if any(
        signal in normalized
        for signal in {
            "code",
            "error",
            "traceback",
            "python",
            "react",
            "fastapi",
            "typescript",
            "pytest",
            "git",
            "backend",
            "frontend",
            "api",
            "database",
            "sql",
        }
    ):
        return "technical"

    if any(
        signal in normalized
        for signal in {
            "write",
            "rewrite",
            "draft",
            "compose",
            "message",
            "email",
            "letter",
            "caption",
            "speech",
            "announcement",
        }
    ):
        return "writing"

    if any(
        signal in normalized
        for signal in {
            "explain",
            "teach",
            "learn",
            "study",
            "what is",
            "how does",
            "step by step",
        }
    ):
        return "learning"

    if any(
        signal in normalized
        for signal in {
            "research",
            "analyze",
            "compare",
            "latest",
            "trend",
            "source",
            "report",
        }
    ):
        return "research"

    if any(
        signal in normalized
        for signal in {
            "plan",
            "schedule",
            "roadmap",
            "routine",
            "strategy",
            "next step",
        }
    ):
        return "planning"

    if any(
        signal in normalized
        for signal in {
            "should i",
            "which one",
            "choose",
            "decide",
            "worth it",
            "pros and cons",
        }
    ):
        return "decision"

    if normalized in {
        "hi",
        "hello",
        "hey",
        "yo",
        "morning",
        "good morning",
        "goo morning",
        "good afternoon",
        "good evening",
        "how are you",
        "how are you doing",
        "how you doing",
        "what's up",
        "whats up",
    }:
        return "casual"

    if any(
        signal in normalized
        for signal in {
            "i feel",
            "i am sad",
            "i'm sad",
            "i am stressed",
            "i'm stressed",
            "i feel betrayed",
            "i feel lost",
            "i feel lonely",
            "i am overwhelmed",
            "i'm overwhelmed",
            "hopeless",
            "heartbroken",
        }
    ):
        return "emotional_support"

    return "general"


def _build_casual_mock_reply(message: str) -> str:
    normalized = _normalize_message(message)

    if "morning" in normalized:
        return "Good morning. I’m doing well and ready to help. How is your morning going?"

    if "afternoon" in normalized:
        return "Good afternoon. I’m here and ready when you are. How is your day going?"

    if "evening" in normalized:
        return "Good evening. I’m doing well and ready to help. How has your day been?"

    if "how are you" in normalized or "how you doing" in normalized:
        return "I’m doing well and ready to help. What are you working on today?"

    return "Hey. I’m here and ready. What would you like us to do today?"


def _build_writing_mock_reply(message: str) -> str:
    normalized = _normalize_message(message)

    if "team" in normalized and ("motivat" in normalized or "encourage" in normalized):
        return (
            "Here’s a message you can send:\n\n"
            "Good morning team,\n\n"
            "I want to encourage everyone to stay focused, disciplined, and committed. "
            "Every effort we put in matters, every customer we serve matters, and every "
            "sale brings us closer to our goal.\n\n"
            "Let’s keep pushing with positive energy, teamwork, and consistency. I believe "
            "in this team, and I know we can achieve stronger results when we all give our best.\n\n"
            "Let’s make this period productive and successful for all of us."
        )

    if "manager" in normalized or "boss" in normalized:
        return (
            "Here’s a professional message you can send:\n\n"
            "Good day,\n\n"
            "I hope you are doing well. I would like to respectfully discuss an important "
            "matter with you when you have time. I believe it would be best for us to talk "
            "clearly and constructively so we can handle it properly.\n\n"
            "Please let me know a convenient time.\n\n"
            "Thank you."
        )

    return (
        "Here’s a clean draft you can use:\n\n"
        "Hello,\n\n"
        "I hope you are doing well. I wanted to share this message clearly and respectfully. "
        "Thank you for your time, effort, and attention. I believe we can move forward "
        "positively and achieve a good result together.\n\n"
        "Best regards."
    )


def _build_mock_reply(
    *,
    message: str,
    safety_level: str,
    detected_emotion: str | None,
    memory_context: str | None,
    response_posture: ResponsePosture,
) -> str:
    if response_posture == "emotional_support":
        return build_support_reply(
            user_message=message,
            detected_emotion=detected_emotion,
            safety_level=safety_level,
            memory_context=memory_context,
        )

    if response_posture == "casual":
        return _build_casual_mock_reply(message)

    if response_posture == "writing":
        return _build_writing_mock_reply(message)

    if response_posture == "learning":
        return (
            "I can help you learn this step by step.\n\n"
            "Send me the exact topic or question, and I’ll explain it clearly with examples "
            "and practice points."
        )

    if response_posture == "research":
        return (
            "I can help you structure the research.\n\n"
            "Send the topic, and I’ll organize it into key questions, comparison points, "
            "evidence to look for, and a clean summary."
        )

    if response_posture == "planning":
        return (
            "I can help you build a clear plan.\n\n"
            "Let’s define the goal, deadline, constraints, priorities, and the first practical step."
        )

    if response_posture == "technical":
        return (
            "I can help troubleshoot this directly.\n\n"
            "Send the exact error, file, command output, or code section, and I’ll guide you "
            "through the fix step by step."
        )

    if response_posture == "decision":
        return (
            "I can help you decide.\n\n"
            "Let’s compare the options by cost, risk, benefit, timing, and what matters most."
        )

    return "I can help with that. Tell me what you want to do, and I’ll respond directly."


def _build_openai_input(
    *,
    message: str,
    safety_level: str,
    detected_emotion: str | None,
    memory_context: str | None,
    response_posture: ResponsePosture,
) -> str:
    memory_block = memory_context.strip() if memory_context else "<none>"
    posture_instruction = POSTURE_INSTRUCTIONS[response_posture]

    return (
        f"Safety level: {safety_level}\n"
        f"Detected emotion: {detected_emotion or 'none'}\n"
        f"Internal response posture: {response_posture}\n\n"
        f"Response guidance:\n{posture_instruction}\n\n"
        "Important behavior rules:\n"
        "- Answer the user's actual request directly.\n"
        "- Do not assume emotional distress by default.\n"
        "- Use emotional-support language only when response posture is emotional_support "
        "or when safety requires it.\n"
        "- If the user asks for a message, email, caption, letter, announcement, or speech, "
        "produce the draft immediately when enough context exists.\n"
        "- If the user greets you casually, reply naturally like a normal companion.\n"
        "- If the user asks for learning, research, planning, technical help, or a decision, "
        "respond in that useful posture.\n"
        "- Do not mention saved memory, saved context, or old details unless they are directly "
        "useful for answering the user's current request.\n\n"
        f"Relevant saved memory:\n{memory_block}\n\n"
        f"User message:\n{message}"
    )


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_reply(
        self,
        message: str,
        safety_level: str,
        detected_emotion: str | None,
        memory_context: str | None = None,
        response_posture: ResponsePosture | None = None,
    ) -> str:
        raise NotImplementedError


class MockLLMProvider(BaseLLMProvider):
    def generate_reply(
        self,
        message: str,
        safety_level: str,
        detected_emotion: str | None,
        memory_context: str | None = None,
        response_posture: ResponsePosture | None = None,
    ) -> str:
        posture = response_posture or _fallback_posture_from_message(message)

        return _build_mock_reply(
            message=message,
            safety_level=safety_level,
            detected_emotion=detected_emotion,
            memory_context=memory_context,
            response_posture=posture,
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
        response_posture: ResponsePosture | None = None,
    ) -> str:
        posture = response_posture or _fallback_posture_from_message(message)

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=AKON_SYSTEM_PROMPT,
                input=_build_openai_input(
                    message=message,
                    safety_level=safety_level,
                    detected_emotion=detected_emotion,
                    memory_context=memory_context,
                    response_posture=posture,
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