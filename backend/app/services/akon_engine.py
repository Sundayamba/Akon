from typing import Any

from app.services.llm_provider import LLMProviderError, get_llm_provider


def _crisis_reply() -> str:
    return (
        "I’m really sorry you’re carrying this right now. "
        "Your safety matters more than solving everything in this moment. "
        "Are you in immediate danger, or have you already done anything that could harm you?\n\n"
        "If there is any immediate danger, please contact your local emergency service now "
        "or ask someone nearby to stay with you. If there is a trusted person close to you, "
        "send them this simple message: “I’m not safe alone right now. Please stay with me.”\n\n"
        "Stay with me for a moment. What country are you in right now so I can guide you toward "
        "the right kind of urgent support?"
    )


def _high_distress_reply() -> str:
    return (
        "That sounds heavy, and I don’t want to rush past it. "
        "Let’s slow it down. You do not need to solve everything at once.\n\n"
        "For the next minute, focus only on this: breathe slowly, sit somewhere safe, "
        "and name the one thing that feels most urgent right now. "
        "What is the biggest pressure on you at this moment?"
    )


def _fallback_reply(detected_emotion: str | None, memory_context: str | None = None) -> str:
    memory_note = ""

    if memory_context:
        memory_note = "\n\nI’m also taking your saved context into account."

    if detected_emotion == "frustration":
        return (
            "I hear the frustration. Let’s cut the noise and deal with the next useful step. "
            "Tell me exactly what failed, what you expected to happen, and what actually happened."
            f"{memory_note}"
        )

    if detected_emotion == "anxiety":
        return (
            "It sounds like your mind is carrying too much at once. "
            "Let’s slow it down and choose one small step. "
            "What is the one thing you need to handle first?"
            f"{memory_note}"
        )

    if detected_emotion == "sadness":
        return (
            "That sounds painful, and I won’t pretend it is small. "
            "But we can separate what hurts from what you can do next. "
            "What happened that made you feel this way?"
            f"{memory_note}"
        )

    if detected_emotion == "excitement":
        return (
            "Good. That energy is useful. Let’s turn it into execution before it fades. "
            "What exactly are we building, deciding, or doing next?"
            f"{memory_note}"
        )

    return (
        "I’m here with you. Tell me what is going on, and I’ll help you think through it "
        "clearly, step by step, without judgment and without rushing you."
        f"{memory_note}"
    )


def generate_akon_reply(
    message: str,
    safety_result: dict[str, Any],
    memory_context: str | None = None,
) -> str:
    """
    Generate Akon's reply.

    S4 and S3 safety flows are deterministic and controlled.
    Normal and low-risk emotional conversations may use the configured LLM provider.
    """
    safety_level = safety_result.get("level", "S0")
    detected_emotion = safety_result.get("detected_emotion")

    if safety_level == "S4":
        return _crisis_reply()

    if safety_level == "S3":
        return _high_distress_reply()

    try:
        provider = get_llm_provider()
        return provider.generate_reply(
            message=message,
            safety_level=safety_level,
            detected_emotion=detected_emotion,
            memory_context=memory_context,
        )
    except LLMProviderError:
        return _fallback_reply(
            detected_emotion=detected_emotion,
            memory_context=memory_context,
        )