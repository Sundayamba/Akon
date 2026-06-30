import re


NEUTRAL_EMOTION = "neutral"

SUPPORTED_EMOTIONS = {
    "calm",
    "stressed",
    "sad",
    "anxious",
    "angry",
    "overwhelmed",
    "lonely",
    "confused",
    "hopeful",
    "neutral",
}

EMOTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "overwhelmed": (
        "overwhelmed",
        "too much",
        "too many things",
        "can't handle",
        "cant handle",
        "cannot handle",
        "everything at once",
        "everything is falling apart",
        "drowning in",
        "spread too thin",
        "burned out",
        "burnt out",
        "i am drowning",
        "i feel buried",
        "buried under",
        "i can't cope",
        "i cant cope",
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
        "restless",
        "uneasy",
        "can't stop thinking",
        "cant stop thinking",
        "my mind is racing",
        "what if",
        "i keep thinking",
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
        "this is unfair",
        "not fair",
        "i am fed up",
        "im fed up",
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
        "down",
        "low",
        "broken",
        "painful",
        "it hurts",
    ),
    "lonely": (
        "lonely",
        "alone",
        "isolated",
        "no one",
        "nobody cares",
        "left out",
        "miss having someone",
        "no one understands",
        "nobody understands",
        "by myself",
        "feel unseen",
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
        "tired",
        "worn out",
        "too much work",
        "deadline",
        "deadlines",
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
        "mixed up",
        "stuck",
        "what should i do",
        "what do i do",
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
        "i feel ready",
        "i am ready",
        "i believe",
        "there is a chance",
    ),
    "calm": (
        "calm",
        "peaceful",
        "steady",
        "relieved",
        "okay now",
        "settled",
        "centered",
        "clear headed",
        "clear-headed",
        "balanced",
        "at peace",
    ),
}


def _normalize_message(message: str) -> str:
    normalized = re.sub(r"[^a-z0-9']+", " ", message.lower())
    return " ".join(normalized.split())


def _contains_phrase(normalized_message: str, phrase: str) -> bool:
    normalized_phrase = _normalize_message(phrase)
    pattern = rf"(?<!\w){re.escape(normalized_phrase)}(?!\w)"
    return re.search(pattern, normalized_message) is not None


def normalize_emotion_label(emotion: str | None) -> str:
    if not emotion:
        return NEUTRAL_EMOTION

    normalized = emotion.strip().lower()
    return normalized if normalized in SUPPORTED_EMOTIONS else NEUTRAL_EMOTION


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