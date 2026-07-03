from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.conversation import Conversation, Message, MessageFeedback
from app.models.user import User
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationDeleteResponse,
    ConversationDetailResponse,
    ConversationReflectionResponse,
    ConversationSummary,
    ConversationUpdateRequest,
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

TITLE_STOPWORDS = {
    "please",
    "help",
    "me",
    "with",
    "about",
    "the",
    "and",
    "for",
    "that",
    "this",
    "into",
    "from",
    "your",
    "akon",
}


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def _clip_text(value: str, limit: int = 380) -> str:
    cleaned = _normalize_text(value)

    if len(cleaned) <= limit:
        return cleaned

    return f"{cleaned[: limit - 3]}..."


def _contains_any(text: str, signals: set[str]) -> bool:
    normalized = text.lower()
    return any(signal in normalized for signal in signals)


def _create_conversation_title(message: str) -> str:
    cleaned = _normalize_text(message)
    normalized = cleaned.lower()

    if not cleaned:
        return "New conversation"

    if normalized in {
        "hi",
        "hello",
        "hey",
        "good morning",
        "goo morning",
        "good afternoon",
        "good evening",
        "how are you",
        "how are you doing",
    }:
        return "Casual check-in"

    if _contains_any(
        normalized,
        {
            "traceback",
            "error",
            "bug",
            "pytest",
            "build",
            "runtimeerror",
            "module not found",
        },
    ):
        return "Technical troubleshooting"

    if _contains_any(
        normalized,
        {
            "cybersecurity",
            "networking",
            "linux",
            "windows server",
            "active directory",
            "soc analyst",
        },
    ):
        return "Cybersecurity learning"

    if _contains_any(
        normalized,
        {
            "professional announcement",
            "write an announcement",
            "write a professional announcement",
        },
    ):
        return "Professional announcement"

    if _contains_any(
        normalized,
        {
            "write",
            "rewrite",
            "draft",
            "compose",
            "message to",
            "email",
        },
    ):
        return "Writing draft"

    if _contains_any(
        normalized,
        {
            "roadmap",
            "plan",
            "strategy",
            "next step",
            "steps",
        },
    ):
        return "Planning next steps"

    if _contains_any(
        normalized,
        {
            "should i",
            "which one",
            "choose",
            "decide",
            "worth it",
        },
    ):
        return "Decision support"

    if _contains_any(
        normalized,
        {
            "i feel overwhelmed",
            "i feel lost",
            "i feel betrayed",
            "i feel sad",
            "i am stressed",
            "i'm stressed",
        },
    ):
        return "Support conversation"

    words = [
        word.strip(".,!?;:()[]{}\"'").lower()
        for word in cleaned.split()
    ]

    meaningful_words = [
        word
        for word in words
        if len(word) >= 3 and word not in TITLE_STOPWORDS
    ]

    if meaningful_words:
        title = " ".join(meaningful_words[:7]).capitalize()
    else:
        title = cleaned

    if len(title) <= 60:
        return title

    return f"{title[:57]}..."


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


def _conversation_to_summary(conversation: Conversation) -> ConversationSummary:
    return ConversationSummary(
        id=conversation.id,
        title=conversation.title,
        channel=conversation.channel,
        safety_level=conversation.safety_level,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
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


def _find_previous_user_message(
    messages: list[Message],
    assistant_message_id: str,
) -> Message | None:
    assistant_index = next(
        (
            index
            for index, message in enumerate(messages)
            if message.id == assistant_message_id
        ),
        None,
    )

    if assistant_index is None:
        return None

    for message in reversed(messages[:assistant_index]):
        if message.role == "user":
            return message

    return None


def _messages_before_message(
    messages: list[Message],
    message_id: str,
) -> list[Message]:
    message_index = next(
        (
            index
            for index, message in enumerate(messages)
            if message.id == message_id
        ),
        None,
    )

    if message_index is None:
        return []

    return messages[:message_index]


def _build_recent_conversation_context(
    messages: list[Message],
    limit: int = 8,
) -> str | None:
    if not messages:
        return None

    recent_messages = messages[-limit:]

    context_lines = []

    for message in recent_messages:
        role = "User" if message.role == "user" else "Akon"
        context_lines.append(f"- {role}: {_clip_text(message.content)}")

    return "\n".join(context_lines)


def _build_ai_context(
    db: Session,
    *,
    user_id: str,
    message: str,
    existing_messages: list[Message] | None = None,
) -> str | None:
    context_blocks = []

    memory_context = retrieve_memory_context(
        db=db,
        user_id=user_id,
        message=message,
    )

    if memory_context:
        context_blocks.append(
            "Relevant saved memory. Use only if directly helpful:\n"
            f"{memory_context}"
        )

    recent_context = _build_recent_conversation_context(existing_messages or [])

    if recent_context:
        context_blocks.append(
            "Recent conversation context. Use this to maintain continuity without repeating it:\n"
            f"{recent_context}"
        )

    if not context_blocks:
        return None

    return "\n\n".join(context_blocks)


def _raise_ai_unavailable_error() -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Akon's AI provider is temporarily unavailable. "
            "Please try again shortly."
        ),
    )


def _build_memory_candidates(
    message: str,
    safety_result: dict,
) -> list[MemoryCandidateItem]:
    memory_candidates_raw = extract_memory_candidates(
        message=message,
        safety_result=safety_result,
    )

    return [
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

    existing_messages: list[Message] = []

    if conversation is None:
        conversation = Conversation(
            id=conversation_id,
            user_id=current_user.id,
            title=_create_conversation_title(payload.message),
            channel="text",
        )
        db.add(conversation)
        db.flush()
    else:
        existing_messages = _get_owned_conversation_messages(
            db=db,
            conversation_id=conversation.id,
            user_id=current_user.id,
        )

    safety_result = classify_safety(payload.message)
    safety_level = safety_result["level"]
    detected_emotion = safety_result.get("detected_emotion")

    ai_context = _build_ai_context(
        db=db,
        user_id=current_user.id,
        message=payload.message,
        existing_messages=existing_messages,
    )

    try:
        reply = generate_akon_reply(
            message=payload.message,
            safety_result=safety_result,
            memory_context=ai_context,
        )
    except LLMProviderError:
        db.rollback()
        _raise_ai_unavailable_error()

    grounding_tool = _build_grounding_tool_response(
        safety_level=safety_level,
        detected_emotion=detected_emotion,
    )

    memory_candidates = _build_memory_candidates(
        message=payload.message,
        safety_result=safety_result,
    )

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
            "used_ai_context": bool(ai_context),
            "recent_context_message_count": len(existing_messages[-8:]),
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
    "/messages/{message_id}/regenerate",
    response_model=ChatMessageResponse,
)
def regenerate_assistant_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    source_message = db.get(Message, message_id)

    if source_message is None or source_message.user_id != current_user.id:
        raise HTTPException(
            status_code=404,
            detail="Message not found.",
        )

    if source_message.role != "assistant":
        raise HTTPException(
            status_code=400,
            detail="Only Akon's replies can be regenerated.",
        )

    conversation = _get_owned_conversation(
        db=db,
        conversation_id=source_message.conversation_id,
        user_id=current_user.id,
    )

    messages = _get_owned_conversation_messages(
        db=db,
        conversation_id=conversation.id,
        user_id=current_user.id,
    )

    previous_user_message = _find_previous_user_message(
        messages=messages,
        assistant_message_id=source_message.id,
    )

    if previous_user_message is None:
        raise HTTPException(
            status_code=400,
            detail="Could not find the user message that produced this reply.",
        )

    prior_messages = _messages_before_message(
        messages=messages,
        message_id=previous_user_message.id,
    )

    safety_result = classify_safety(previous_user_message.content)
    safety_level = safety_result["level"]
    detected_emotion = safety_result.get("detected_emotion")

    ai_context = _build_ai_context(
        db=db,
        user_id=current_user.id,
        message=previous_user_message.content,
        existing_messages=prior_messages,
    )

    try:
        reply = generate_akon_reply(
            message=previous_user_message.content,
            safety_result=safety_result,
            memory_context=ai_context,
        )
    except LLMProviderError:
        db.rollback()
        _raise_ai_unavailable_error()

    grounding_tool = _build_grounding_tool_response(
        safety_level=safety_level,
        detected_emotion=detected_emotion,
    )

    conversation.safety_level = safety_level

    assistant_message = Message(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="assistant",
        content=reply,
        safety_level=safety_level,
        detected_emotion=detected_emotion,
    )

    db.add(assistant_message)
    db.flush()

    create_audit_log(
        db,
        action="chat.message.regenerated",
        entity_type="conversation",
        entity_id=conversation.id,
        actor_user_id=current_user.id,
        risk_level=_audit_risk_from_safety_level(safety_level),
        source="chat_route",
        details={
            "source_message_id": source_message.id,
            "previous_user_message_id": previous_user_message.id,
            "new_assistant_message_id": assistant_message.id,
            "used_ai_context": bool(ai_context),
            "safety_level": safety_level,
            "detected_emotion": detected_emotion,
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
        memory_candidates=[],
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

    return [_conversation_to_summary(conversation) for conversation in conversations]


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


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationSummary,
)
def update_conversation(
    conversation_id: str,
    payload: ConversationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationSummary:
    conversation = _get_owned_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )

    cleaned_title = _normalize_text(payload.title)

    if not cleaned_title:
        raise HTTPException(
            status_code=400,
            detail="Conversation title cannot be empty.",
        )

    old_title = conversation.title
    conversation.title = cleaned_title

    create_audit_log(
        db,
        action="conversation.updated",
        entity_type="conversation",
        entity_id=conversation.id,
        actor_user_id=current_user.id,
        risk_level="low",
        source="chat_route",
        details={
            "old_title": old_title,
            "new_title": cleaned_title,
        },
    )

    db.commit()
    db.refresh(conversation)

    return _conversation_to_summary(conversation)


@router.delete(
    "/conversations/{conversation_id}",
    response_model=ConversationDeleteResponse,
)
def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDeleteResponse:
    conversation = _get_owned_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )

    deleted_title = conversation.title

    db.execute(
        delete(MessageFeedback)
        .where(MessageFeedback.conversation_id == conversation.id)
        .where(MessageFeedback.user_id == current_user.id)
    )

    db.execute(
        delete(Message)
        .where(Message.conversation_id == conversation.id)
        .where(Message.user_id == current_user.id)
    )

    create_audit_log(
        db,
        action="conversation.deleted",
        entity_type="conversation",
        entity_id=conversation.id,
        actor_user_id=current_user.id,
        risk_level="low",
        source="chat_route",
        details={
            "title": deleted_title,
        },
    )

    db.delete(conversation)
    db.commit()

    return ConversationDeleteResponse(
        id=conversation_id,
        deleted=True,
    )