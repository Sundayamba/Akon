from typing import Any


SELF_HARM_KEYWORDS = [
    "kill myself",
    "end my life",
    "suicide",
    "i want to die",
    "i don't want to live",
    "i dont want to live",
    "harm myself",
    "hurt myself",
    "take my life",
]

MEDICAL_EMERGENCY_KEYWORDS = [
    "chest pain",
    "can't breathe",
    "cant breathe",
    "difficulty breathing",
    "overdose",
    "took too many pills",
    "severe bleeding",
    "unconscious",
    "seizure",
    "stroke",
    "poisoned",
]

VIOLENCE_KEYWORDS = [
    "i will kill",
    "i want to kill",
    "i am going to attack",
    "i will attack",
    "hurt them badly",
    "stab",
    "shoot",
]

HIGH_DISTRESS_KEYWORDS = [
    "i can't take it anymore",
    "i cant take it anymore",
    "i am breaking down",
    "i'm breaking down",
    "i feel hopeless",
    "everything is falling apart",
    "i am losing control",
    "i'm losing control",
]

FRUSTRATION_KEYWORDS = [
    "angry",
    "annoyed",
    "frustrated",
    "tired of this",
    "this is stupid",
    "why is this not working",
    "i hate this",
]

ANXIETY_KEYWORDS = [
    "anxious",
    "panic",
    "panicking",
    "worried",
    "scared",
    "afraid",
    "overwhelmed",
    "nervous",
]

SADNESS_KEYWORDS = [
    "sad",
    "lonely",
    "depressed",
    "heartbroken",
    "discouraged",
    "worthless",
    "empty",
]

EXCITEMENT_KEYWORDS = [
    "excited",
    "happy",
    "great news",
    "amazing",
    "finally",
    "i did it",
    "let's go",
    "lets go",
]


def _contains_any(message: str, keywords: list[str]) -> bool:
    normalized = message.lower()
    return any(keyword in normalized for keyword in keywords)


def _detect_emotion(message: str) -> str | None:
    if _contains_any(message, FRUSTRATION_KEYWORDS):
        return "frustration"

    if _contains_any(message, ANXIETY_KEYWORDS):
        return "anxiety"

    if _contains_any(message, SADNESS_KEYWORDS):
        return "sadness"

    if _contains_any(message, EXCITEMENT_KEYWORDS):
        return "excitement"

    return None


def classify_safety(message: str) -> dict[str, Any]:
    """
    Temporary MVP rule-based classifier.

    This is intentionally simple and must later be replaced or supported by
    a stronger safety model before production launch.
    """
    detected_emotion = _detect_emotion(message)

    if _contains_any(message, SELF_HARM_KEYWORDS):
        return {
            "level": "S4",
            "reason": "Possible self-harm or suicide risk detected.",
            "detected_emotion": detected_emotion or "crisis",
        }

    if _contains_any(message, MEDICAL_EMERGENCY_KEYWORDS):
        return {
            "level": "S4",
            "reason": "Possible medical emergency detected.",
            "detected_emotion": detected_emotion or "crisis",
        }

    if _contains_any(message, VIOLENCE_KEYWORDS):
        return {
            "level": "S4",
            "reason": "Possible violent intent detected.",
            "detected_emotion": detected_emotion or "anger",
        }

    if _contains_any(message, HIGH_DISTRESS_KEYWORDS):
        return {
            "level": "S3",
            "reason": "High emotional distress detected.",
            "detected_emotion": detected_emotion or "distress",
        }

    if detected_emotion:
        return {
            "level": "S1",
            "reason": f"Emotional signal detected: {detected_emotion}.",
            "detected_emotion": detected_emotion,
        }

    return {
        "level": "S0",
        "reason": "No immediate safety concern detected.",
        "detected_emotion": None,
    }