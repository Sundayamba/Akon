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
        "title": "A conversation worth noticing",
        "summary": "This conversation seems to be about sorting things out one piece at a time.",
        "next_step": "Choose the one part of this conversation that feels most useful to continue from.",
    },
}


def _normalize_emotion(emotion: str | None) -> str:
    if not emotion:
        return "neutral"

    normalized = emotion.strip().lower()
    return normalized if normalized in EMOTION_REFLECTIONS else "neutral"


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


def build_conversation_reflection(
    *,
    conversation_id: str,
    messages: list[MessageForReflection],
):
    """
    Build a warm, non-clinical reflection summary for a conversation.

    This does not diagnose the user. It only summarizes the visible conversation
    pattern in supportive language.
    """
    from app.schemas.chat import ConversationReflectionResponse

    if not messages:
        raise ValueError("Cannot reflect on an empty conversation.")

    dominant_emotion = _dominant_emotion(messages)
    reflection = EMOTION_REFLECTIONS[dominant_emotion]
    user_count = _user_message_count(messages)
    message_count = len(messages)

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