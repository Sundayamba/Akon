from app.services.reflection_service import build_conversation_reflection


def test_build_reflection_uses_dominant_emotion() -> None:
    reflection = build_conversation_reflection(
        conversation_id="conversation-1",
        messages=[
            {
                "role": "user",
                "content": "I feel very overwhelmed today.",
                "detected_emotion": "overwhelmed",
                "safety_level": "S1",
            },
            {
                "role": "assistant",
                "content": "That sounds like a lot to carry.",
                "detected_emotion": "overwhelmed",
                "safety_level": "S1",
            },
            {
                "role": "user",
                "content": "I do not know where to start.",
                "detected_emotion": "confused",
                "safety_level": "S1",
            },
        ],
    )

    assert reflection.conversation_id == "conversation-1"
    assert reflection.dominant_emotion == "overwhelmed"
    assert reflection.message_count == 3
    assert reflection.title == "A moment with a lot to carry"
    assert "stretched" in reflection.summary
    assert reflection.supportive_next_step


def test_build_reflection_falls_back_to_neutral() -> None:
    reflection = build_conversation_reflection(
        conversation_id="conversation-2",
        messages=[
            {
                "role": "user",
                "content": "I want to think through my next step.",
                "detected_emotion": None,
                "safety_level": "S0",
            },
            {
                "role": "assistant",
                "content": "Let us slow it down.",
                "detected_emotion": None,
                "safety_level": "S0",
            },
        ],
    )

    assert reflection.conversation_id == "conversation-2"
    assert reflection.dominant_emotion == "neutral"
    assert reflection.title == "A conversation worth noticing"
    assert reflection.message_count == 2


def test_build_reflection_marks_single_user_message_as_snapshot() -> None:
    reflection = build_conversation_reflection(
        conversation_id="conversation-3",
        messages=[
            {
                "role": "user",
                "content": "I am anxious about this decision.",
                "detected_emotion": "anxious",
                "safety_level": "S1",
            },
        ],
    )

    assert reflection.dominant_emotion == "anxious"
    assert "small snapshot" in reflection.summary