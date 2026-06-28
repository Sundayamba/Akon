from typing import Any


SENSITIVE_KEYWORDS = [
    "depression",
    "anxiety disorder",
    "suicide",
    "self-harm",
    "self harm",
    "diagnosed",
    "medication",
    "hospital",
    "pregnant",
    "religion",
    "christian",
    "muslim",
    "politics",
    "political",
    "address",
    "where i live",
    "bank",
    "debt",
    "loan",
    "password",
    "pin",
]


def _normalize_text(text: str) -> str:
    cleaned = text.lower()

    for character in [",", ".", "!", "?", ";", ":", "(", ")", "[", "]", "{", "}", '"', "'"]:
        cleaned = cleaned.replace(character, " ")

    return " ".join(cleaned.split())


def _contains_any(text: str, keywords: list[str]) -> bool:
    normalized = _normalize_text(text)

    return any(_normalize_text(keyword) in normalized for keyword in keywords)


def _clean_candidate_content(content: str) -> str:
    return " ".join(content.strip().split())


def _build_candidate(
    memory_type: str,
    content: str,
    source: str = "chat_candidate",
) -> dict[str, Any]:
    cleaned_content = _clean_candidate_content(content)
    is_sensitive = _contains_any(cleaned_content, SENSITIVE_KEYWORDS)

    return {
        "memory_type": memory_type,
        "content": cleaned_content,
        "source": source,
        "confidence": "medium",
        "sensitivity": "high" if is_sensitive else "low",
        "consent_required": True,
        "reason": (
            "Potentially sensitive memory detected. Explicit consent is required."
            if is_sensitive
            else "Possible useful long-term memory detected. User confirmation is required before saving."
        ),
    }


def extract_memory_candidates(
    message: str,
    safety_result: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Extract possible memory candidates from a user message.

    Important:
    - This function does NOT save memory.
    - It only proposes candidate memories.
    - User confirmation must happen before persistence.
    - S3/S4/S5 safety messages are excluded from normal memory extraction.
    """
    safety_level = safety_result.get("level", "S0")

    if safety_level in {"S3", "S4", "S5"}:
        return []

    normalized = _normalize_text(message)
    candidates: list[dict[str, Any]] = []

    preference_markers = [
        "i prefer",
        "i like",
        "i don't like",
        "i dont like",
        "i hate",
        "i want you to",
        "from now on",
    ]

    goal_markers = [
        "my goal is",
        "i want to become",
        "i want to build",
        "i am building",
        "i'm building",
        "im building",
        "i want to learn",
    ]

    constraint_markers = [
        "i can only",
        "i don't have",
        "i dont have",
        "i have limited",
        "i struggle with",
        "my problem is",
    ]

    cultural_markers = [
        "in my culture",
        "traditionally",
        "my family expects",
        "where i come from",
        "in my tradition",
    ]

    emotional_baseline_markers = [
        "i usually feel",
        "i often feel",
        "i always feel",
        "i get overwhelmed when",
        "i get anxious when",
    ]

    if any(marker in normalized for marker in preference_markers):
        candidates.append(
            _build_candidate(
                memory_type="preference",
                content=message,
            )
        )

    if any(marker in normalized for marker in goal_markers):
        candidates.append(
            _build_candidate(
                memory_type="goal",
                content=message,
            )
        )

    if any(marker in normalized for marker in constraint_markers):
        candidates.append(
            _build_candidate(
                memory_type="constraint",
                content=message,
            )
        )

    if any(marker in normalized for marker in cultural_markers):
        candidates.append(
            _build_candidate(
                memory_type="cultural_context",
                content=message,
            )
        )

    if any(marker in normalized for marker in emotional_baseline_markers):
        candidates.append(
            _build_candidate(
                memory_type="emotional_baseline",
                content=message,
            )
        )

    return candidates[:3]