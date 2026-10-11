"""
Optional language-model fallback for the Therapy Assistant (Claude).

Used only when the offline intent classifier is not confident. It is
switched on by setting ANTHROPIC_API_KEY; without it the assistant runs
fully offline.

Privacy: the model receives only a small summary of the student's own
practice numbers (level, recent scores, goals, plan) and their first
name — never audio, email addresses or other students' data.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """You are the practice assistant inside SpeakFree, a speech-therapy practice app \
for people who stutter. You talk to one student about their own practice.

Use only the practice data provided in the user's message. Do not invent scores, dates or \
exercises. Keep replies under 120 words, warm and plain-spoken, suitable for someone who may \
feel anxious about speaking. You are not a clinician: do not diagnose, and suggest talking to \
their therapist for medical or clinical questions. If the question is unrelated to speech \
practice, say briefly what you can help with instead.

Exercises available: graded reading (Beginner, Intermediate, Advanced/final stage), \
picture description, gentle and standard pacing, delayed auditory feedback (DAF)."""

try:
    import anthropic
except ImportError:  # optional dependency
    anthropic = None

_client = None


def is_enabled() -> bool:
    return anthropic is not None and bool(os.environ.get("ANTHROPIC_API_KEY"))


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(timeout=30.0)
    return _client


def ask(question: str, first_name: str, context: dict) -> str | None:
    """Returns the model's reply, or None if unavailable or it fails."""
    if not is_enabled():
        return None
    content = (
        f"Student's first name: {first_name}\n"
        f"Their practice data:\n{json.dumps(context, indent=1)}\n\n"
        f"Their question: {question}"
    )
    try:
        response = _get_client().beta.messages.create(
            model=MODEL,
            max_tokens=2000,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEM_PROMPT,
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
