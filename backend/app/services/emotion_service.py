import re


NEUTRAL_EMOTION = "neutral"

EMOTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "overwhelmed": (
        "overwhelmed",
        "too much",
        "can't handle",
        "cant handle",
        "everything at once",
        "everything is falling apart",
        "drowning in",
        "spread too thin",
        "burned out",
        "burnt out",
    ),
    "anxious": (
        "anxious",
        "anxiety",
        "panic",
        "panicking",
        "worried",
        "worry",
        "scared",
        "afraid",
        "nervous",
        "fearful",
        "can't stop thinking",
        "cant stop thinking",
    ),
    "angry": (
        "angry",
        "mad",
        "furious",
        "annoyed",
        "frustrated",
        "irritated",
        "pissed",
        "hate this",
        "tired of this",
        "this is stupid",
        "why is this not working",
    ),
    "sad": (
        "sad",
        "heartbroken",
        "discouraged",
        "hopeless",
        "worthless",
        "empty",
        "crying",
        "hurt",
        "grief",
        "grieving",
    ),
    "lonely": (
        "lonely",
        "alone",
        "isolated",
        "no one",
        "nobody cares",
        "left out",
        "miss having someone",
    ),
    "stressed": (
        "stressed",
        "stressful",
        "stress",
        "under pressure",
        "pressure",
        "tense",
        "drained",
        "exhausted",
    ),
    "confused": (
        "confused",
        "lost",
        "unclear",
        "don't understand",
        "dont understand",
        "not sure",
        "i don't know",
        "i dont know",
        "unsure",
        "can't figure",
        "cant figure",
    ),
    "hopeful": (
        "hopeful",
        "hope things",
        "things will get better",
        "optimistic",
        "encouraged",
        "looking forward",
        "i can do this",
        "better soon",
    ),
    "calm": (
        "calm",
        "peaceful",
        "steady",
        "relieved",
        "okay now",
        "settled",
        "centered",
    ),
}


def _normalize_message(message: str) -> str:
    normalized = re.sub(r"[^a-z0-9']+", " ", message.lower())
    return " ".join(normalized.split())


def _contains_phrase(normalized_message: str, phrase: str) -> bool:
    normalized_phrase = _normalize_message(phrase)
    pattern = rf"(?<!\w){re.escape(normalized_phrase)}(?!\w)"
    return re.search(pattern, normalized_message) is not None


def detect_emotion(message: str) -> str:
    """
    Return a simple, non-clinical emotional context label.

    This intentionally uses deterministic phrase matching. It does not diagnose
    the user or infer anything beyond the words present in the message.
    """
    normalized = _normalize_message(message)

    if not normalized:
        return NEUTRAL_EMOTION

    for emotion, keywords in EMOTION_KEYWORDS.items():
        if any(_contains_phrase(normalized, keyword) for keyword in keywords):
            return emotion

    return NEUTRAL_EMOTION
