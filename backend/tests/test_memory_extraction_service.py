from app.services.memory_extraction_service import extract_memory_candidates


def test_extracts_preference_candidate() -> None:
    candidates = extract_memory_candidates(
        message="I prefer direct step-by-step guidance.",
        safety_result={
            "level": "S0",
            "reason": "No immediate safety concern detected.",
            "detected_emotion": None,
        },
    )

    assert len(candidates) == 1
    assert candidates[0]["memory_type"] == "preference"
    assert candidates[0]["consent_required"] is True
    assert candidates[0]["sensitivity"] == "low"


def test_extracts_goal_candidate() -> None:
    candidates = extract_memory_candidates(
        message="My goal is to build Akon into a strong AI companion app.",
        safety_result={
            "level": "S0",
            "reason": "No immediate safety concern detected.",
            "detected_emotion": None,
        },
    )

    assert len(candidates) == 1
    assert candidates[0]["memory_type"] == "goal"
    assert candidates[0]["consent_required"] is True


def test_extracts_constraint_candidate() -> None:
    candidates = extract_memory_candidates(
        message="I have limited time for development sessions.",
        safety_result={
            "level": "S0",
            "reason": "No immediate safety concern detected.",
            "detected_emotion": None,
        },
    )

    assert len(candidates) == 1
    assert candidates[0]["memory_type"] == "constraint"


def test_extracts_cultural_context_candidate() -> None:
    candidates = extract_memory_candidates(
        message="In my culture, family expectations matter a lot.",
        safety_result={
            "level": "S0",
            "reason": "No immediate safety concern detected.",
            "detected_emotion": None,
        },
    )

    assert len(candidates) == 1
    assert candidates[0]["memory_type"] == "cultural_context"


def test_extracts_emotional_baseline_candidate() -> None:
    candidates = extract_memory_candidates(
        message="I often feel overwhelmed when I have too many tasks.",
        safety_result={
            "level": "S0",
            "reason": "No immediate safety concern detected.",
            "detected_emotion": None,
        },
    )

    assert len(candidates) == 1
    assert candidates[0]["memory_type"] == "emotional_baseline"


def test_extracts_learning_goal_candidate() -> None:
    candidates = extract_memory_candidates(
        message="I want to learn cybersecurity properly this year.",
        safety_result={
            "level": "S0",
            "reason": "No immediate safety concern detected.",
            "detected_emotion": None,
        },
    )

    assert len(candidates) == 1
    assert candidates[0]["memory_type"] == "goal"


def test_sensitive_candidate_requires_high_sensitivity() -> None:
    candidates = extract_memory_candidates(
        message="I prefer that you remember my medication situation carefully.",
        safety_result={
            "level": "S0",
            "reason": "No immediate safety concern detected.",
            "detected_emotion": None,
        },
    )

    assert len(candidates) == 1
    assert candidates[0]["memory_type"] == "preference"
    assert candidates[0]["sensitivity"] == "high"
    assert candidates[0]["consent_required"] is True


def test_explicit_remember_request_creates_candidate() -> None:
    candidates = extract_memory_candidates(
        message="Remember that I prefer short and direct answers.",
        safety_result={
            "level": "S0",
            "reason": "No immediate safety concern detected.",
            "detected_emotion": None,
        },
    )

    assert len(candidates) == 1
    assert candidates[0]["memory_type"] == "preference"
    assert candidates[0]["confidence"] == "high"


def test_no_candidate_for_normal_message() -> None:
    candidates = extract_memory_candidates(
        message="Hello Akon, how are you today?",
        safety_result={
            "level": "S0",
            "reason": "No immediate safety concern detected.",
            "detected_emotion": None,
        },
    )

    assert candidates == []


def test_no_candidate_for_one_off_learning_request() -> None:
    candidates = extract_memory_candidates(
        message="Can you teach me networking basics step by step?",
        safety_result={
            "level": "S0",
            "reason": "No immediate safety concern detected.",
            "detected_emotion": None,
        },
    )

    assert candidates == []


def test_no_candidate_for_crisis_message() -> None:
    candidates = extract_memory_candidates(
        message="I want to kill myself.",
        safety_result={
            "level": "S4",
            "reason": "Possible self-harm or suicide risk detected.",
            "detected_emotion": "overwhelmed",
        },
    )

    assert candidates == []