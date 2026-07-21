from datetime import datetime

from pydantic import BaseModel, Field


class MemoryCreateRequest(BaseModel):
    memory_type: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Type of memory, such as preference, goal, constraint, cultural_context, or emotional_baseline.",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Memory content to save.",
    )
    source: str | None = Field(
        default="manual",
        max_length=100,
        description="Where this memory came from.",
    )
    confidence: str = Field(
        default="medium",
        max_length=20,
    )
    sensitivity: str = Field(
        default="low",
        max_length=20,
    )
    consent_state: str = Field(
        default="implicit",
        max_length=20,
    )


class MemoryCandidateConfirmRequest(BaseModel):
    memory_type: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Type of memory candidate being confirmed.",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Candidate memory content to save.",
    )
    source: str | None = Field(
        default="chat_candidate",
        max_length=100,
    )
    confidence: str = Field(
        default="medium",
        max_length=20,
    )
    sensitivity: str = Field(
        default="low",
        max_length=20,
    )
    consent_required: bool = Field(
        default=True,
        description="Whether the candidate requires consent before saving.",
    )
    user_confirmed: bool = Field(
        ...,
        description="Must be true before Akon saves this candidate as memory.",
    )


class MemoryUpdateRequest(BaseModel):
    memory_type: str | None = Field(
        default=None,
        min_length=2,
        max_length=50,
    )
    content: str | None = Field(
        default=None,
        min_length=1,
        max_length=4000,
    )
    source: str | None = Field(
        default=None,
        max_length=100,
    )
    confidence: str | None = Field(
        default=None,
        max_length=20,
    )
    sensitivity: str | None = Field(
        default=None,
        max_length=20,
    )
    consent_state: str | None = Field(
        default=None,
        max_length=20,
    )


class MemoryRecallPreviewRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="A user-authored query used to preview Akon's memory retrieval.",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of memory matches to return.",
    )


class MemoryRecallMatchResponse(BaseModel):
    id: str
    memory_type: str
    content: str
    source: str | None = None
    confidence: str
    sensitivity: str
    consent_state: str
    relevance_score: int = Field(ge=0)
    reasons: list[str] = Field(default_factory=list)


class MemoryRecallPreviewResponse(BaseModel):
    query: str
    is_recall_request: bool
    matched_count: int = Field(ge=0)
    matches: list[MemoryRecallMatchResponse] = Field(default_factory=list)
    privacy_note: str


class MemoryHealthResponse(BaseModel):
    total_count: int = Field(ge=0)
    active_count: int = Field(ge=0)
    explicit_count: int = Field(ge=0)
    implicit_count: int = Field(ge=0)
    revoked_count: int = Field(ge=0)
    high_sensitivity_count: int = Field(ge=0)
    low_confidence_count: int = Field(ge=0)
    review_recommended_count: int = Field(ge=0)
    duplicate_group_count: int = Field(ge=0)
    memory_type_counts: dict[str, int] = Field(default_factory=dict)
    review_recommended_memory_ids: list[str] = Field(default_factory=list)
    duplicate_groups: list[list[str]] = Field(default_factory=list)


class MemoryItemResponse(BaseModel):
    id: str
    memory_type: str
    content: str
    source: str | None = None
    confidence: str
    sensitivity: str
    consent_state: str
    created_at: datetime
    updated_at: datetime
