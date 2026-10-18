"""Pydantic models of the Component 4 API (used by the platform's therapy routes)."""
from typing import Literal

from pydantic import BaseModel, Field

SelfRating = Literal["easy", "ok", "hard"]
TaskType = Literal["reading", "picture", "conversation"]  # the three age-bracket task types


class BracketExercise(BaseModel):
    """One of the 24 age-bracket exercises (bracket_tasks.py)."""
    id: str
    bracket: int = Field(ge=1, le=8)
    task_type: TaskType
    title: str
    description: str
    passage: str | None = None          # reading
    target_wpm: int | None = None       # reading: rises with the bracket (70 -> 150)
    image_url: str | None = None        # picture
    situation: str | None = None        # conversation
    prompts: list[str] = []             # picture + conversation guiding questions


class LiveMetric(BaseModel):
    """On-device metrics streamed every 500 ms during a live exercise (never raw audio)."""
    timestamp_ms: float
    rms_energy: float
    zero_crossing_rate: float
    is_speaking: bool
    syllables: int = 0  # syllable-like energy peaks detected in the browser this interval


class FeedbackMessage(BaseModel):
    type: str
    message: str
    severity: str = "info"


class AttemptRequest(BaseModel):
    """Result of one therapy exercise, computed in the browser."""
    exercise_id: str
    live_session_id: str | None = None   # summary of the live WebSocket session, if one was used
    duration_seconds: float = Field(default=0, ge=0, le=3600)
    speaking_ratio: float | None = Field(default=None, ge=0, le=1)
    long_pauses: int = Field(default=0, ge=0)
    quiet_warnings: int = Field(default=0, ge=0)
    syllables: int | None = Field(default=None, ge=0)
    target_wpm: int | None = None
    max_phonation_sec: float | None = Field(default=None, ge=0)
    items_total: int | None = Field(default=None, ge=0)     # sound drills: words practised
    items_clear: int | None = Field(default=None, ge=0)     # sound drills: words the user marked "clear"
    self_rating: SelfRating = "ok"


class ChatRequest(BaseModel):
    message: str = Field(max_length=500)
