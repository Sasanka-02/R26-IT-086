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

Each student practises on a ladder made for their age group (Beginner, Intermediate, Advanced): \
children (6–13) get picture words, short phrases and a tiny story; teens (14–20) school readings, \
class presentations and role-plays; adults (21+) news readings, everyday role-plays, job \
interviews and work presentations. Other exercises: picture description, pacing, and delayed \
auditory feedback (DAF) for teens and adults."""

# How to talk to each age group (added to the system prompt).
STYLE = {
    "child": "The student is a child aged 6–13. Use very short, simple sentences (under 40 words), "
             "a cheerful tone and one emoji. Never use technical words.",
    "teen": "The student is a teenager aged 14–20. Be friendly and encouraging, casual but not childish.",
    "adult": "The student is an adult. Be respectful, calm and professional.",
}

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


def ask(question: str, first_name: str, context: dict, age_group: str = "adult") -> str | None:
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
            system=SYSTEM_PROMPT + "\n\n" + STYLE.get(age_group, STYLE["adult"]),
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
