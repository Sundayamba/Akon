from app.services.study_note_candidate_service import (
    build_study_note_candidate,
    is_study_note_save_request,
)


def test_detects_study_note_save_request() -> None:
    assert is_study_note_save_request("Turn this lesson into a study note.")
    assert is_study_note_save_request("Save the key point.")
    assert is_study_note_save_request("Help me create a study-note memory.")


def test_ignores_normal_study_request() -> None:
    assert not is_study_note_save_request("Teach me the OSI model.")


def test_builds_candidate_from_recent_lesson() -> None:
    messages = [
        {
            "role": "user",
            "content": "Teach me DNS so I will remember it.",
        },
        {
            "role": "assistant",
            "content": (
                "DNS means Domain Name System. It translates human-readable domain "
                "names such as example.com into IP addresses that computers use to "
                "locate systems across a network. DNS commonly uses port 53."
            ),
        },
    ]

    candidate = build_study_note_candidate(
        message="Turn this lesson into a study note.",
        safety_result={"level": "S0"},
        conversation_messages=messages,
    )

    assert candidate is not None
    assert candidate["memory_type"] == "study_note"
    assert candidate["source"] == "study_session_candidate"
    assert candidate["consent_required"] is True
    assert candidate["content"].startswith("DNS:")
    assert "**" not in candidate["content"]
    assert "#" not in candidate["content"]


def test_does_not_build_candidate_from_study_scaffold() -> None:
    messages = [
        {
            "role": "assistant",
            "content": (
                "Study Retention Mode. Understand it, compress it, recall it, quiz it, "
                "and save it. Send the topic or paste your note now."
            ),
        },
    ]

    candidate = build_study_note_candidate(
        message="Turn this lesson into a study note.",
        safety_result={"level": "S0"},
        conversation_messages=messages,
    )

    assert candidate is None


def test_safety_flow_blocks_study_note_candidate() -> None:
    candidate = build_study_note_candidate(
        message="Save this lesson.",
        safety_result={"level": "S4"},
        conversation_messages=[
            {
                "role": "assistant",
                "content": "A long lesson that would otherwise qualify for memory extraction.",
            },
        ],
    )

    assert candidate is None