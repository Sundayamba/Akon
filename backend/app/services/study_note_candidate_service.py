import re
from typing import Any

from app.services.study_retention_service import (
    extract_study_topic,
    is_study_retention_request,
)


STUDY_NOTE_SAVE_SIGNALS = {
    "save this lesson",
    "save the lesson",
    "save this as a study note",
    "save that as a study note",
    "save as a study note",
    "save the key point",
    "save key point",
    "turn this lesson into a study note",
    "turn the lesson into a study note",
    "turn this into a study note",
    "create a study note",
    "make a study note",
    "study-note memory",
    "study note memory",
    "remember this lesson",
    "remember what i learned",
    "remember what i learnt",
    "save what i learned",
    "save what i learnt",
}

UNUSABLE_LESSON_SIGNALS = {
    "send the topic or paste your note now",
    "i'm having trouble reaching my ai provider",
    "akon's ai provider is temporarily unavailable",
    "could not complete that reply",
}


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().strip().split())


def is_study_note_save_request(message: str) -> bool:
    normalized = _normalize_text(message)

    return any(signal in normalized for signal in STUDY_NOTE_SAVE_SIGNALS)


def _message_value(message: Any, field: str) -> str:
    if isinstance(message, dict):
        value = message.get(field)
    else:
        value = getattr(message, field, None)

    return value if isinstance(value, str) else ""


def _clean_markdown(content: str) -> str:
    cleaned_lines: list[str] = []

    for raw_line in content.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()

        if not line or line.startswith("```"):
            continue

        line = re.sub(r"^#{1,6}\s+", "", line)
        line = re.sub(r"^[-*+]\s+", "", line)
        line = re.sub(r"^\d+[.)]\s+", "", line)
        line = line.replace("**", "")
        line = line.replace("__", "")
        line = re.sub(r"`([^`]+)`", r"\1", line)

        if line:
            cleaned_lines.append(line)

    cleaned = " ".join(cleaned_lines)
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip(" .,:;-")


def _clip_to_sentence(content: str, limit: int = 700) -> str:
    if len(content) <= limit:
        return content

    excerpt = content[: limit + 1]

    sentence_end = max(
        excerpt.rfind(". "),
        excerpt.rfind("? "),
        excerpt.rfind("! "),
    )

    if sentence_end >= int(limit * 0.55):
        return excerpt[: sentence_end + 1].strip()

    return f"{excerpt[: limit - 1].rstrip()}…"


def _is_usable_lesson(content: str) -> bool:
    cleaned = _clean_markdown(content)

    if len(cleaned) < 80:
        return False

    normalized = _normalize_text(cleaned)

    if any(signal in normalized for signal in UNUSABLE_LESSON_SIGNALS):
        return False

    return True


def _find_latest_assistant_lesson(
    conversation_messages: list[Any],
) -> str | None:
    for message in reversed(conversation_messages):
        role = _message_value(message, "role")
        content = _message_value(message, "content")

        if role != "assistant":
            continue

        if _is_usable_lesson(content):
            return content

    return None


def _find_recent_study_topic(
    conversation_messages: list[Any],
) -> str | None:
    for message in reversed(conversation_messages):
        role = _message_value(message, "role")
        content = _message_value(message, "content")

        if role != "user" or not content:
            continue

        if is_study_note_save_request(content):
            continue

        if not is_study_retention_request(content):
            continue

        topic = extract_study_topic(content).strip(" .,:;-")
        topic = re.sub(
            (
                r"\b("
                r"so i will remember it|"
                r"so i can remember it|"
                r"so i do not forget it|"
                r"so i won'?t forget it|"
                r"in a detailed but memorable way|"
                r"in a memorable way"
                r")\b"
            ),
            "",
            topic,
            flags=re.IGNORECASE,
        ).strip(" .,:;-")

        if topic and topic != "the topic you want to study":
            return topic[:160]

    return None


def build_study_note_candidate(
    *,
    message: str,
    safety_result: dict[str, Any],
    conversation_messages: list[Any],
) -> dict[str, Any] | None:
    """
    Build a consent-required study-note candidate from a recent Akon lesson.

    This function never saves memory. It only prepares a candidate that must be
    approved through the normal memory confirmation flow.
    """
    safety_level = safety_result.get("level", "S0")

    if safety_level in {"S3", "S4", "S5"}:
        return None

    if not is_study_note_save_request(message):
        return None

    lesson = _find_latest_assistant_lesson(conversation_messages)

    if lesson is None:
        return None

    cleaned_lesson = _clean_markdown(lesson)

    if not cleaned_lesson:
        return None

    summary = _clip_to_sentence(cleaned_lesson)
    topic = _find_recent_study_topic(conversation_messages)

    if topic:
        topic_prefix = f"{topic.lower()}:"

        if summary.lower().startswith(topic_prefix):
            content = summary
        else:
            content = f"{topic}: {summary}"
    else:
        content = summary

    return {
        "memory_type": "study_note",
        "content": content,
        "source": "study_session_candidate",
        "confidence": "high",
        "sensitivity": "low",
        "consent_required": True,
        "reason": (
            "Study-note candidate generated from the recent lesson. "
            "Review and approve it before saving."
        ),
    }