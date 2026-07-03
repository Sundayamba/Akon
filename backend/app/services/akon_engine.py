from typing import Any, Literal

from app.core.config import settings
from app.services.llm_provider import LLMProviderError, get_llm_provider
from app.services.support_strategy_service import build_grounding_line, build_support_reply


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


LEARNING_SIGNALS = {
    "explain",
    "teach",
    "learn",
    "study",
    "understand",
    "course",
    "lesson",
    "assignment",
    "homework",
    "exam",
    "quiz",
    "topic",
    "meaning of",
    "what is",
    "how does",
    "how do i",
    "step by step",
    "example",
    "practice",
    "cybersecurity",
    "networking",
    "linux",
    "windows server",
    "active directory",
    "cloud security",
    "python for cybersecurity",
    "soc analyst",
}

RESEARCH_SIGNALS = {
    "research",
    "find out",
    "look into",
    "analyze",
    "analyse",
    "compare",
    "latest",
    "trend",
    "source",
    "sources",
    "evidence",
    "report",
    "summary of",
    "investigate",
}

PLANNING_SIGNALS = {
    "plan",
    "schedule",
    "routine",
    "roadmap",
    "timeline",
    "organize",
    "prepare",
    "strategy",
    "next step",
    "steps",
    "milestone",
    "workflow",
}

WRITING_SIGNALS = {
    "write",
    "rewrite",
    "draft",
    "polish",
    "compose",
    "email",
    "letter",
    "caption",
    "proposal",
    "speech",
    "announcement",
    "motivational",
    "motivation",
    "make it professional",
    "give me a message",
    "give me an email",
    "give me a caption",
    "give me a speech",
    "send to",
}

TECHNICAL_SIGNALS = {
    "code",
    "bug",
    "error",
    "traceback",
    "exception",
    "api",
    "backend",
    "frontend",
    "database",
    "sql",
    "python",
    "fastapi",
    "react",
    "typescript",
    "javascript",
    "server",
    "terminal",
    "powershell",
    "pytest",
    "build",
    "deploy",
    "git",
    "github",
    "uvicorn",
    "npm",
    "vite",
    ".env",
    "module not found",
    "runtimeerror",
}

DECISION_SIGNALS = {
    "should i",
    "which one",
    "choose",
    "decide",
    "decision",
    "better option",
    "worth it",
    "pros and cons",
    "what do you think",
    "is it advisable",
    "recommend",
}

CASUAL_EXACT_SIGNALS = {
    "hi",
    "hello",
    "hey",
    "yo",
    "good morning",
    "goo morning",
    "morning",
    "good afternoon",
    "afternoon",
    "good evening",
    "evening",
    "what's up",
    "whats up",
    "how are you",
    "how are you doing",
    "how you doing",
}

CASUAL_PREFIX_SIGNALS = {
    "hi ",
    "hello ",
    "hey ",
    "good morning",
    "goo morning",
    "good afternoon",
    "good evening",
    "how are you",
    "how are you doing",
}

EMOTIONAL_SUPPORT_SIGNALS = {
    "i feel overwhelmed",
    "i'm overwhelmed",
    "i am overwhelmed",
    "i feel stressed",
    "i'm stressed",
    "i am stressed",
    "i feel anxious",
    "i'm anxious",
    "i am anxious",
    "i feel sad",
    "i'm sad",
    "i am sad",
    "i feel betrayed",
    "i feel lost",
    "i feel lonely",
    "i feel tired",
    "i'm tired of",
    "i am tired of",
    "heartbroken",
    "depressed",
    "hopeless",
    "angry",
    "hurt",
    "afraid",
    "worried",
    "panic",
    "i don't know what to do",
    "i need advice",
    "i need someone to talk to",
    "i feel like giving up",
}


def _crisis_reply() -> str:
    return (
        "I'm really sorry you're carrying this right now. "
        "Your safety matters more than solving everything in this moment. "
        "Are you in immediate danger, or have you already done anything that could harm you?\n\n"
        "If there is any immediate danger, please contact your local emergency service now "
        "or ask someone nearby to stay with you. If there is a trusted person close to you, "
        'send them this simple message: "I\'m not safe alone right now. Please stay with me."\n\n'
        "Stay with me for a moment. What country are you in right now so I can guide you toward "
        "the right kind of urgent support?"
    )


def _high_distress_reply(detected_emotion: str | None = None) -> str:
    grounding_line = build_grounding_line(detected_emotion)

    return (
        "That sounds heavy, and I don't want to rush past it. "
        "Let's slow it down. You do not need to solve everything at once.\n\n"
        f"{grounding_line}\n\n"
        "For the next minute, focus only on this: breathe slowly, sit somewhere safe, "
        "and name the one thing that feels most urgent right now. "
        "What is the biggest pressure on you at this moment?"
    )


def _normalize_message(message: str) -> str:
    return " ".join(message.lower().strip().split())


def _contains_any(message: str, signals: set[str]) -> bool:
    normalized = _normalize_message(message)
    return any(signal in normalized for signal in signals)


def _is_short_casual_message(message: str) -> bool:
    normalized = _normalize_message(message)

    if len(normalized) > 100:
        return False

    if normalized in CASUAL_EXACT_SIGNALS:
        return True

    return any(normalized.startswith(signal) for signal in CASUAL_PREFIX_SIGNALS)


def _has_task_signal(message: str) -> bool:
    return any(
        (
            _contains_any(message, LEARNING_SIGNALS),
            _contains_any(message, RESEARCH_SIGNALS),
            _contains_any(message, PLANNING_SIGNALS),
            _contains_any(message, WRITING_SIGNALS),
            _contains_any(message, TECHNICAL_SIGNALS),
            _contains_any(message, DECISION_SIGNALS),
        )
    )


def _has_emotional_support_signal(
    message: str,
    safety_level: str,
    detected_emotion: str | None,
) -> bool:
    if _contains_any(message, EMOTIONAL_SUPPORT_SIGNALS):
        return True

    if safety_level == "S2" and not _has_task_signal(message):
        return True

    if detected_emotion in {
        "sad",
        "lonely",
        "anxious",
        "stressed",
        "overwhelmed",
        "angry",
    } and not _has_task_signal(message):
        return True

    return False


def _detect_response_posture(
    message: str,
    safety_level: str,
    detected_emotion: str | None,
) -> ResponsePosture:
    """
    Infer Akon's response posture from the user's actual message.

    This is internal only. The user should not have to choose a mode in the UI.
    Akon should adapt naturally from the conversation.
    """
    if _contains_any(message, TECHNICAL_SIGNALS):
        return "technical"

    if _contains_any(message, WRITING_SIGNALS):
        return "writing"

    if _contains_any(message, LEARNING_SIGNALS):
        return "learning"

    if _contains_any(message, RESEARCH_SIGNALS):
        return "research"

    if _has_emotional_support_signal(
        message=message,
        safety_level=safety_level,
        detected_emotion=detected_emotion,
    ):
        return "emotional_support"

    if _contains_any(message, PLANNING_SIGNALS):
        return "planning"

    if _contains_any(message, DECISION_SIGNALS):
        return "decision"

    if _is_short_casual_message(message):
        return "casual"

    return "general"


def _casual_fallback_reply(message: str) -> str:
    normalized = _normalize_message(message)

    if "morning" in normalized:
        return "Good morning. I'm doing well and ready to help. How is your morning going?"

    if "afternoon" in normalized:
        return "Good afternoon. I'm here and ready whenever you are. How is your day going?"

    if "evening" in normalized:
        return "Good evening. I'm doing well and ready to help. How has your day been?"

    if "how are you" in normalized or "how you doing" in normalized:
        return "I'm doing well and ready to help. What are you working on today?"

    return "Hey, I'm here. What would you like us to talk about today?"


def _writing_fallback_reply(message: str) -> str:
    normalized = _normalize_message(message)

    if "team" in normalized and (
        "motivational" in normalized
        or "motivation" in normalized
        or "encourage" in normalized
        or "message" in normalized
    ):
        return (
            "Good morning team,\n\n"
            "I want to encourage everyone to stay focused, disciplined, and committed. "
            "Every effort we put in matters, every customer we serve matters, and every "
            "sale brings us closer to our goal.\n\n"
            "Let's keep pushing with positive energy, teamwork, and consistency. I believe "
            "in this team, and I know we can achieve stronger results when we all give our best.\n\n"
            "Let's make this period productive and successful for all of us."
        )

    return (
        "Hello,\n\n"
        "I hope you are doing well. I wanted to share this message clearly and respectfully. "
        "Thank you for your effort, attention, and commitment. Let's keep moving forward "
        "with focus, discipline, and a positive mindset.\n\n"
        "Best regards."
    )


def _learning_fallback_reply() -> str:
    return (
        "Let's learn it step by step.\n\n"
        "Start by telling me the exact topic or question, and I'll explain it clearly with "
        "simple examples and practice points."
    )


def _research_fallback_reply() -> str:
    return (
        "Let's structure the research clearly.\n\n"
        "Share the topic, and I'll break it into the key questions, comparison points, "
        "evidence to look for, and a clean summary structure."
    )


def _planning_fallback_reply() -> str:
    return (
        "Let's turn this into a clear plan.\n\n"
        "We need the goal, the deadline, the constraints, and the first practical step."
    )


def _technical_fallback_reply() -> str:
    return (
        "Send the exact error, file, command output, or code section, and I'll guide you "
        "through the fix step by step."
    )


def _decision_fallback_reply() -> str:
    return (
        "Let's compare the options by cost, risk, benefit, timing, and what matters most "
        "to you."
    )


def _adaptive_fallback_reply(
    message: str,
    response_posture: ResponsePosture,
) -> str:
    if response_posture == "casual":
        return _casual_fallback_reply(message)

    if response_posture == "writing":
        return _writing_fallback_reply(message)

    if response_posture == "learning":
        return _learning_fallback_reply()

    if response_posture == "research":
        return _research_fallback_reply()

    if response_posture == "planning":
        return _planning_fallback_reply()

    if response_posture == "technical":
        return _technical_fallback_reply()

    if response_posture == "decision":
        return _decision_fallback_reply()

    return "Tell me what you want to do next, and I'll respond in the most useful way for the task."


def _fallback_reply(
    message: str,
    safety_level: str,
    detected_emotion: str | None,
    response_posture: ResponsePosture,
    memory_context: str | None = None,
) -> str:
    if response_posture == "emotional_support":
        return build_support_reply(
            user_message=message,
            detected_emotion=detected_emotion,
            safety_level=safety_level,
            memory_context=memory_context,
        )

    return _adaptive_fallback_reply(
        message=message,
        response_posture=response_posture,
    )


def _generate_with_provider(
    *,
    message: str,
    safety_level: str,
    detected_emotion: str | None,
    memory_context: str | None,
    response_posture: ResponsePosture,
) -> str:
    provider = get_llm_provider()

    try:
        return provider.generate_reply(
            message=message,
            safety_level=safety_level,
            detected_emotion=detected_emotion,
            memory_context=memory_context,
            response_posture=response_posture,
        )
    except TypeError as exc:
        if "response_posture" not in str(exc):
            raise

        return provider.generate_reply(
            message=message,
            safety_level=safety_level,
            detected_emotion=detected_emotion,
            memory_context=memory_context,
        )


def _should_use_local_fallback() -> bool:
    """
    Decide whether provider failures may fall back to Akon's local deterministic reply.

    Development can use fallback for resilience. For real AI verification use:
    ALLOW_AI_FALLBACK=false
    """
    return bool(settings.allow_ai_fallback)


def generate_akon_reply(
    message: str,
    safety_result: dict[str, Any],
    memory_context: str | None = None,
) -> str:
    """
    Generate Akon's reply.

    S4 and S3 safety flows remain deterministic and controlled.
    For ordinary messages, Akon automatically adapts from the user's actual
    request instead of assuming emotional distress.
    """
    safety_level = safety_result.get("level", "S0")
    detected_emotion = safety_result.get("detected_emotion")

    if safety_level == "S4":
        return _crisis_reply()

    if safety_level == "S3":
        return _high_distress_reply(detected_emotion=detected_emotion)

    response_posture = _detect_response_posture(
        message=message,
        safety_level=safety_level,
        detected_emotion=detected_emotion,
    )

    if settings.default_ai_provider == "mock":
        return _fallback_reply(
            message=message,
            safety_level=safety_level,
            detected_emotion=detected_emotion,
            response_posture=response_posture,
            memory_context=memory_context,
        )

    provider_detected_emotion = (
        detected_emotion if response_posture == "emotional_support" else None
    )

    try:
        return _generate_with_provider(
            message=message,
            safety_level=safety_level,
            detected_emotion=provider_detected_emotion,
            memory_context=memory_context,
            response_posture=response_posture,
        )
    except LLMProviderError:
        if not _should_use_local_fallback():
            raise

        return _fallback_reply(
            message=message,
            safety_level=safety_level,
            detected_emotion=detected_emotion,
            response_posture=response_posture,
            memory_context=memory_context,
        )