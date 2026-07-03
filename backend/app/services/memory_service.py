from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.memory import MemoryItem


STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "your",
    "you",
    "are",
    "was",
    "were",
    "have",
    "has",
    "had",
    "but",
    "not",
    "can",
    "will",
    "would",
    "should",
    "could",
    "about",
    "into",
    "next",
    "what",
    "when",
    "where",
    "why",
    "how",
    "help",
    "please",
    "need",
    "want",
    "like",
    "feel",
    "feeling",
    "today",
    "tomorrow",
}


MEMORY_TYPE_KEYWORDS: dict[str, set[str]] = {
    "preference": {
        "prefer",
        "preference",
        "style",
        "tone",
        "direct",
        "step",
        "guidance",
        "explain",
        "short",
        "detailed",
    },
    "goal": {
        "goal",
        "build",
        "become",
        "career",
        "learn",
        "master",
        "project",
        "company",
        "startup",
        "cybersecurity",
        "developer",
    },
    "constraint": {
        "constraint",
        "limited",
        "struggle",
        "problem",
        "budget",
        "money",
        "time",
        "schedule",
        "cannot",
        "can't",
    },
    "cultural_context": {
        "culture",
        "family",
        "tradition",
        "traditional",
        "community",
        "expectation",
    },
    "emotional_baseline": {
        "overwhelmed",
        "anxious",
        "stressed",
        "sad",
        "angry",
        "lonely",
        "confused",
    },
}


CONFIDENCE_WEIGHT = {
    "high": 4,
    "medium": 2,
    "low": 1,
}


CONSENT_WEIGHT = {
    "explicit": 3,
    "implicit": 1,
}


def _normalize_token(token: str) -> str:
    return token.strip(".,!?;:()[]{}\"'`").lower()


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in (_normalize_token(word) for word in text.split())
        if len(token) >= 3 and token not in STOPWORDS
    }


def _recency_value(memory: MemoryItem) -> float:
    timestamp = memory.updated_at or memory.created_at

    if timestamp is None:
        return 0.0

    return timestamp.timestamp()


def _memory_type_bonus(message_tokens: set[str], memory: MemoryItem) -> int:
    type_keywords = MEMORY_TYPE_KEYWORDS.get(memory.memory_type, set())

    if not type_keywords:
        return 0

    overlap = len(message_tokens.intersection(type_keywords))

    if overlap == 0:
        return 0

    return min(overlap * 2, 6)


def _phrase_bonus(message: str, memory: MemoryItem) -> int:
    normalized_message = message.lower()
    normalized_content = memory.content.lower()

    if memory.memory_type.lower() in normalized_message:
        return 2

    memory_tokens = _tokenize(memory.content)

    for token in memory_tokens:
        if token in normalized_message and token in normalized_content:
            return 2

    return 0


def _score_memory(message: str, message_tokens: set[str], memory: MemoryItem) -> int:
    memory_tokens = _tokenize(f"{memory.memory_type} {memory.content}")
    overlap_score = len(message_tokens.intersection(memory_tokens)) * 5

    confidence_score = CONFIDENCE_WEIGHT.get(memory.confidence, 1)
    consent_score = CONSENT_WEIGHT.get(memory.consent_state, 0)
    type_score = _memory_type_bonus(message_tokens, memory)
    phrase_score = _phrase_bonus(message, memory)

    sensitivity_penalty = 1 if memory.sensitivity == "high" else 0

    return (
        overlap_score
        + confidence_score
        + consent_score
        + type_score
        + phrase_score
        - sensitivity_penalty
    )


def _format_memory_context(memory: MemoryItem, score: int) -> str:
    return (
        f"- {memory.memory_type}: {memory.content} "
        f"(confidence={memory.confidence}, sensitivity={memory.sensitivity}, relevance={score})"
    )


def retrieve_memory_context(
    db: Session,
    *,
    user_id: str,
    message: str,
    limit: int = 5,
) -> str | None:
    """
    Retrieve relevant memory context for Akon.

    This is still an MVP retrieval system, but it is now stricter than simple
    recency fallback:
    - Retrieval is scoped to the authenticated user.
    - Revoked memories are excluded.
    - Memories are ranked by keyword overlap, memory type relevance, confidence,
      consent state, and recency.
    - If nothing is meaningfully relevant, no memory context is returned.
    """
    memories = db.scalars(
        select(MemoryItem)
        .where(MemoryItem.user_id == user_id)
        .where(MemoryItem.consent_state != "revoked")
        .order_by(MemoryItem.updated_at.desc())
    ).all()

    if not memories:
        return None

    message_tokens = _tokenize(message)

    if not message_tokens:
        return None

    scored_memories = [
        (_score_memory(message, message_tokens, memory), _recency_value(memory), memory)
        for memory in memories
    ]

    relevant_memories = [
        (score, memory)
        for score, _, memory in sorted(
            scored_memories,
            key=lambda item: (item[0], item[1]),
            reverse=True,
        )
        if score >= 5
    ]

    if not relevant_memories:
        return None

    selected_memories = relevant_memories[:limit]

    memory_lines = [
        _format_memory_context(memory, score)
        for score, memory in selected_memories
    ]

    return "\n".join(memory_lines)