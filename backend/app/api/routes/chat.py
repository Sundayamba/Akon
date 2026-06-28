from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.conversation import Conversation, Message
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationDetailResponse,
    ConversationSummary,
    MemoryCandidateItem,
    MessageItem,
)
from app.services.akon_engine import generate_akon_reply
from app.services.audit_service import create_audit_log
from app.services.memory_extraction_service import extract_memory_candidates
from app.services.memory_service import retrieve_memory_context
from app.services.safety_service import classify_safety

router = APIRouter()


def _create_conversation_title(message: str) -> str:
    cleaned = " ".join(message.strip().split())

    if len(cleaned) <= 60:
        return cleaned

    return f"{cleaned[:57]}..."


def _audit_risk_from_safety_level(safety_level: str) -> str:
    if safety_level == "S4":
        return "critical"

    if safety_level == "S3":
        return "high"

    if safety_level in {"S1", "S2"}:
        return "medium"

    return "low"


@router.post("/message", response_model=ChatMessageResponse)
def send_chat_message(
    payload: ChatMessageRequest,
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    conversation_id = payload.conversation_id or str(uuid4())

    conversation = db.get(Conversation, conversation_id)

    if conversation is None:
        conversation = Conversation(
            id=conversation_id,
            title=_create_conversation_title(payload.message),
            channel="text",
        )
        db.add(conversation)
        db.flush()

    safety_result = classify_safety(payload.message)

    memory_context = retrieve_memory_context(
        db=db,
        message=payload.message,
    )

    reply = generate_akon_reply(
        message=payload.message,
        safety_result=safety_result,
        memory_context=memory_context,
    )

    memory_candidates_raw = extract_memory_candidates(
        message=payload.message,
        safety_result=safety_result,
    )

    memory_candidates = [
        MemoryCandidateItem(
            memory_type=candidate["memory_type"],
            content=candidate["content"],
            source=candidate["source"],
            confidence=candidate["confidence"],
            sensitivity=candidate["sensitivity"],
            consent_required=candidate["consent_required"],
            reason=candidate["reason"],
        )
        for candidate in memory_candidates_raw
    ]

    conversation.safety_level = safety_result["level"]

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=payload.message,
        safety_level=safety_result["level"],
        detected_emotion=safety_result.get("detected_emotion"),
    )

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=reply,
        safety_level=safety_result["level"],
        detected_emotion=safety_result.get("detected_emotion"),
    )

    db.add(user_message)
    db.add(assistant_message)
    db.flush()

    create_audit_log(
        db,
        action="chat.message.created",
        entity_type="conversation",
        entity_id=conversation.id,
        risk_level=_audit_risk_from_safety_level(safety_result["level"]),
        source="chat_route",
        details={
            "safety_level": safety_result["level"],
            "detected_emotion": safety_result.get("detected_emotion"),
            "memory_candidate_count": len(memory_candidates),
            "user_message_id": user_message.id,
            "assistant_message_id": assistant_message.id,
            "message_length": len(payload.message),
        },
    )

    db.commit()
    db.refresh(conversation)

    return ChatMessageResponse(
        reply=reply,
        safety_level=safety_result["level"],
        detected_emotion=safety_result.get("detected_emotion"),
        conversation_id=conversation.id,
        memory_candidates=memory_candidates,
    )


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    db: Session = Depends(get_db),
) -> list[ConversationSummary]:
    conversations = db.scalars(
        select(Conversation)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
    ).all()

    return [
        ConversationSummary(
            id=conversation.id,
            title=conversation.title,
            channel=conversation.channel,
            safety_level=conversation.safety_level,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )
        for conversation in conversations
    ]


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> ConversationDetailResponse:
    conversation = db.get(Conversation, conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
    ).all()

    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        channel=conversation.channel,
        safety_level=conversation.safety_level,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            MessageItem(
                id=message.id,
                role=message.role,
                content=message.content,
                safety_level=message.safety_level,
                detected_emotion=message.detected_emotion,
                created_at=message.created_at,
            )
            for message in messages
        ],
    )