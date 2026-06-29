from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=True)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)

    return hashed_password.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    password_bytes = password.encode("utf-8")
    password_hash_bytes = password_hash.encode("utf-8")

    return bcrypt.checkpw(password_bytes, password_hash_bytes)


def create_access_token(
    *,
    subject: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, int]:
    expire_delta = expires_delta or timedelta(
        minutes=settings.access_token_expire_minutes
    )
    expires_at = datetime.now(UTC) + expire_delta

    payload: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "exp": expires_at,
        "iat": datetime.now(UTC),
    }

    token = jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return token, int(expire_delta.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token type.",
        )

    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token subject.",
        )

    return payload


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    normalized_email = normalize_email(email)

    return db.scalar(
        select(User).where(User.email == normalized_email)
    )


def authenticate_user(
    db: Session,
    *,
    email: str,
    password: str,
) -> User | None:
    user = get_user_by_email(
        db=db,
        email=email,
    )

    if user is None:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)
    user_id = payload["sub"]

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user was not found.",
        )

    return user