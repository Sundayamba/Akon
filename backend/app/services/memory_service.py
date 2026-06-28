from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.memory import MemoryItem


def _tokenize(text: str) -> set[str]:
    return {
        word.strip(".,!?;:()[]{}\"'").lower()
        for word in text.split()
        if len(word.strip(".,!?;:()[]{}\"'")) >= 3
    }


def _score_memory(message_tokens: set[str], memory: MemoryItem) -> int:
    memory_tokens = _tokenize(f"{memory.memory_type} {memory.content}")
    return len(message_tokens.intersection(memory_tokens))


def retrieve_memory_context(
    db: Session,
    message: str,
    limit: int = 5,
) -> str | None:
    """
    Retrieve simple relevant memory context for Akon.

    This is a temporary keyword-based MVP retrieval system.
    Later we will replace this with embeddings/vector search.
    """
    memories = db.scalars(
        select(MemoryItem)
        .where(MemoryItem.consent_state != "revoked")
        .order_by(MemoryItem.updated_at.desc())
    ).all()

    if not memories:
        return None

    message_tokens = _tokenize(message)

    scored_memories = [
        (_score_memory(message_tokens, memory), memory)
        for memory in memories
    ]

    relevant_memories = [
        memory
        for score, memory in sorted(
            scored_memories,
            key=lambda item: item[0],
            reverse=True,
        )
        if score > 0
    ]

    if not relevant_memories:
        relevant_memories = list(memories[:limit])

    selected_memories = relevant_memories[:limit]

    memory_lines = [
        f"- {memory.memory_type}: {memory.content} "
        f"(confidence={memory.confidence}, sensitivity={memory.sensitivity})"
        for memory in selected_memories
    ]

    return "\n".join(memory_lines)