from datetime import UTC, datetime, timedelta
from threading import Lock

from fastapi import HTTPException, status


_rate_limit_lock = Lock()
_rate_limit_attempts: dict[str, list[datetime]] = {}


def check_rate_limit(
    *,
    key: str,
    max_attempts: int,
    window_seconds: int,
    detail: str = "Too many requests. Please try again later.",
) -> None:
    """
    Simple in-memory rate-limit foundation.

    This is acceptable for local MVP development and tests.
    Before production or multi-worker deployment, this must be replaced with
    Redis or another shared external rate-limit store.
    """
    now = datetime.now(UTC)
    window_start = now - timedelta(seconds=window_seconds)

    with _rate_limit_lock:
        attempts = [
            attempt_time
            for attempt_time in _rate_limit_attempts.get(key, [])
            if attempt_time > window_start
        ]

        if len(attempts) >= max_attempts:
            _rate_limit_attempts[key] = attempts

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail,
            )

        attempts.append(now)
        _rate_limit_attempts[key] = attempts


def reset_rate_limit_state() -> None:
    """
    Clear in-memory rate-limit state.

    This is used by tests so one test cannot poison another.
    """
    with _rate_limit_lock:
        _rate_limit_attempts.clear()