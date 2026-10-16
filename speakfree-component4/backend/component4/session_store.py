"""
In-memory, ephemeral session state for live therapy feedback.

Privacy design: nothing here is written to disk. No raw audio is ever
received by the backend for a live exercise — only aggregated numeric
metrics computed client-side. State is discarded when the session ends
or the process restarts; there is no persistence layer by design.
"""

import time
from dataclasses import dataclass, field

from typing import Optional


@dataclass
class LiveSessionState:
    session_id: str
    exercise_type: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    energy_samples: list[float] = field(default_factory=list)
    speaking_flags: list[bool] = field(default_factory=list)
    pause_count: int = 0
    feedback_events: int = 0
    quiet_warnings: int = 0
    syllables: int = 0
    _was_speaking: bool = False
    _voiced_run: int = 0
    max_voiced_run: int = 0  # longest continuous voicing, in 500 ms frames (sustained-vowel task)


_SESSIONS: dict[str, LiveSessionState] = {}


def start_session(session_id: str, exercise_type: Optional[str] = None) -> LiveSessionState:
    state = LiveSessionState(session_id=session_id, exercise_type=exercise_type)
    _SESSIONS[session_id] = state
    return state


def get_session(session_id: str) -> LiveSessionState | None:
    return _SESSIONS.get(session_id)


def end_session(session_id: str) -> LiveSessionState | None:
    return _SESSIONS.pop(session_id, None)
