SUPPORTIVE_SAFETY_LEVELS = {"S0", "S1", "S2"}

EMOTION_STRATEGIES: dict[str, dict[str, str]] = {
    "overwhelmed": {
        "validation": "That sounds like a lot to hold, and it makes sense that you would feel overwhelmed.",
        "reflection": "From what you shared, Akon senses this may be stress or overwhelm.",
        "step": "One small step for now: write down the one thing that needs your attention first.",
    },
    "stressed": {
        "validation": "That sounds heavy, and it makes sense that your system would feel strained.",
        "reflection": "From what you shared, Akon senses this may be stress asking for a little order.",
        "step": "One small step for now: name the next task that would lower the pressure even slightly.",
    },
    "sad": {
        "validation": "That sounds tender and painful, and you do not have to rush past it.",
        "reflection": "From what you shared, Akon senses sadness may be close to the surface.",
        "step": "One small step for now: tell me what part of this hurts the most.",
    },
    "anxious": {
        "validation": "That sounds unsettling, and it makes sense that your mind is trying to scan for what could go wrong.",
        "reflection": "From what you shared, Akon senses this may be anxiety or worry.",
        "step": "One small step for now: write down what is known, what is unknown, and what can wait.",
    },
    "angry": {
        "validation": "That sounds frustrating, and it makes sense that there is heat around it.",
        "reflection": "From what you shared, Akon senses anger may be pointing at something that feels unfair or blocked.",
        "step": "One small step for now: name what boundary, need, or expectation was crossed.",
    },
    "lonely": {
        "validation": "That sounds lonely, and it makes sense that you would want to feel met instead of carrying it alone.",
        "reflection": "From what you shared, Akon senses loneliness may be part of this moment.",
        "step": "One small step for now: think of one safe person or place that could give you a little connection today.",
    },
    "confused": {
        "validation": "That sounds unclear, and it makes sense that choosing a next step feels harder right now.",
        "reflection": "From what you shared, Akon senses confusion, not failure.",
        "step": "One small step for now: list the options in front of you and circle the one that matters most today.",
    },
    "hopeful": {
        "validation": "That sounds hopeful, and it is worth noticing that part of you can still see a way forward.",
        "reflection": "From what you shared, Akon senses some cautious optimism.",
        "step": "One small step for now: choose one action that protects that hope without demanding everything from you.",
    },
    "calm": {
        "validation": "That sounds steady, and it is okay to let the calm be simple.",
        "reflection": "From what you shared, Akon senses a calmer place to make the next choice from.",
        "step": "One small step for now: decide what would help you keep this steadiness for the next hour.",
    },
    "neutral": {
        "validation": "I am here with you, and we can take this one piece at a time.",
        "reflection": "From what you shared, Akon does not need to force a feeling label onto it.",
        "step": "One small step for now: tell me what would be most useful to sort out first.",
    },
}

GROUNDING_TOOLS: dict[str, dict[str, str]] = {
    "overwhelmed": {
        "name": "One-thing anchor",
        "instruction": "Pause for ten seconds, place both feet on the floor, and choose only one thing to handle next.",
    },
    "stressed": {
        "name": "Pressure drop",
        "instruction": "Unclench your jaw, lower your shoulders, breathe out slowly, then name the smallest useful next action.",
    },
    "anxious": {
        "name": "Known / unknown / next",
        "instruction": "Write three short lines: what I know, what I do not know yet, and the next safe thing I can do.",
    },
    "angry": {
        "name": "Heat to boundary",
        "instruction": "Take one slow breath before acting, then name the boundary, need, or value that feels crossed.",
    },
    "confused": {
        "name": "Three-option sort",
        "instruction": "List up to three options, cross out what is unrealistic today, and choose the smallest remaining step.",
    },
    "sad": {
        "name": "Gentle naming",
        "instruction": "Put one hand on your chest if that feels okay, breathe slowly, and name the hardest part in one sentence.",
    },
    "lonely": {
        "name": "Connection thread",
        "instruction": "Think of one safe person, place, or routine that could make you feel a little less alone today.",
    },
    "hopeful": {
        "name": "Protect the spark",
        "instruction": "Name one small action that supports this hope without putting too much pressure on yourself.",
    },
    "calm": {
        "name": "Steady hour",
        "instruction": "Notice what is helping you feel steady, then choose one simple thing that protects that calm for the next hour.",
    },
    "neutral": {
        "name": "Next useful thing",
        "instruction": "Take a slow breath and choose the one topic, task, or feeling that would be most useful to sort out first.",
    },
}


def normalize_emotion(detected_emotion: str | None) -> str:
    if not detected_emotion:
        return "neutral"

    emotion = detected_emotion.strip().lower()
    return emotion if emotion in EMOTION_STRATEGIES else "neutral"


def get_grounding_tool(detected_emotion: str | None) -> dict[str, str]:
    """
    Return a deterministic, non-clinical grounding tool for the detected emotion.

    These tools are not medical treatment or diagnosis. They are lightweight
    support prompts for ordinary stressful, confusing, or emotionally heavy moments.
    """
    emotion = normalize_emotion(detected_emotion)
    return GROUNDING_TOOLS.get(emotion, GROUNDING_TOOLS["neutral"])


def build_grounding_line(detected_emotion: str | None) -> str:
    tool = get_grounding_tool(detected_emotion)
    return f"Grounding tool — {tool['name']}: {tool['instruction']}"


def build_support_reply(
    user_message: str,
    detected_emotion: str | None,
    safety_level: str,
    memory_context: str | None = None,
) -> str:
    """
    Build Akon's deterministic non-clinical support reply.

    This is for ordinary supportive exchanges only. Higher-risk safety flows
    should keep using their dedicated safety responses.
    """
    if safety_level not in SUPPORTIVE_SAFETY_LEVELS:
        raise ValueError("Support strategy is only for normal supportive safety levels.")

    emotion = normalize_emotion(detected_emotion)
    strategy = EMOTION_STRATEGIES[emotion]

    closing = "I am here with you as we sort it out."

    if memory_context:
        closing = "I am also taking your saved context into account. " + closing

    return "\n\n".join(
        [
            strategy["validation"],
            strategy["reflection"],
            strategy["step"],
            closing,
        ]
    )