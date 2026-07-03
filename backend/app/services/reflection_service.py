from collections import Counter
from collections.abc import Mapping


MessageForReflection = Mapping[str, str | None]


EMOTION_REFLECTIONS: dict[str, dict[str, str]] = {
    "overwhelmed": {
        "title": "A moment with a lot to carry",
        "summary": "This conversation seems to circle around feeling stretched, pressured, or pulled in many directions at once.",
        "next_step": "Choose one small thing that would reduce the pressure slightly, then let that be enough for the next step.",
    },
    "stressed": {
        "title": "A pressure-filled moment",
        "summary": "This conversation seems to hold some stress, with your mind trying to organize what needs attention.",
        "next_step": "Name the one task or decision that would make today feel a little lighter.",
    },
    "anxious": {
        "title": "A worry asking for steadiness",
        "summary": "This conversation seems to carry worry or uncertainty, with attention moving toward what could go wrong.",
        "next_step": "Separate what you know from what you do not know yet, then choose one safe action you can take.",
    },
    "angry": {
        "title": "A boundary may be speaking",
        "summary": "This conversation seems to include frustration, heat, or a sense that something may feel unfair.",
        "next_step": "Name the boundary, need, or expectation that matters most before deciding what to do next.",
    },
    "sad": {
        "title": "A tender place surfaced",
        "summary": "This conversation seems to touch something painful or disappointing that deserves gentleness rather than pressure.",
        "next_step": "Give yourself permission to name the hardest part clearly, without forcing yourself to solve it immediately.",
    },
    "lonely": {
        "title": "A need for connection",
        "summary": "This conversation seems to carry a wish to feel seen, supported, or less alone with what is happening.",
        "next_step": "Think of one safe person, place, or routine that could offer a small amount of connection today.",
    },
    "confused": {
        "title": "A moment needing clarity",
        "summary": "This conversation seems to hold uncertainty, where the next step may not feel obvious yet.",
        "next_step": "List the options in front of you and pick the one that is most realistic for today.",
    },
    "hopeful": {
        "title": "A quiet sign of possibility",
        "summary": "This conversation seems to include some hope or readiness, even if the path is not fully clear yet.",
        "next_step": "Protect that hope with one small action that moves you forward without overwhelming you.",
    },
    "calm": {
        "title": "A steadier place to choose from",
        "summary": "This conversation seems to have a calmer tone, which can make the next decision feel more grounded.",
        "next_step": "Notice what is helping you feel steady, then keep one part of that with you today.",
    },
    "neutral": {
        "title": "A conversation worth continuing",
        "summary": "This conversation is mainly about sorting out a topic, task, or idea.",
        "next_step": "Continue from the most useful point in the conversation.",
    },
}


TASK_REFLECTIONS: dict[str, dict[str, str]] = {
    "technical": {
        "title": "A technical troubleshooting thread",
        "summary": "This conversation is mainly about diagnosing, fixing, or improving a technical issue.",
        "next_step": "Continue from the last command, error, file, or test result so the next step stays grounded.",
    },
    "learning": {
        "title": "A learning thread",
        "summary": "This conversation is mainly about understanding a topic step by step.",
        "next_step": "Continue with the next concept, example, or practice checkpoint.",
    },
    "writing": {
        "title": "A writing thread",
        "summary": "This conversation is mainly about creating or improving wording.",
        "next_step": "Continue by refining tone, clarity, audience, or final formatting.",
    },
    "planning": {
        "title": "A planning thread",
        "summary": "This conversation is mainly about turning an idea or goal into practical steps.",
        "next_step": "Continue with priorities, constraints, timeline, and the next action.",
    },
    "decision": {
        "title": "A decision thread",
        "summary": "This conversation is mainly about comparing options and choosing a direction.",
        "next_step": "Continue by clarifying tradeoffs, risks, and the strongest recommendation.",
    },
    "general": {
        "title": "A conversation worth continuing",
        "summary": "This conversation is mainly about sorting out a topic, task, or idea.",
        "next_step": "Continue from the point that feels most useful now.",
    },
}


TECHNICAL_SIGNALS = {
    "code",
    "error",
    "traceback",
    "python",
    "react",
    "typescript",
    "fastapi",
    "api",
    "backend",
    "frontend",
    "pytest",
    "build",
    "git",
}

LEARNING_SIGNALS = {
    "explain",
    "teach",
    "learn",
    "study",
    "what is",
    "how does",
    "cybersecurity",
    "networking",
}

WRITING_SIGNALS = {
    "write",
    "rewrite",
    "draft",
    "message",
    "email",
    "announcement",
    "caption",
    "speech",
}

PLANNING_SIGNALS = {
    "plan",
    "roadmap",
    "schedule",
    "steps",
    "strategy",
    "next step",
}

DECISION_SIGNALS = {
    "should i",
    "which one",
    "choose",
    "decide",
    "worth it",
    "pros and cons",
}


def _normalize_emotion(emotion: str | None) -> str:
    if not emotion:
        return "neutral"

    normalized = emotion.strip().lower()
    return normalized if normalized in EMOTION_REFLECTIONS else "neutral"


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""

    return " ".join(text.lower().split())


def _contains_any(text: str, signals: set[str]) -> bool:
    return any(signal in text for signal in signals)


def _dominant_emotion(messages: list[MessageForReflection]) -> str:
    emotions = [
        _normalize_emotion(message.get("detected_emotion"))
        for message in messages
        if message.get("detected_emotion")
    ]

    if not emotions:
        return "neutral"

    return Counter(emotions).most_common(1)[0][0]


def _user_message_count(messages: list[MessageForReflection]) -> int:
    return sum(1 for message in messages if message.get("role") == "user")


def _conversation_task_theme(messages: list[MessageForReflection]) -> str:
    user_text = " ".join(
        _normalize_text(message.get("content"))
        for message in messages
        if message.get("role") == "user"
    )

    if _contains_any(user_text, TECHNICAL_SIGNALS):
        return "technical"

    if _contains_any(user_text, WRITING_SIGNALS):
        return "writing"

    if _contains_any(user_text, LEARNING_SIGNALS):
        return "learning"

    if _contains_any(user_text, PLANNING_SIGNALS):
        return "planning"

    if _contains_any(user_text, DECISION_SIGNALS):
        return "decision"

    return "general"


def build_conversation_reflection(
    *,
    conversation_id: str,
    messages: list[MessageForReflection],
):
    """
    Build a non-clinical reflection summary for a conversation.

    Emotional reflections are used only when the dominant emotion is meaningful.
    Neutral conversations are summarized by task theme instead of being forced into
    emotional language.
    """
    from app.schemas.chat import ConversationReflectionResponse

    if not messages:
        raise ValueError("Cannot reflect on an empty conversation.")

    dominant_emotion = _dominant_emotion(messages)
    user_count = _user_message_count(messages)
    message_count = len(messages)

    if dominant_emotion != "neutral":
        reflection = EMOTION_REFLECTIONS[dominant_emotion]
    else:
        task_theme = _conversation_task_theme(messages)
        reflection = TASK_REFLECTIONS[task_theme]

    summary = reflection["summary"]

    if user_count <= 1:
        summary = (
            f"{summary} This is still early, so Akon is treating it as a small "
            "snapshot rather than a full picture."
        )

    return ConversationReflectionResponse(
        conversation_id=conversation_id,
        title=reflection["title"],
        summary=summary,
        dominant_emotion=dominant_emotion,
        supportive_next_step=reflection["next_step"],
        message_count=message_count,
    )