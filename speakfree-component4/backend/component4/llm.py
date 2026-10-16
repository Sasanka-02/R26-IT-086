"""
Optional language-model fallback for the Therapy Assistant (Claude).

Used only when the offline intent classifier is not confident. Switched on by setting
ANTHROPIC_API_KEY (or another Anthropic credential); without it the assistant runs fully
offline. Server-side refusal fallbacks are enabled (`fallbacks: "default"`).

Privacy: the model receives only the patient's first name, their therapy focus (the friendly
name - never a diagnosis) and a small summary of their own practice numbers. Never audio,
e-mail addresses, screening reports or other patients' data.
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
Keep replies under 120 words, warm and plain-spoken, suitable for someone (often a child or teenager) \
who may feel anxious about speaking. You are not a clinician: never diagnose or name a disorder, and \
suggest talking to their speech therapist for medical or clinical questions. If the question is \
unrelated to speech practice, say briefly what you can help with instead."""

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


def ask(question: str, first_name: str, focus: dict, context: dict) -> str | None:
    """Returns the model's reply, or None if unavailable, refused or failed."""
    if not is_enabled():
        return None
    system = SYSTEM_TEMPLATE.format(focus_name=focus["patient_name"], tagline=focus["tagline"],
                                    techniques="; ".join(focus["techniques"]))
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
