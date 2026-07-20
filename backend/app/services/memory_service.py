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
    "remember",
    "recall",
    "memory",
    "memories",
    "saved",
    "know",
    "tell",
}

RECALL_SIGNALS = {
    "remember",
    "recall",
    "remind me",
    "what do you remember",
    "what did i tell you",
    "what have i told you",
    "saved memory",
    "my memory",
    "your memory",
    "do you know my",
    "tell me what you know",
    "what do you know about me",
    "what do you remember about me",
}

RECALL_PREFIXES = [
    "what do you remember about",
    "what do you know about",
    "what did i tell you about",
    "what have i told you about",
    "tell me what you remember about",
    "tell me what you know about",
    "recall",
    "remember",
    "remind me about",
]

MEMORY_TYPE_LABELS = {
    "preference": "Preference",
    "goal": "Goal",
    "constraint": "Constraint",
    "emotional_baseline": "Emotional baseline",
    "cultural_context": "Cultural context",
    "study_note": "Study note",
    "fact": "Fact",
    "person": "Person",
    "project": "Project",
    "decision": "Decision",
    "language": "Language",
    "conversation_context": "Conversation context",
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
    "study_note": {
        "study",
        "studied",
        "learn",
        "lesson",
        "course",
        "topic",
        "exam",
        "quiz",
        "retain",
        "retention",
        "understand",
        "explain",
    },
    "fact": {
        "fact",
        "detail",
        "information",
        "important",
        "note",
        "remember",
    },
    "person": {
        "person",
        "name",
        "friend",
        "boss",
        "manager",
        "teacher",
        "client",
        "customer",
        "brother",
        "sister",
        "mother",
        "father",
    },
    "project": {
        "project",
        "app",
        "platform",
        "feature",
        "repo",
        "github",
        "roadmap",
        "milestone",
        "version",
        "product",
    },
    "decision": {
        "decision",
        "decided",
        "choose",
        "choice",
        "option",
        "agreed",
        "plan",
    },
    "language": {
        "language",
        "translate",
        "translation",
        "spanish",
        "mandarin",
        "french",
        "english",
        "twi",
        "yoruba",
        "igbo",
        "hausa",
    },
    "conversation_context": {
        "conversation",
        "context",
        "thread",
        "discussion",
        "talked",
        "said",
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


def _normalize_message(message: str) -> str:
    return " ".join(message.lower().strip().split())


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


def _is_recall_request(message: str) -> bool:
    normalized = _normalize_message(message)
    return any(signal in normalized for signal in RECALL_SIGNALS)


def _extract_recall_query(message: str) -> str:
    normalized = _normalize_message(message)

    for prefix in RECALL_PREFIXES:
        if normalized.startswith(prefix):
            return normalized.removeprefix(prefix).strip(" .,:;-")

    return message


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


def _recall_bonus(
    *,
    is_recall_request: bool,
    message_tokens: set[str],
    memory: MemoryItem,
) -> int:
    if not is_recall_request:
        return 0

    memory_tokens = _tokenize(f"{memory.memory_type} {memory.content}")

    if message_tokens and message_tokens.intersection(memory_tokens):
        return 8

    if message_tokens:
        return 1

    if memory.sensitivity == "high":
        return 0

    return 4


def _score_memory(
    message: str,
    message_tokens: set[str],
    memory: MemoryItem,
    *,
    is_recall_request: bool,
) -> int:
    memory_tokens = _tokenize(f"{memory.memory_type} {memory.content}")
    overlap_score = len(message_tokens.intersection(memory_tokens)) * 5

    confidence_score = CONFIDENCE_WEIGHT.get(memory.confidence, 1)
    consent_score = CONSENT_WEIGHT.get(memory.consent_state, 0)
    type_score = _memory_type_bonus(message_tokens, memory)
    phrase_score = _phrase_bonus(message, memory)
    recall_score = _recall_bonus(
        is_recall_request=is_recall_request,
        message_tokens=message_tokens,
        memory=memory,
    )

    sensitivity_penalty = 3 if memory.sensitivity == "high" else 0

    return (
        overlap_score
        + confidence_score
        + consent_score
        + type_score
        + phrase_score
        + recall_score
        - sensitivity_penalty
    )


def _memory_allowed_for_recall(
    *,
    memory: MemoryItem,
    message_tokens: set[str],
    is_recall_request: bool,
) -> bool:
    if not is_recall_request:
        return True

    if memory.sensitivity != "high":
        return True

    memory_tokens = _tokenize(f"{memory.memory_type} {memory.content}")

    return bool(message_tokens.intersection(memory_tokens))


def _format_memory_context(memory: MemoryItem, score: int) -> str:
    label = MEMORY_TYPE_LABELS.get(memory.memory_type, memory.memory_type.replace("_", " ").title())

    return (
        f"- [{label}] {memory.content} "
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

    v0.5.3 adds recall-aware retrieval:
    - Retrieval is scoped to the authenticated user.
    - Revoked memories are excluded.
    - Ordinary messages still require meaningful relevance.
    - Recall requests can retrieve broader saved memory when the user explicitly asks.
    - High-sensitivity memory is not broadly returned unless the query overlaps it.
    """
    memories = db.scalars(
        select(MemoryItem)
        .where(MemoryItem.user_id == user_id)
        .where(MemoryItem.consent_state != "revoked")
        .order_by(MemoryItem.updated_at.desc())
    ).all()

    if not memories:
        return None

    is_recall_request = _is_recall_request(message)
    recall_query = _extract_recall_query(message) if is_recall_request else message
    message_tokens = _tokenize(recall_query)

    if not message_tokens and not is_recall_request:
        return None

    scored_memories = [
        (
            _score_memory(
                recall_query,
                message_tokens,
                memory,
                is_recall_request=is_recall_request,
            ),
            _recency_value(memory),
            memory,
        )
        for memory in memories
        if _memory_allowed_for_recall(
            memory=memory,
            message_tokens=message_tokens,
            is_recall_request=is_recall_request,
        )
    ]

    minimum_score = 3 if is_recall_request else 5

    relevant_memories = [
        (score, memory)
        for score, _, memory in sorted(
            scored_memories,
            key=lambda item: (item[0], item[1]),
            reverse=True,
        )
        if score >= minimum_score
    ]

    if not relevant_memories:
        return None

    selected_memories = relevant_memories[:limit]

    memory_lines = [
        _format_memory_context(memory, score)
        for score, memory in selected_memories
    ]

    if is_recall_request:
        return (
            "The user is asking Akon to recall saved memory. "
            "Use only the saved memory below. If it is not enough, say so clearly.\n"
            + "\n".join(memory_lines)
        )

    return "\n".join(memory_lines)