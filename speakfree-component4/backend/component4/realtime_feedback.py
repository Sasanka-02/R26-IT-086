"""
Simple rule-based real-time feedback engine. Operates only on the
lightweight numeric metrics the browser sends — never on raw audio.
"""

from .schemas import FeedbackMessage, LiveMetric
from .session_store import LiveSessionState

QUIET_THRESHOLD = 0.02
LONG_PAUSE_FRAMES = 6  # ~3 seconds at 500ms cadence
FRAME_SEC = 0.5


def process_metric(state: LiveSessionState, metric: LiveMetric) -> FeedbackMessage | None:
    state.energy_samples.append(metric.rms_energy)
    state.syllables += max(0, metric.syllables)
    state.speaking_flags.append(metric.is_speaking)

    if not metric.is_speaking:
        state._was_speaking = False
        state._voiced_run = 0
        state._silent_run += 1
        # one long pause per silence (counted when it reaches ~3 s, not again on every later silent frame),
        # and only after the learner has started speaking - getting ready at the start is not a pause
        if state._silent_run == LONG_PAUSE_FRAMES and state._has_spoken:
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
    state._has_spoken = True
    state._silent_run = 0
    state._voiced_run += 1
    state.max_voiced_run = max(state.max_voiced_run, state._voiced_run)

    if metric.rms_energy < QUIET_THRESHOLD:
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
    # no frames received (mic blocked, socket dropped) -> no measurement, not "silent the whole time"
    speaking_ratio = (
        sum(1 for f in state.speaking_flags if f) / len(state.speaking_flags)
        if state.speaking_flags
        else None
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
        "max_phonation_sec": round(state.max_voiced_run * FRAME_SEC, 1),
    }
