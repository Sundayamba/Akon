from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthUserResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services.audit_service import create_audit_log
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    ensure_password_policy,
    get_current_user,
    get_user_by_email,
    hash_password,
    normalize_email,
)
from app.services.rate_limit_service import check_rate_limit

router = APIRouter()


def _to_auth_user_response(user: User) -> AuthUserResponse:
    return AuthUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post(
    "/register",
    response_model=AuthUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> AuthUserResponse:
    normalized_email = normalize_email(payload.email)

    check_rate_limit(
        key=f"auth:register:{normalized_email}",
        max_attempts=settings.auth_rate_limit_max_attempts,
        window_seconds=settings.auth_rate_limit_window_seconds,
    )

    ensure_password_policy(
        password=payload.password,
        email=normalized_email,
    )

    existing_user = get_user_by_email(
        db=db,
        email=normalized_email,
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=409,
            detail="A user with this email already exists.",
        )

    user = User(
        email=normalized_email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        is_active=True,
    )

    db.add(user)
    db.flush()

    create_audit_log(
        db,
        action="auth.user.registered",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        risk_level="low",
        source="auth_route",
        details={
            "email_domain": normalized_email.split("@")[-1],
            "has_display_name": bool(payload.display_name),
        },
    )

    db.commit()
    db.refresh(user)

    return _to_auth_user_response(user)


@router.post("/login", response_model=TokenResponse)
def login_user(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    normalized_email = normalize_email(payload.email)

    check_rate_limit(
        key=f"auth:login:{normalized_email}",
        max_attempts=settings.auth_rate_limit_max_attempts,
        window_seconds=settings.auth_rate_limit_window_seconds,
    )

    user = authenticate_user(
        db=db,
        email=normalized_email,
        password=payload.password,
    )

    if user is None:
        create_audit_log(
            db,
            action="auth.login.failed",
            entity_type="user",
            entity_id=None,
            actor_user_id=None,
            risk_level="medium",
            source="auth_route",
            details={
                "email_domain": normalized_email.split("@")[-1],
            },
        )
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    access_token, expires_in = create_access_token(subject=user.id)

    create_audit_log(
        db,
        action="auth.login.succeeded",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        risk_level="low",
        source="auth_route",
        details={
            "email_domain": user.email.split("@")[-1],
        },
    )

    db.commit()

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        user=_to_auth_user_response(user),
    )


@router.get("/me", response_model=AuthUserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
) -> AuthUserResponse:
    return _to_auth_user_response(current_user)