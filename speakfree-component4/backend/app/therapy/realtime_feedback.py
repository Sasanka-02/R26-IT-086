"""
Simple rule-based real-time feedback engine. Operates only on the
lightweight numeric metrics the browser sends — never on raw audio.
"""

from app.therapy.schemas import FeedbackMessage, LiveMetric
from app.therapy.session_store import LiveSessionState

QUIET_THRESHOLD = 0.015  # mean loudness of the voiced part of a 500 ms frame
LONG_PAUSE_FRAMES = 6  # ~3 seconds at 500ms cadence
QUIET_FRAMES = 2  # ~1 second of quiet speech before warning


def process_metric(state: LiveSessionState, metric: LiveMetric) -> FeedbackMessage | None:
    state.energy_samples.append(metric.rms_energy)
    state.syllables += max(0, metric.syllables)
    state.speaking_flags.append(metric.is_speaking)

    if not metric.is_speaking:
        state._was_speaking = False
        state._quiet_frames = 0
        recent = state.speaking_flags[-LONG_PAUSE_FRAMES:]
        # One silence counts as one long pause, however long it lasts.
        if len(recent) == LONG_PAUSE_FRAMES and not any(recent) and not state._in_long_pause:
            state._in_long_pause = True
            state.pause_count += 1
            state.feedback_events += 1
            return FeedbackMessage(
                type="long_pause",
                message="Take your time — no rush. Continue whenever you're ready.",
                severity="info",
            )
        return None

    just_started = not state._was_speaking
    state._was_speaking = True
    state._in_long_pause = False

    # One warning per stretch of quiet speech, not one per frame.
    state._quiet_frames = state._quiet_frames + 1 if metric.rms_energy < QUIET_THRESHOLD else 0
    if state._quiet_frames == QUIET_FRAMES:
        state.feedback_events += 1
        state.quiet_warnings += 1
        return FeedbackMessage(
            type="too_quiet",
            message="Try speaking a little louder — the mic is picking up very little sound.",
            severity="warning",
        )

    if just_started:
        state.feedback_events += 1
        return FeedbackMessage(
            type="good_pace",
            message="Nice and steady — keep going.",
            severity="success",
        )

    return None


def summarize(state: LiveSessionState) -> dict:
    import time as _time

    duration = _time.time() - state.started_at
    speaking_ratio = (
        sum(1 for f in state.speaking_flags if f) / len(state.speaking_flags)
        if state.speaking_flags
        else 0.0
    )
    avg_energy = (
        sum(state.energy_samples) / len(state.energy_samples)
        if state.energy_samples
        else 0.0
    )

    return {
        "duration_seconds": duration,
        "exercise_type": state.exercise_type,
        "speaking_ratio": speaking_ratio,
        "avg_energy": avg_energy,
        "pause_count": state.pause_count,
        "feedback_events": state.feedback_events,
        "quiet_warnings": state.quiet_warnings,
        "syllables": state.syllables,
    }
