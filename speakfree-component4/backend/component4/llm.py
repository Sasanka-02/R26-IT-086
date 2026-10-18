"""
Optional language-model fallback for the Therapy Assistant (Claude).

Used only when the offline intent classifier is not confident. Switched on by setting
ANTHROPIC_API_KEY (or another Anthropic credential); without it the assistant runs fully
offline. Server-side refusal fallbacks are enabled (`fallbacks: "default"`).

Privacy: the model receives only the patient's first name, their age group (bracket), their
therapy focus (the friendly name - never a diagnosis) and a small summary of their own practice
numbers. Never audio, e-mail addresses, screening reports or other patients' data.

Tone follows the age bracket (brackets.py "tone"): playful (6-9), simple (10-13),
friendly (14-20), respectful (21+).
"""
from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

MODEL = "claude-opus-5-5"

SYSTEM_TEMPLATE = """You are the practice assistant inside SpeakFree, a speech-therapy practice app. \
You talk to one person about their own practice.

Their practice focus is "{focus_name}": {tagline}
Techniques for this focus: {techniques}

Use only the practice data provided in the user's message. Do not invent scores, dates or exercises. \
Keep replies under {max_words} words. They are in the "{age_label}" age group, so {tone_instruction} \
They may feel anxious about speaking. You are not a clinician: never diagnose or name a disorder, and \
suggest talking to their speech therapist for medical or clinical questions. If the question is \
unrelated to speech practice, say briefly what you can help with instead."""

TONE_INSTRUCTIONS = {
    "playful": "use very short, cheerful sentences a young child understands, with one or two friendly emoji.",
    "simple": "use simple words and short sentences, and be warm and encouraging.",
    "friendly": "be friendly and motivating, like a supportive coach - no baby talk.",
    "respectful": "be respectful and professional, as with an adult client - no emoji.",
}
MAX_WORDS = {"playful": 40, "simple": 80}

try:
    import anthropic
except ImportError:  # optional dependency
    anthropic = None

_client = None


def is_enabled() -> bool:
    return anthropic is not None and bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(timeout=30.0)
    return _client


def system_prompt(focus: dict, context: dict, tone: str = "respectful") -> str:
    return SYSTEM_TEMPLATE.format(focus_name=focus["patient_name"], tagline=focus["tagline"],
                                  techniques="; ".join(focus["techniques"]),
                                  age_label=context.get("age_group") or "adult",
                                  tone_instruction=TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["respectful"]),
                                  max_words=MAX_WORDS.get(tone, 120))


def ask(question: str, first_name: str, focus: dict, context: dict, tone: str = "respectful") -> str | None:
    """Returns the model's reply, or None if unavailable, refused or failed."""
    if not is_enabled():
        return None
    system = system_prompt(focus, context, tone)
    content = (f"First name: {first_name}\nTheir practice data:\n{json.dumps(context, indent=1)}\n\n"
               f"Their question: {question}")
    try:
        response = _get_client().beta.messages.create(
            model=MODEL,
            max_tokens=2000,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=system,
            messages=[{"role": "user", "content": content}],
        )
    except anthropic.RateLimitError:
        logger.warning("Assistant LLM rate limited; using offline answer")
        return None
    except anthropic.APIStatusError as e:
        logger.warning("Assistant LLM error %s; using offline answer", e.status_code)
        return None
    except anthropic.APIConnectionError:
        logger.warning("Assistant LLM unreachable; using offline answer")
        return None

    if response.stop_reason == "refusal":
        return None
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    return text or None
