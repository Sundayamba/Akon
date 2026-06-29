import pytest

from app.services.support_strategy_service import build_support_reply


def test_support_strategy_output_shape() -> None:
    reply = build_support_reply(
        user_message="I feel overwhelmed and stressed today.",
        detected_emotion="overwhelmed",
        safety_level="S1",
    )

    parts = reply.split("\n\n")

    assert len(parts) == 4
    assert parts[0].startswith("That sounds")
    assert "Akon senses" in parts[1]
    assert parts[2].startswith("One small step")
    assert parts[3] == "I am here with you as we sort it out."


def test_support_strategy_is_emotion_aware() -> None:
    overwhelmed_reply = build_support_reply(
        user_message="I feel overwhelmed and stressed today.",
        detected_emotion="overwhelmed",
        safety_level="S1",
    )
    confused_reply = build_support_reply(
        user_message="I am confused about what to do next.",
        detected_emotion="confused",
        safety_level="S1",
    )

    assert "overwhelm" in overwhelmed_reply.lower()
    assert "confusion" in confused_reply.lower()
    assert overwhelmed_reply != confused_reply


def test_support_strategy_keeps_memory_context_note() -> None:
    reply = build_support_reply(
        user_message="I feel overwhelmed and need guidance.",
        detected_emotion="overwhelmed",
        safety_level="S1",
        memory_context="User prefers direct, step-by-step guidance.",
    )

    assert "saved context" in reply


def test_support_strategy_rejects_higher_risk_safety_levels() -> None:
    with pytest.raises(ValueError):
        build_support_reply(
            user_message="I feel hopeless and everything is falling apart.",
            detected_emotion="overwhelmed",
            safety_level="S3",
        )
