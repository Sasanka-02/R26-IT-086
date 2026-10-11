import { useEffect, useRef, useState } from "react";
import { TherapyExercise, SessionSummary } from "../types/therapy";
import { useLiveFeedback } from "./useLiveFeedback";
import { endTherapySession } from "./therapyApi";
import CompletionPanel from "./CompletionPanel";
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
  const [attemptId] = useState(() => `${sessionId}-${exercise.id}-${Date.now()}`);
  const { isActive, feedback, permissionError, start, stop } = useLiveFeedback(
    attemptId,
    "pacing"
  );
  const words = (exercise.passage ?? "").split(/\s+/).filter(Boolean);
  const [highlightIndex, setHighlightIndex] = useState(0);
  const [hasStopped, setHasStopped] = useState(false);
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [warmingUp, setWarmingUp] = useState(false);
  const startedAtRef = useRef(0);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!isActive) {
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
  }, [isActive, exercise.target_wpm, words.length]);

  const handleStart = () => {
    startedAtRef.current = Date.now();
    start();
  };

  const handleStop = async () => {
    stop();
    setHasStopped(true);
    const elapsed = (Date.now() - startedAtRef.current) / 1000;
    try {
      const s = await endTherapySession(attemptId);
      setSummary({ ...s, duration_seconds: s.duration_seconds || elapsed });
    } catch {
      setSummary({
        session_id: attemptId,
        duration_seconds: elapsed,
        speaking_ratio: 0,
        pause_count: 0,
        quiet_warnings: 0,
        syllables: 0,
      });
    }
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
              i === highlightIndex && isActive
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

      {feedback && !hasStopped && (
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

      {summary && (
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
        Privacy: only pacing/volume numbers are sent from your device — your
        voice recording never leaves the browser during this exercise.
      </p>
    </div>
  );
}
