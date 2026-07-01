from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


FeedbackRating = Literal["helpful", "not_helpful"]


class MemoryCandidateItem(BaseModel):
    memory_type: str
    content: str
    source: str
    confidence: str
    sensitivity: str
    consent_required: bool
    reason: str


class GroundingToolItem(BaseModel):
    name: str = Field(
        ...,
        description="Short name for the grounding support tool.",
    )
    instruction: str = Field(
        ...,
        description="Brief non-clinical grounding instruction.",
    )


class ChatMessageRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="The user's message to Akon.",
    )
    conversation_id: str | None = Field(
        default=None,
        description="Optional existing conversation ID.",
    )
    language: str | None = Field(
        default=None,
        description="Optional preferred response language.",
    )


class ChatMessageResponse(BaseModel):
    reply: str = Field(
        ...,
        description="Akon's response.",
    )
    safety_level: str = Field(
        ...,
        description="Safety classification level for the message.",
    )
    detected_emotion: str | None = Field(
        default=None,
        description="Detected emotional signal, if any.",
    )
    grounding_tool: GroundingToolItem | None = Field(
        default=None,
        description="Optional lightweight grounding tool for stressful or emotionally heavy moments.",
    )
    conversation_id: str = Field(
        ...,
        description="Conversation ID used for the exchange.",
    )
    assistant_message_id: str = Field(
        ...,
        description="Message ID for Akon's reply. Used for optional quality feedback.",
    )
    memory_candidates: list[MemoryCandidateItem] = Field(
        default_factory=list,
        description="Possible memories detected from the message. These are not saved until user confirms.",
    )


class MessageItem(BaseModel):
    id: str
    role: str
    content: str
    safety_level: str | None = None
    detected_emotion: str | None = None
    feedback_rating: str | None = None
    created_at: datetime


class ConversationSummary(BaseModel):
    id: str
    title: str | None = None
    channel: str
    safety_level: str | None = None
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(BaseModel):
    id: str
    title: str | None = None
    channel: str
    safety_level: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageItem]


class MessageFeedbackRequest(BaseModel):
    rating: FeedbackRating = Field(
        ...,
        description="Whether Akon's reply felt helpful or not helpful.",
    )
    note: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional short note explaining the feedback.",
    )


class MessageFeedbackResponse(BaseModel):
    id: str
    message_id: str
    conversation_id: str
    rating: str
    note: str | None = None
    created_at: datetime
    updated_at: datetime


class ConversationReflectionResponse(BaseModel):
    conversation_id: str = Field(
        ...,
        description="Conversation ID reflected on.",
    )
    title: str = Field(
        ...,
        description="Short warm title for the reflection.",
    )
    summary: str = Field(
        ...,
        description="Gentle non-clinical summary of the conversation theme.",
    )
    dominant_emotion: str | None = Field(
        default=None,
        description="Most common detected emotion in the conversation, if available.",
    )
    supportive_next_step: str = Field(
        ...,
        description="One gentle next step suggested by the reflection.",
    )
    message_count: int = Field(
        ...,
        ge=1,
        description="Number of messages considered.",
    )