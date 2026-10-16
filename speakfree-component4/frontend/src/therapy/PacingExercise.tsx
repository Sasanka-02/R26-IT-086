import { useEffect, useRef, useState } from "react";
import { TherapyExercise, SessionSummary } from "../types/therapy";
import { useLiveFeedback } from "./useLiveFeedback";
import { endTherapySession } from "./therapyApi";
import CompletionPanel from "./CompletionPanel";
import RecordingPlayer from "../components/RecordingPlayer";
import BreathingWarmup from "./BreathingWarmup";

interface PacingExerciseProps {
  sessionId: string;
  exercise: TherapyExercise;
}

const FEEDBACK_STYLES: Record<string, string> = {
  success: "bg-teal-50 border-teal-200 text-teal-800",
  warning: "bg-gold-400/10 border-gold-500/40 text-gold-600",
  info: "bg-teal-50 border-teal-100 text-ink-soft",
};

const LEVEL_BADGES: Record<string, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced · Final stage",
};

/** Used for both pacing and graded reading — both follow a highlighted passage. */
export default function PacingExercise({ sessionId, exercise }: PacingExerciseProps) {
  // A separate live session per attempt, so its summary covers only this exercise.
  const newAttemptId = () => `${sessionId}-${exercise.id}-${Date.now()}`;
  const [attemptId, setAttemptId] = useState(newAttemptId);
  const { isActive, calibrating, feedback, permissionError, recordingUrl, heardNothing, start, stop } = useLiveFeedback(
    attemptId,
    "pacing"
  );
  const [micSilent, setMicSilent] = useState(false);
  const words = (exercise.passage ?? "").split(/\s+/).filter(Boolean);
  const [highlightIndex, setHighlightIndex] = useState(0);
  const [hasStopped, setHasStopped] = useState(false);
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [warmingUp, setWarmingUp] = useState(false);
  const startedAtRef = useRef(0);
  const timerRef = useRef<number | null>(null);

  // The highlight starts once the room's background noise has been measured.
  const reading = isActive && !calibrating;
  useEffect(() => {
    if (!reading) {
      if (timerRef.current) window.clearInterval(timerRef.current);
      setHighlightIndex(0);
      return;
    }
    const wpm = exercise.target_wpm ?? 110;
    const msPerWord = 60000 / wpm;
    timerRef.current = window.setInterval(() => {
      setHighlightIndex((i) => (i + 1 < words.length ? i + 1 : i));
    }, msPerWord);
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, [reading, exercise.target_wpm, words.length]);

  const handleStart = () => {
    startedAtRef.current = Date.now();
    start();
  };

  const handleStop = async () => {
    const silent = heardNothing();
    stop();
    setHasStopped(true);
    setMicSilent(silent);
    const elapsed = (Date.now() - startedAtRef.current) / 1000;
    try {
      const s = await endTherapySession(attemptId);
      setSummary({ ...s, duration_seconds: s.duration_seconds || elapsed });
    } catch {
      // No live measurements reached the server: save time and rating only,
      // rather than scoring the attempt as if the student had been silent.
      setSummary({
        session_id: attemptId,
        duration_seconds: elapsed,
        speaking_ratio: null,
        pause_count: 0,
        quiet_warnings: 0,
        syllables: 0,
      });
    }
  };

  const tryAgain = () => {
    setAttemptId(newAttemptId());
    setHasStopped(false);
    setSummary(null);
    setMicSilent(false);
  };

  return (
    <div className="space-y-4 rounded-2xl border border-teal-100 bg-white p-6">
      <div>
        {exercise.level && (
          <span className="mb-2 inline-flex rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-700">
            {LEVEL_BADGES[exercise.level]}
          </span>
        )}
        {exercise.assigned && (
          <span className="mb-2 ml-2 inline-flex rounded-full bg-gold-400/20 px-3 py-1 text-xs font-medium text-gold-600">
            Assigned by your therapist
          </span>
        )}
        <h2 className="font-display text-lg font-semibold text-ink">{exercise.title}</h2>
        <p className="text-sm text-ink-soft">{exercise.description}</p>
        {exercise.target_wpm && (
          <p className="mt-1 text-xs text-ink-soft">
            Highlight speed: <strong className="text-ink">{exercise.target_wpm} words/min</strong>
            {exercise.base_wpm && exercise.base_wpm !== exercise.target_wpm
              ? ` — adapted for you from ${exercise.base_wpm} based on your earlier attempts`
              : ""}
          </p>
        )}
      </div>

      {warmingUp && (
        <BreathingWarmup
          onDone={() => {
            setWarmingUp(false);
            handleStart();
          }}
        />
      )}

      <div className="rounded-xl border border-teal-100 bg-paper p-6 text-lg leading-relaxed">
        {words.map((word, i) => (
          <span
            key={i}
            className={
              i === highlightIndex && reading
                ? "rounded bg-gold-400/30 px-1 text-ink"
                : i < highlightIndex
                ? "text-ink-soft/50"
                : "text-ink"
            }
          >
            {word}{" "}
          </span>
        ))}
      </div>

      {isActive && calibrating && (
        <div className="rounded-lg border border-teal-200 bg-teal-50 px-4 py-2 text-sm font-medium text-teal-800" role="status">
          Get ready — stay quiet for a moment while we listen to the room…
        </div>
      )}

      {feedback && !hasStopped && !calibrating && (
        <div
          className={`rounded-lg border px-4 py-2 text-sm ${
            FEEDBACK_STYLES[feedback.severity] ?? FEEDBACK_STYLES.info
          }`}
        >
          {feedback.message}
        </div>
      )}

      {permissionError && <p className="text-sm text-red-600">{permissionError}</p>}

      {!hasStopped && !warmingUp && (
        <div className="flex flex-wrap gap-3">
          {!isActive ? (
            <>
              <button
                onClick={handleStart}
                className="rounded-full bg-teal-600 px-5 py-2 text-sm font-medium text-white hover:bg-teal-700"
              >
                Start Exercise
              </button>
              <button
                onClick={() => setWarmingUp(true)}
                className="rounded-full border border-teal-200 px-5 py-2 text-sm font-medium text-teal-700 hover:bg-teal-50"
              >
                Warm up first (36 s)
              </button>
            </>
          ) : (
            <button
              onClick={handleStop}
              className="rounded-full bg-red-600 px-5 py-2 text-sm font-medium text-white hover:bg-red-700"
            >
              Stop
            </button>
          )}
        </div>
      )}

      {hasStopped && !summary && <p className="text-sm text-ink-soft">Working out your result...</p>}

      {recordingUrl && hasStopped && (
        <RecordingPlayer src={recordingUrl} label="Listen to your reading" />
      )}

      {summary && micSilent && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-ink" role="alert">
          <p className="font-medium">We didn't hear you reading, so this attempt hasn't been scored.</p>
          <p className="mt-1 text-ink-soft">
            A score needs at least 2 seconds of your voice. Read the passage aloud after the “Get ready” message.
            If you did read, check that the browser is using the right microphone (the mic icon in the address bar)
            — play the recording above to hear what was picked up.
          </p>
          <button
            onClick={tryAgain}
            className="mt-3 rounded-full bg-teal-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-teal-700"
          >
            Try again
          </button>
        </div>
      )}

      {summary && !micSilent && (
        <CompletionPanel
          metrics={{
            exercise_id: exercise.id,
            duration_seconds: summary.duration_seconds,
            speaking_ratio: summary.speaking_ratio,
            long_pauses: summary.pause_count,
            quiet_warnings: summary.quiet_warnings,
            syllables: summary.syllables,
            target_wpm: exercise.target_wpm,
          }}
        />
      )}

      <p className="text-xs text-ink-soft">
        Privacy: only pacing/volume numbers are sent from your device. The
        recording stays in this page for you to listen back — it is never uploaded.
      </p>
    </div>
  );
}
