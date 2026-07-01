from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.conversation import Conversation, Message, MessageFeedback
from app.models.user import User
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationDetailResponse,
    ConversationReflectionResponse,
    ConversationSummary,
    GroundingToolItem,
    MemoryCandidateItem,
    MessageFeedbackRequest,
    MessageFeedbackResponse,
    MessageItem,
)
from app.services.akon_engine import generate_akon_reply
from app.services.audit_service import create_audit_log
from app.services.auth_service import get_current_user
from app.services.llm_provider import LLMProviderError
from app.services.memory_extraction_service import extract_memory_candidates
from app.services.memory_service import retrieve_memory_context
from app.services.reflection_service import build_conversation_reflection
from app.services.safety_service import classify_safety
from app.services.support_strategy_service import get_grounding_tool

router = APIRouter()

GROUNDING_EMOTIONS = {
    "overwhelmed",
    "stressed",
    "anxious",
    "angry",
    "confused",
    "sad",
    "lonely",
}


def _create_conversation_title(message: str) -> str:
    cleaned = " ".join(message.strip().split())

    if len(cleaned) <= 60:
        return cleaned

    return f"{cleaned[:57]}..."


def _audit_risk_from_safety_level(safety_level: str | None) -> str:
    if safety_level == "S4":
        return "critical"

    if safety_level == "S3":
        return "high"

    if safety_level in {"S1", "S2"}:
        return "medium"

    return "low"


def _build_grounding_tool_response(
    safety_level: str,
    detected_emotion: str | None,
) -> GroundingToolItem | None:
    """
    Return a lightweight grounding tool for ordinary emotional support moments.

    S4 crisis flow remains dedicated to urgent safety guidance and should not be
    mixed with general grounding UX.
    """
    if safety_level == "S4":
        return None

    if detected_emotion not in GROUNDING_EMOTIONS:
        return None

    tool = get_grounding_tool(detected_emotion)

    return GroundingToolItem(
        name=tool["name"],
        instruction=tool["instruction"],
    )


def _get_user_message_feedback(
    db: Session,
    user_id: str,
    message_ids: list[str],
) -> dict[str, str]:
    if not message_ids:
        return {}

    feedback_items = db.scalars(
        select(MessageFeedback)
        .where(MessageFeedback.user_id == user_id)
        .where(MessageFeedback.message_id.in_(message_ids))
    ).all()

    return {
        feedback.message_id: feedback.rating
        for feedback in feedback_items
    }


def _get_owned_conversation(
    db: Session,
    conversation_id: str,
    user_id: str,
) -> Conversation:
    conversation = db.get(Conversation, conversation_id)

    if conversation is None or conversation.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return conversation


def _get_owned_conversation_messages(
    db: Session,
    conversation_id: str,
    user_id: str,
) -> list[Message]:
    return list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .where(Message.user_id == user_id)
            .order_by(Message.created_at.asc())
        ).all()
    )


def _raise_ai_unavailable_error() -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Akon's AI provider is temporarily unavailable. "
            "Please try again shortly."
        ),
    )


@router.post("/message", response_model=ChatMessageResponse)
def send_chat_message(
    payload: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    conversation_id = payload.conversation_id or str(uuid4())

    conversation = db.get(Conversation, conversation_id)

    if conversation is not None and conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    if conversation is None:
        conversation = Conversation(
            id=conversation_id,
            user_id=current_user.id,
            title=_create_conversation_title(payload.message),
            channel="text",
        )
        db.add(conversation)
        db.flush()

    safety_result = classify_safety(payload.message)
    safety_level = safety_result["level"]
    detected_emotion = safety_result.get("detected_emotion")

    memory_context = retrieve_memory_context(
        db=db,
        user_id=current_user.id,
        message=payload.message,
    )

    try:
        reply = generate_akon_reply(
            message=payload.message,
            safety_result=safety_result,
            memory_context=memory_context,
        )
    except LLMProviderError:
        db.rollback()
        _raise_ai_unavailable_error()

    grounding_tool = _build_grounding_tool_response(
        safety_level=safety_level,
        detected_emotion=detected_emotion,
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

    conversation.safety_level = safety_level

    user_message = Message(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="user",
        content=payload.message,
        safety_level=safety_level,
        detected_emotion=detected_emotion,
    )

    assistant_message = Message(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="assistant",
        content=reply,
        safety_level=safety_level,
        detected_emotion=detected_emotion,
    )

    db.add(user_message)
    db.add(assistant_message)
    db.flush()

    create_audit_log(
        db,
        action="chat.message.created",
        entity_type="conversation",
        entity_id=conversation.id,
        actor_user_id=current_user.id,
        risk_level=_audit_risk_from_safety_level(safety_level),
        source="chat_route",
        details={
            "safety_level": safety_level,
            "detected_emotion": detected_emotion,
            "grounding_tool": grounding_tool.name if grounding_tool else None,
            "memory_candidate_count": len(memory_candidates),
            "user_message_id": user_message.id,
            "assistant_message_id": assistant_message.id,
            "message_length": len(payload.message),
        },
    )

    db.commit()
    db.refresh(conversation)
    db.refresh(assistant_message)

    return ChatMessageResponse(
        reply=reply,
        safety_level=safety_level,
        detected_emotion=detected_emotion,
        grounding_tool=grounding_tool,
        conversation_id=conversation.id,
        assistant_message_id=assistant_message.id,
        memory_candidates=memory_candidates,
    )


@router.post(
    "/messages/{message_id}/feedback",
    response_model=MessageFeedbackResponse,
)
def submit_message_feedback(
    message_id: str,
    payload: MessageFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageFeedbackResponse:
    message = db.get(Message, message_id)

    if message is None or message.user_id != current_user.id:
        raise HTTPException(
            status_code=404,
            detail="Message not found.",
        )

    if message.role != "assistant":
        raise HTTPException(
            status_code=400,
            detail="Feedback can only be submitted for Akon's replies.",
        )

    existing_feedback = db.scalar(
        select(MessageFeedback)
        .where(MessageFeedback.message_id == message.id)
        .where(MessageFeedback.user_id == current_user.id)
    )

    note = payload.note.strip() if payload.note else None

    if existing_feedback is None:
        feedback = MessageFeedback(
            message_id=message.id,
            conversation_id=message.conversation_id,
            user_id=current_user.id,
            rating=payload.rating,
            note=note,
        )
        db.add(feedback)
        audit_action = "message.feedback.created"
    else:
        feedback = existing_feedback
        feedback.rating = payload.rating
        feedback.note = note
        audit_action = "message.feedback.updated"

    db.flush()

    create_audit_log(
        db,
        action=audit_action,
        entity_type="message_feedback",
        entity_id=feedback.id,
        actor_user_id=current_user.id,
        risk_level="low",
        source="chat_route",
        details={
            "message_id": message.id,
            "conversation_id": message.conversation_id,
            "rating": feedback.rating,
            "has_note": bool(feedback.note),
        },
    )

    db.commit()
    db.refresh(feedback)

    return MessageFeedbackResponse(
        id=feedback.id,
        message_id=feedback.message_id,
        conversation_id=feedback.conversation_id,
        rating=feedback.rating,
        note=feedback.note,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
    )


@router.post(
    "/conversations/{conversation_id}/reflection",
    response_model=ConversationReflectionResponse,
)
def reflect_on_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationReflectionResponse:
    conversation = _get_owned_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )

    messages = _get_owned_conversation_messages(
        db=db,
        conversation_id=conversation.id,
        user_id=current_user.id,
    )

    if not messages:
        raise HTTPException(
            status_code=400,
            detail="Conversation has no messages to reflect on.",
        )

    reflection = build_conversation_reflection(
        conversation_id=conversation.id,
        messages=[
            {
                "role": message.role,
                "content": message.content,
                "detected_emotion": message.detected_emotion,
                "safety_level": message.safety_level,
            }
            for message in messages
        ],
    )

    create_audit_log(
        db,
        action="conversation.reflection.generated",
        entity_type="conversation",
        entity_id=conversation.id,
        actor_user_id=current_user.id,
        risk_level=_audit_risk_from_safety_level(conversation.safety_level),
        source="chat_route",
        details={
            "message_count": reflection.message_count,
            "dominant_emotion": reflection.dominant_emotion,
            "safety_level": conversation.safety_level,
        },
    )

    db.commit()

    return reflection


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConversationSummary]:
    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetailResponse:
    conversation = _get_owned_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )

    messages = _get_owned_conversation_messages(
        db=db,
        conversation_id=conversation.id,
        user_id=current_user.id,
    )

    feedback_by_message_id = _get_user_message_feedback(
        db=db,
        user_id=current_user.id,
        message_ids=[message.id for message in messages],
    )

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
                feedback_rating=feedback_by_message_id.get(message.id),
                created_at=message.created_at,
            )
            for message in messages
        ],
    )