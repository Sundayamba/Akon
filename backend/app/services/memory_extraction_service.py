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
    "help me remember",
    "save this",
    "save that",
    "store this",
    "store that",
    "add this to memory",
    "add that to memory",
    "note that",
    "keep in mind",
    "don't forget",
    "do not forget",
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

MEMORY_TYPE_SIGNALS: list[tuple[str, list[str]]] = [
    (
        "preference",
        [
            "i prefer",
            "i like",
            "i don't like",
            "i dont like",
            "i hate",
            "from now on",
            "going forward",
        ],
    ),
    (
        "goal",
        [
            "my goal is",
            "i want to become",
            "i want to build",
            "i want to start",
            "i want to learn",
            "i want to master",
            "i plan to",
        ],
    ),
    (
        "constraint",
        [
            "i can only",
            "i don't have",
            "i dont have",
            "i have limited",
            "i struggle with",
            "my problem is",
            "my limitation is",
        ],
    ),
    (
        "project",
        [
            "project",
            "app",
            "platform",
            "repo",
            "github",
            "roadmap",
            "milestone",
            "version",
            "feature",
            "product",
            "i am building",
            "i'm building",
            "im building",
        ],
    ),
    (
        "person",
        [
            "his name is",
            "her name is",
            "their name is",
            "my boss",
            "my friend",
            "my manager",
            "my teacher",
            "my client",
            "my customer",
            "my brother",
            "my sister",
        ],
    ),
    (
        "decision",
        [
            "i decided",
            "we decided",
            "i chose",
            "we chose",
            "i agreed",
            "we agreed",
            "the decision is",
            "final decision",
        ],
    ),
    (
        "language",
        [
            "translate",
            "translation",
            "language",
            "spanish",
            "mandarin",
            "french",
            "english",
            "twi",
            "yoruba",
            "igbo",
            "hausa",
        ],
    ),
    (
        "study_note",
        [
            "i studied",
            "i am studying",
            "i'm studying",
            "exam",
            "quiz",
            "lesson",
            "course",
            "topic",
            "revision",
            "retention",
            "remember what i studied",
        ],
    ),
    (
        "cultural_context",
        [
            "in my culture",
            "traditionally",
            "my family expects",
            "where i come from",
            "in my tradition",
        ],
    ),
    (
        "emotional_baseline",
        [
            "i usually feel",
            "i often feel",
            "i always feel",
            "i get overwhelmed when",
            "i get anxious when",
            "i get stressed when",
        ],
    ),
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


def _infer_memory_type(normalized: str) -> str:
    for memory_type, signals in MEMORY_TYPE_SIGNALS:
        if any(signal in normalized for signal in signals):
            return memory_type

    return "fact"


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


def _extract_after_marker(message: str, marker_pattern: str) -> str:
    match = re.search(marker_pattern, message, flags=re.IGNORECASE)

    if not match:
        return message

    extracted = message[match.end() :].strip(" .,:;-")

    return extracted or message


def _candidate_from_explicit_memory_request(message: str) -> dict[str, Any]:
    content = _extract_after_marker(
        message,
        r"\b(remember that|remember this|please remember|help me remember|save this|save that|store this|store that|add this to memory|add that to memory|note that|keep in mind|don't forget|do not forget)\b",
    )
    normalized_content = _normalize_text(content)
    memory_type = _infer_memory_type(normalized_content)

    return _build_candidate(
        memory_type=memory_type,
        content=content,
        source="explicit_memory_request",
        confidence="high",
    )


def _candidate_from_primary_signal(message: str, normalized: str) -> dict[str, Any] | None:
    memory_type = _infer_memory_type(normalized)

    if memory_type == "fact":
        return None

    return _build_candidate(
        memory_type=memory_type,
        content=message,
    )


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
    - v0.5.3 recognizes study notes, facts, people, projects, decisions, and language context.
    - One user message should create one primary memory candidate to avoid noisy duplicates.
    """
    safety_level = safety_result.get("level", "S0")

    if safety_level in {"S3", "S4", "S5"}:
        return []

    normalized = _normalize_text(message)
    has_persistence_marker = _has_persistence_marker(normalized)

    if _looks_like_one_off_task(normalized) and not has_persistence_marker:
        return []

    if has_persistence_marker:
        return [_candidate_from_explicit_memory_request(message)]

    candidate = _candidate_from_primary_signal(
        message=message,
        normalized=normalized,
    )

    if candidate is None:
        return []

    return [candidate]