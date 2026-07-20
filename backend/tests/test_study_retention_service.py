from app.services.study_retention_service import (
    build_study_retention_reply,
    extract_study_topic,
    is_study_retention_request,
)


def test_detects_study_retention_request() -> None:
    assert is_study_retention_request("Teach me subnetting so I won't forget it.")
    assert is_study_retention_request("Quiz me on the OSI model.")
    assert is_study_retention_request("Help me study Linux permissions.")


def test_ignores_normal_non_study_message() -> None:
    assert not is_study_retention_request("Draft a professional email to my bank.")


def test_extracts_study_topic() -> None:
    assert extract_study_topic("Teach me DNS so I won't forget it and quiz me.") == "DNS"


def test_builds_study_retention_reply() -> None:
    reply = build_study_retention_reply("Quiz me on the OSI model.")

    assert "Study Retention Mode" in reply
    assert "Topic: the OSI model" in reply
    assert "Understand it" in reply
    assert "Recall it" in reply
    assert "Save the key point" in reply