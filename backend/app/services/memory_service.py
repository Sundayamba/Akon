from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.memory import MemoryItem


STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "your", "you",
    "are", "was", "were", "have", "has", "had", "but", "not", "can",
    "will", "would", "should", "could", "about", "into", "next", "what",
    "when", "where", "why", "how", "help", "please", "need", "want",
    "like", "feel", "feeling", "today", "tomorrow", "remember", "recall",
    "memory", "memories", "saved", "know", "tell",
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
        "prefer", "preference", "style", "tone", "direct", "step",
        "guidance", "explain", "short", "detailed",
    },
    "goal": {
        "goal", "build", "become", "career", "learn", "master", "project",
        "company", "startup", "cybersecurity", "developer",
    },
    "constraint": {
        "constraint", "limited", "struggle", "problem", "budget", "money",
        "time", "schedule", "cannot", "can't",
    },
    "cultural_context": {
        "culture", "family", "tradition", "traditional", "community",
        "expectation",
    },
    "emotional_baseline": {
        "overwhelmed", "anxious", "stressed", "sad", "angry", "lonely",
        "confused",
    },
    "study_note": {
        "study", "studied", "learn", "lesson", "course", "topic", "exam",
        "quiz", "retain", "retention", "understand", "explain",
    },
    "fact": {
        "fact", "detail", "information", "important", "note", "remember",
    },
    "person": {
        "person", "name", "friend", "boss", "manager", "teacher", "client",
        "customer", "brother", "sister", "mother", "father",
    },
    "project": {
        "project", "app", "platform", "feature", "repo", "github", "roadmap",
        "milestone", "version", "product",
    },
    "decision": {
        "decision", "decided", "choose", "choice", "option", "agreed", "plan",
    },
    "language": {
        "language", "translate", "translation", "spanish", "mandarin",
        "french", "english", "twi", "yoruba", "igbo", "hausa",
    },
    "conversation_context": {
        "conversation", "context", "thread", "discussion", "talked", "said",
    },
}

CONFIDENCE_WEIGHT = {"high": 4, "medium": 2, "low": 1}
CONSENT_WEIGHT = {"explicit": 3, "implicit": 1}


@dataclass(frozen=True, slots=True)
class MemoryRecallMatch:
    memory: MemoryItem
    relevance_score: int
    reasons: tuple[str, ...]


def _normalize_token(token: str) -> str:
    return token.strip(".,!?;:()[]{}\"'`").lower()


def _normalize_message(message: str) -> str:
    return " ".join(message.lower().strip().split())


def _normalize_content(content: str) -> str:
    return " ".join(content.lower().strip().split())


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in (_normalize_token(word) for word in text.split())
        if len(token) >= 3 and token not in STOPWORDS
    }


def _recency_value(memory: MemoryItem) -> float:
    timestamp = memory.updated_at or memory.created_at
    return timestamp.timestamp() if timestamp is not None else 0.0


def is_recall_request(message: str) -> bool:
    normalized = _normalize_message(message)
    return any(signal in normalized for signal in RECALL_SIGNALS)


def _extract_recall_query(message: str) -> str:
    normalized = _normalize_message(message)

    for prefix in RECALL_PREFIXES:
        if normalized.startswith(prefix):
            return normalized.removeprefix(prefix).strip(" .,:;-")

    return message


def _memory_type_bonus(
    message_tokens: set[str],
    memory: MemoryItem,
) -> tuple[int, int]:
    overlap = len(
        message_tokens.intersection(
            MEMORY_TYPE_KEYWORDS.get(memory.memory_type, set())
        )
    )
    return (min(overlap * 2, 6), overlap) if overlap else (0, 0)


def _phrase_bonus(message: str, memory: MemoryItem) -> int:
    normalized_message = message.lower()

    if memory.memory_type.lower() in normalized_message:
        return 2

    for token in _tokenize(memory.content):
        if token in normalized_message:
            return 2

    return 0


def _recall_bonus(
    *,
    recall_request: bool,
    message_tokens: set[str],
    memory: MemoryItem,
) -> int:
    if not recall_request:
        return 0

    memory_tokens = _tokenize(f"{memory.memory_type} {memory.content}")

    if message_tokens and message_tokens.intersection(memory_tokens):
        return 8

    if message_tokens:
        return 1

    return 0 if memory.sensitivity == "high" else 4


def _score_memory(
    message: str,
    message_tokens: set[str],
    memory: MemoryItem,
    *,
    recall_request: bool,
) -> tuple[int, tuple[str, ...]]:
    memory_tokens = _tokenize(f"{memory.memory_type} {memory.content}")
    overlap_count = len(message_tokens.intersection(memory_tokens))
    overlap_score = overlap_count * 5
    type_score, type_overlap_count = _memory_type_bonus(
        message_tokens,
        memory,
    )
    phrase_score = _phrase_bonus(message, memory)
    recall_score = _recall_bonus(
        recall_request=recall_request,
        message_tokens=message_tokens,
        memory=memory,
    )
    confidence_score = CONFIDENCE_WEIGHT.get(memory.confidence, 1)
    consent_score = CONSENT_WEIGHT.get(memory.consent_state, 0)
    sensitivity_penalty = 3 if memory.sensitivity == "high" else 0

    score = (
        overlap_score
        + type_score
        + phrase_score
        + recall_score
        + confidence_score
        + consent_score
        - sensitivity_penalty
    )

    reasons: list[str] = []

    if overlap_count:
        noun = "term" if overlap_count == 1 else "terms"
        reasons.append(f"Matched {overlap_count} key {noun} from your request.")

    if type_overlap_count:
        reasons.append("The memory type aligns with the request topic.")

    if phrase_score:
        reasons.append("A direct phrase or category match increased relevance.")

    if recall_score >= 4:
        reasons.append("You explicitly asked Akon to recall saved memory.")
    elif recall_score:
        reasons.append("The request contains a recall signal.")

    if memory.consent_state == "explicit":
        reasons.append("You explicitly approved this memory.")
    elif memory.consent_state == "implicit":
        reasons.append("This memory is active with implicit consent.")

    if memory.confidence == "high":
        reasons.append("The memory is marked high confidence.")
    elif memory.confidence == "low":
        reasons.append("The memory is marked low confidence and may need review.")

    if memory.sensitivity == "high":
        reasons.append(
            "This high-sensitivity memory was included only because the query matched it."
        )

    if not reasons:
        reasons.append("This memory ranked above the relevance threshold.")

    return score, tuple(reasons)


def _memory_allowed_for_recall(
    *,
    memory: MemoryItem,
    message_tokens: set[str],
    recall_request: bool,
) -> bool:
    if not recall_request or memory.sensitivity != "high":
        return True

    memory_tokens = _tokenize(f"{memory.memory_type} {memory.content}")
    return bool(message_tokens.intersection(memory_tokens))


def retrieve_memory_matches(
    db: Session,
    *,
    user_id: str,
    message: str,
    limit: int = 5,
) -> list[MemoryRecallMatch]:
    memories = db.scalars(
        select(MemoryItem)
        .where(MemoryItem.user_id == user_id)
        .where(MemoryItem.consent_state != "revoked")
        .order_by(MemoryItem.updated_at.desc())
    ).all()

    if not memories:
        return []

    recall_request = is_recall_request(message)
    recall_query = _extract_recall_query(message) if recall_request else message
    message_tokens = _tokenize(recall_query)

    if not message_tokens and not recall_request:
        return []

    scored: list[tuple[int, float, MemoryItem, tuple[str, ...]]] = []

    for memory in memories:
        if not _memory_allowed_for_recall(
            memory=memory,
            message_tokens=message_tokens,
            recall_request=recall_request,
        ):
            continue

        score, reasons = _score_memory(
            recall_query,
            message_tokens,
            memory,
            recall_request=recall_request,
        )
        scored.append((score, _recency_value(memory), memory, reasons))

    minimum_score = 3 if recall_request else 5

    matches = [
        MemoryRecallMatch(
            memory=memory,
            relevance_score=score,
            reasons=reasons,
        )
        for score, _, memory, reasons in sorted(
            scored,
            key=lambda item: (item[0], item[1]),
            reverse=True,
        )
        if score >= minimum_score
    ]

    return matches[: max(1, min(limit, 10))]


def _format_memory_context(match: MemoryRecallMatch) -> str:
    memory = match.memory
    label = MEMORY_TYPE_LABELS.get(
        memory.memory_type,
        memory.memory_type.replace("_", " ").title(),
    )

    return (
        f"- [{label}] {memory.content} "
        f"(confidence={memory.confidence}, "
        f"sensitivity={memory.sensitivity}, "
        f"relevance={match.relevance_score})"
    )


def build_memory_context(
    *,
    message: str,
    matches: list[MemoryRecallMatch],
) -> str | None:
    if not matches:
        return None

    lines = [_format_memory_context(match) for match in matches]

    if is_recall_request(message):
        return (
            "The user is asking Akon to recall saved memory. "
            "Use only the saved memory below. If it is not enough, say so clearly.\n"
            + "\n".join(lines)
        )

    return "\n".join(lines)


def retrieve_memory_context(
    db: Session,
    *,
    user_id: str,
    message: str,
    limit: int = 5,
) -> str | None:
    return build_memory_context(
        message=message,
        matches=retrieve_memory_matches(
            db=db,
            user_id=user_id,
            message=message,
            limit=limit,
        ),
    )


def _duplicate_similarity(first: MemoryItem, second: MemoryItem) -> float:
    if first.memory_type != second.memory_type:
        return 0.0

    if _normalize_content(first.content) == _normalize_content(second.content):
        return 1.0

    first_tokens = _tokenize(first.content)
    second_tokens = _tokenize(second.content)

    if len(first_tokens) < 2 or len(second_tokens) < 2:
        return 0.0

    union = first_tokens.union(second_tokens)

    if not union:
        return 0.0

    return len(first_tokens.intersection(second_tokens)) / len(union)


def _duplicate_groups(memories: list[MemoryItem]) -> list[list[str]]:
    active = [
        memory
        for memory in memories
        if memory.consent_state != "revoked"
    ]
    parent = {memory.id: memory.id for memory in active}

    def find(memory_id: str) -> str:
        while parent[memory_id] != memory_id:
            parent[memory_id] = parent[parent[memory_id]]
            memory_id = parent[memory_id]
        return memory_id

    def union(first_id: str, second_id: str) -> None:
        first_root = find(first_id)
        second_root = find(second_id)
        if first_root != second_root:
            parent[second_root] = first_root

    for index, first in enumerate(active):
        for second in active[index + 1:]:
            if _duplicate_similarity(first, second) >= 0.72:
                union(first.id, second.id)

    groups: dict[str, list[str]] = {}

    for memory in active:
        groups.setdefault(find(memory.id), []).append(memory.id)

    return [ids for ids in groups.values() if len(ids) >= 2]


def build_memory_health(memories: list[MemoryItem]) -> dict[str, Any]:
    duplicate_groups = _duplicate_groups(memories)
    duplicate_ids = {
        memory_id
        for group in duplicate_groups
        for memory_id in group
    }
    active = [
        memory
        for memory in memories
        if memory.consent_state != "revoked"
    ]
    review_ids = sorted(
        {
            memory.id
            for memory in active
            if (
                memory.consent_state == "implicit"
                or memory.confidence == "low"
                or memory.sensitivity == "high"
                or memory.id in duplicate_ids
            )
        }
    )
    type_counts: dict[str, int] = {}

    for memory in active:
        type_counts[memory.memory_type] = type_counts.get(memory.memory_type, 0) + 1

    return {
        "total_count": len(memories),
        "active_count": len(active),
        "explicit_count": sum(
            memory.consent_state == "explicit"
            for memory in active
        ),
        "implicit_count": sum(
            memory.consent_state == "implicit"
            for memory in active
        ),
        "revoked_count": sum(
            memory.consent_state == "revoked"
            for memory in memories
        ),
        "high_sensitivity_count": sum(
            memory.sensitivity == "high"
            for memory in active
        ),
        "low_confidence_count": sum(
            memory.confidence == "low"
            for memory in active
        ),
        "review_recommended_count": len(review_ids),
        "duplicate_group_count": len(duplicate_groups),
        "memory_type_counts": dict(sorted(type_counts.items())),
        "review_recommended_memory_ids": review_ids,
        "duplicate_groups": duplicate_groups,
    }
