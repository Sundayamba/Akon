import pytest

from app.services.emotion_service import detect_emotion


@pytest.mark.parametrize(
    ("message", "expected_emotion"),
    [
        ("I feel calm and steady right now.", "calm"),
        ("I am stressed about this deadline.", "stressed"),
        ("I feel sad about what happened.", "sad"),
        ("I am anxious about the call.", "anxious"),
        ("I am angry that this keeps breaking.", "angry"),
        ("I feel overwhelmed and stressed today.", "overwhelmed"),
        ("I feel lonely even around people.", "lonely"),
        ("I am confused and not sure what to do.", "confused"),
        ("I am hopeful things will get better.", "hopeful"),
        ("Help me plan my day.", "neutral"),
    ],
)
def test_detect_emotion_returns_basic_non_clinical_labels(
    message: str,
    expected_emotion: str,
) -> None:
    assert detect_emotion(message) == expected_emotion


def test_hopeful_does_not_match_hopeless() -> None:
    assert detect_emotion("I feel hopeless and empty.") == "sad"
