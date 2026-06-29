from app.services.akon_engine import generate_akon_reply


def test_engine_uses_support_strategy_for_mock_supportive_reply() -> None:
    reply = generate_akon_reply(
        message="I feel overwhelmed and stressed today.",
        safety_result={
            "level": "S1",
            "reason": "Emotional signal detected: overwhelmed.",
            "detected_emotion": "overwhelmed",
        },
    )

    assert "makes sense" in reply
    assert "Akon senses" in reply
    assert "One small step" in reply
    assert "I am here with you" in reply


def test_engine_safety_behavior_takes_priority_for_high_distress() -> None:
    reply = generate_akon_reply(
        message="I feel hopeless and everything is falling apart.",
        safety_result={
            "level": "S3",
            "reason": "High emotional distress detected.",
            "detected_emotion": "overwhelmed",
        },
    )

    assert "What is the biggest pressure on you at this moment?" in reply
    assert "Akon senses" not in reply


def test_engine_safety_behavior_takes_priority_for_crisis() -> None:
    reply = generate_akon_reply(
        message="I want to kill myself.",
        safety_result={
            "level": "S4",
            "reason": "Possible self-harm or suicide risk detected.",
            "detected_emotion": "overwhelmed",
        },
    )

    assert "Your safety matters" in reply
    assert "Akon senses" not in reply
