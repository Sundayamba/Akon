from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.memory import MemoryItem
from app.schemas.memory import (
    MemoryCandidateConfirmRequest,
    MemoryCreateRequest,
    MemoryItemResponse,
    MemoryUpdateRequest,
)

router = APIRouter()


def _to_memory_response(memory: MemoryItem) -> MemoryItemResponse:
    return MemoryItemResponse(
        id=memory.id,
        memory_type=memory.memory_type,
        content=memory.content,
        source=memory.source,
        confidence=memory.confidence,
        sensitivity=memory.sensitivity,
        consent_state=memory.consent_state,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
    )


@router.get("", response_model=list[MemoryItemResponse])
def list_memories(
    db: Session = Depends(get_db),
) -> list[MemoryItemResponse]:
    memories = db.scalars(
        select(MemoryItem).order_by(MemoryItem.updated_at.desc())
    ).all()

    return [_to_memory_response(memory) for memory in memories]


@router.post(
    "",
    response_model=MemoryItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_memory(
    payload: MemoryCreateRequest,
    db: Session = Depends(get_db),
) -> MemoryItemResponse:
    memory = MemoryItem(
        memory_type=payload.memory_type,
        content=payload.content,
        source=payload.source,
        confidence=payload.confidence,
        sensitivity=payload.sensitivity,
        consent_state=payload.consent_state,
    )

    db.add(memory)
    db.commit()
    db.refresh(memory)

    return _to_memory_response(memory)


@router.post(
    "/confirm-candidate",
    response_model=MemoryItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def confirm_memory_candidate(
    payload: MemoryCandidateConfirmRequest,
    db: Session = Depends(get_db),
) -> MemoryItemResponse:
    if not payload.user_confirmed:
        raise HTTPException(
            status_code=400,
            detail="User confirmation is required before saving this memory candidate.",
        )

    memory = MemoryItem(
        memory_type=payload.memory_type,
        content=payload.content,
        source=payload.source or "chat_candidate",
        confidence=payload.confidence,
        sensitivity=payload.sensitivity,
        consent_state="explicit",
    )

    db.add(memory)
    db.commit()
    db.refresh(memory)

    return _to_memory_response(memory)


@router.get("/{memory_id}", response_model=MemoryItemResponse)
def get_memory(
    memory_id: str,
    db: Session = Depends(get_db),
) -> MemoryItemResponse:
    memory = db.get(MemoryItem, memory_id)

    if memory is None:
        raise HTTPException(
            status_code=404,
            detail="Memory not found.",
        )

    return _to_memory_response(memory)


@router.patch("/{memory_id}", response_model=MemoryItemResponse)
def update_memory(
    memory_id: str,
    payload: MemoryUpdateRequest,
    db: Session = Depends(get_db),
) -> MemoryItemResponse:
    memory = db.get(MemoryItem, memory_id)

    if memory is None:
        raise HTTPException(
            status_code=404,
            detail="Memory not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(memory, field, value)

    db.commit()
    db.refresh(memory)

    return _to_memory_response(memory)


@router.post("/{memory_id}/revoke", response_model=MemoryItemResponse)
def revoke_memory(
    memory_id: str,
    db: Session = Depends(get_db),
) -> MemoryItemResponse:
    memory = db.get(MemoryItem, memory_id)

    if memory is None:
        raise HTTPException(
            status_code=404,
            detail="Memory not found.",
        )

    memory.consent_state = "revoked"

    db.commit()
    db.refresh(memory)

    return _to_memory_response(memory)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(
    memory_id: str,
    db: Session = Depends(get_db),
) -> None:
    memory = db.get(MemoryItem, memory_id)

    if memory is None:
        raise HTTPException(
            status_code=404,
            detail="Memory not found.",
        )

    db.delete(memory)
    db.commit()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_all_memories(
    db: Session = Depends(get_db),
) -> None:
    memories = db.scalars(select(MemoryItem)).all()

    for memory in memories:
        db.delete(memory)

    db.commit()