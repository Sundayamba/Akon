import re


STUDY_MODE_SIGNALS = {
    "study",
    "learn",
    "teach",
    "explain",
    "understand",
    "revise",
    "revision",
    "quiz",
    "test me",
    "practice",
    "remember",
    "retain",
    "retention",
    "won't forget",
    "wont forget",
    "do not forget",
    "don't forget",
}


def normalize_study_message(message: str) -> str:
    return " ".join(message.lower().strip().split())


def is_study_retention_request(message: str) -> bool:
    normalized = normalize_study_message(message)

    if any(signal in normalized for signal in STUDY_MODE_SIGNALS):
        return any(
            retention_signal in normalized
            for retention_signal in {
                "study",
                "learn",
                "teach",
                "explain",
                "quiz",
                "test me",
                "practice",
                "revise",
                "revision",
                "remember",
                "retain",
                "retention",
                "won't forget",
                "wont forget",
                "do not forget",
                "don't forget",
            }
        )

    return False


def extract_study_topic(message: str) -> str:
    cleaned = " ".join(message.strip().split())

    patterns = [
        r"\bteach me\b",
        r"\bexplain\b",
        r"\bhelp me study\b",
        r"\bhelp me learn\b",
        r"\bhelp me understand\b",
        r"\bquiz me on\b",
        r"\btest me on\b",
        r"\brevise\b",
        r"\bstudy\b",
        r"\blearn\b",
    ]

    topic = cleaned

    for pattern in patterns:
        topic = re.sub(pattern, "", topic, count=1, flags=re.IGNORECASE).strip(" .,:;-")
        if topic != cleaned:
            break

    topic = re.sub(
        r"\b(so i won'?t forget it|so i do not forget it|so i can remember it|and quiz me|quiz me|test me)\b",
        "",
        topic,
        flags=re.IGNORECASE,
    ).strip(" .,:;-")

    topic = re.sub(
        r"^(on|about)\s+",
        "",
        topic,
        count=1,
        flags=re.IGNORECASE,
    ).strip(" .,:;-")

    if not topic:
        return "the topic you want to study"

    return topic


def build_study_retention_reply(message: str) -> str:
    topic = extract_study_topic(message)

    return (
        "Study Retention Mode\n\n"
        f"Topic: {topic}\n\n"
        "1. Understand it\n"
        "Tell me the exact material, note, or concept, and I will explain it in simple layers: "
        "meaning, why it matters, how it works, and a practical example.\n\n"
        "2. Compress it\n"
        "I will turn the explanation into a short memory version you can revise quickly.\n\n"
        "3. Recall it\n"
        "After the explanation, I will ask you to explain it back in your own words so we can test "
        "whether you truly understand it.\n\n"
        "4. Quiz it\n"
        "I will give you a mix of multiple-choice and theory questions, then correct your answers.\n\n"
        "5. Save the key point\n"
        "When the summary is strong, I can suggest a study-note memory for you to approve before saving.\n\n"
        "Send the topic or paste your note now, and I will start with the first clear explanation."
    )