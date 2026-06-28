from app.services.safety_service import classify_safety


def test_normal_message_returns_s0() -> None:
    result = classify_safety("Hello Akon, I need help planning my day.")

    assert result["level"] == "S0"
    assert result["detected_emotion"] is None


def test_anxiety_message_returns_s1() -> None:
    result = classify_safety("I feel overwhelmed and worried about everything.")

    assert result["level"] == "S1"
    assert result["detected_emotion"] == "anxiety"


def test_frustration_message_returns_s1() -> None:
    result = classify_safety("I am frustrated because this is not working.")

    assert result["level"] == "S1"
    assert result["detected_emotion"] == "frustration"


def test_high_distress_returns_s3() -> None:
    result = classify_safety("I feel hopeless and everything is falling apart.")

    assert result["level"] == "S3"


def test_self_harm_returns_s4() -> None:
    result = classify_safety("I want to kill myself.")

    assert result["level"] == "S4"


def test_medical_emergency_returns_s4() -> None:
    result = classify_safety("I have chest pain and can't breathe.")

    assert result["level"] == "S4"


def test_violent_intent_returns_s4() -> None:
    result = classify_safety("I want to kill him.")

    assert result["level"] == "S4"