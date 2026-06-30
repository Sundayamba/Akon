from datetime import datetime

from pydantic import BaseModel, Field


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