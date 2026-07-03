import re
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


PERSISTENCE_MARKERS = [
    "remember that",
    "remember this",
    "please remember",
    "save this",
    "note that",
    "keep in mind",
    "from now on",
    "going forward",
]

ONE_OFF_TASK_STARTERS = [
    "can you",
    "could you",
    "please help",
    "help me",
    "explain",
    "teach me",
    "what is",
    "what are",
    "how do",
    "how does",
    "write ",
    "rewrite ",
    "draft ",
    "compose ",
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


def _has_persistence_marker(normalized_message: str) -> bool:
    return any(marker in normalized_message for marker in PERSISTENCE_MARKERS)


def _looks_like_one_off_task(normalized_message: str) -> bool:
    return any(normalized_message.startswith(starter) for starter in ONE_OFF_TASK_STARTERS)


def _deduplicate_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    unique_candidates: list[dict[str, Any]] = []

    for candidate in candidates:
        key = (
            candidate["memory_type"],
            _normalize_text(candidate["content"]),
        )

        if key in seen:
            continue

        seen.add(key)
        unique_candidates.append(candidate)

    return unique_candidates


def _build_candidate(
    memory_type: str,
    content: str,
    source: str = "chat_candidate",
    confidence: str = "medium",
) -> dict[str, Any]:
    cleaned_content = _clean_candidate_content(content)
    is_sensitive = _contains_any(cleaned_content, SENSITIVE_KEYWORDS)

    return {
        "memory_type": memory_type,
        "content": cleaned_content,
        "source": source,
        "confidence": confidence,
        "sensitivity": "high" if is_sensitive else "low",
        "consent_required": True,
        "reason": (
            "Potentially sensitive memory detected. Explicit consent is required."
            if is_sensitive
            else "Possible useful long-term memory detected. User confirmation is required before saving."
        ),
    }


def _candidate_from_explicit_memory_request(message: str, normalized: str) -> dict[str, Any]:
    if "goal" in normalized or "i want to become" in normalized or "i want to build" in normalized:
        return _build_candidate("goal", message, confidence="high")

    if "i can only" in normalized or "i don't have" in normalized or "i dont have" in normalized:
        return _build_candidate("constraint", message, confidence="high")

    if "culture" in normalized or "tradition" in normalized or "family expects" in normalized:
        return _build_candidate("cultural_context", message, confidence="high")

    if "overwhelmed" in normalized or "anxious" in normalized or "stressed" in normalized:
        return _build_candidate("emotional_baseline", message, confidence="high")

    return _build_candidate("preference", message, confidence="high")


def _extract_after_marker(message: str, marker_pattern: str) -> str:
    match = re.search(marker_pattern, message, flags=re.IGNORECASE)

    if not match:
        return message

    extracted = message[match.end() :].strip(" .,:;-")

    return extracted or message


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
    - One-off task requests should not become memory unless the user clearly asks
      Akon to remember them.
    """
    safety_level = safety_result.get("level", "S0")

    if safety_level in {"S3", "S4", "S5"}:
        return []

    normalized = _normalize_text(message)
    candidates: list[dict[str, Any]] = []

    has_persistence_marker = _has_persistence_marker(normalized)

    if _looks_like_one_off_task(normalized) and not has_persistence_marker:
        return []

    if has_persistence_marker:
        candidates.append(_candidate_from_explicit_memory_request(message, normalized))

    preference_markers = [
        "i prefer",
        "i like",
        "i don't like",
        "i dont like",
        "i hate",
        "from now on",
        "going forward",
    ]

    goal_markers = [
        "my goal is",
        "i want to become",
        "i want to build",
        "i am building",
        "i'm building",
        "im building",
    ]

    learning_goal_markers = [
        "i want to learn",
        "i want to master",
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
        "i get stressed when",
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

    if any(marker in normalized for marker in learning_goal_markers):
        content = _extract_after_marker(
            message,
            r"\bi want to (learn|master)\b",
        )

        if len(_normalize_text(content).split()) >= 2:
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

    return _deduplicate_candidates(candidates)[:3]