from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message
from app.schemas.chat import ConversationSummary


def _normalize_preview(content: str, limit: int = 160) -> str:
    cleaned = " ".join(content.strip().split())

    if len(cleaned) <= limit:
        return cleaned

    return f"{cleaned[: limit - 3].rstrip()}..."


def build_conversation_summaries(
    *,
    db: Session,
    conversations: Sequence[Conversation],
    user_id: str,
) -> list[ConversationSummary]:
    # Build lightweight persisted History records.
    if not conversations:
        return []

    conversation_ids = [
        conversation.id
        for conversation in conversations
    ]

    count_rows = db.execute(
        select(
            Message.conversation_id.label("conversation_id"),
            func.count(Message.id).label("message_count"),
        )
        .where(Message.user_id == user_id)
        .where(Message.conversation_id.in_(conversation_ids))
        .group_by(Message.conversation_id)
    ).all()

    message_count_by_conversation = {
        row.conversation_id: int(row.message_count)
        for row in count_rows
    }

    ranked_messages = (
        select(
            Message.conversation_id.label("conversation_id"),
            Message.content.label("content"),
            Message.role.label("role"),
            Message.created_at.label("created_at"),
            func.row_number()
            .over(
                partition_by=Message.conversation_id,
                order_by=[
                    Message.created_at.desc(),
                    Message.id.desc(),
                ],
            )
            .label("message_rank"),
        )
        .where(Message.user_id == user_id)
        .where(Message.conversation_id.in_(conversation_ids))
        .subquery()
    )

    latest_rows = db.execute(
        select(
            ranked_messages.c.conversation_id,
            ranked_messages.c.content,
            ranked_messages.c.role,
            ranked_messages.c.created_at,
        )
        .where(ranked_messages.c.message_rank == 1)
    ).all()

    latest_by_conversation = {
        row.conversation_id: row
        for row in latest_rows
    }

    summaries: list[ConversationSummary] = []

    for conversation in conversations:
        latest = latest_by_conversation.get(conversation.id)

        summaries.append(
            ConversationSummary(
                id=conversation.id,
                title=conversation.title,
                channel=conversation.channel,
                safety_level=conversation.safety_level,
                message_count=message_count_by_conversation.get(
                    conversation.id,
                    0,
                ),
                last_message_preview=(
                    _normalize_preview(latest.content)
                    if latest is not None
                    else None
                ),
                last_message_role=(
                    latest.role
                    if latest is not None
                    else None
                ),
                last_message_at=(
                    latest.created_at
                    if latest is not None
                    else None
                ),
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
            )
        )

    return summaries
