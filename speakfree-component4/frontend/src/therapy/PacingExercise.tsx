import { useEffect, useRef, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { TherapyExercise } from "../types/therapy";
import { useLiveFeedback } from "./useLiveFeedback";
import { usePracticeHistory } from "../context/PracticeHistoryContext";

interface PacingExerciseProps {
  sessionId: string;
  exercise: TherapyExercise;
}

const FEEDBACK_STYLES: Record<string, string> = {
  success: "bg-teal-50 border-teal-200 text-teal-800",
  warning: "bg-gold-400/10 border-gold-500/40 text-gold-600",
  info: "bg-teal-50 border-teal-100 text-ink-soft",
};

export default function PacingExercise({ sessionId, exercise }: PacingExerciseProps) {
  const { isActive, feedback, permissionError, start, stop } = useLiveFeedback(
    sessionId,
    "pacing"
  );
  const { recordCompletion } = usePracticeHistory();
  const words = (exercise.passage ?? "").split(/\s+/).filter(Boolean);
  const [highlightIndex, setHighlightIndex] = useState(0);
  const [hasStopped, setHasStopped] = useState(false);
  const [markedDone, setMarkedDone] = useState(false);
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

  const handleStop = () => {
    stop();
    setHasStopped(true);
  };

  const handleMarkDone = () => {
    recordCompletion(exercise);
    setMarkedDone(true);
  };

  return (
    <div className="space-y-4 rounded-2xl border border-teal-100 bg-white p-6">
      <div>
        <h2 className="font-display text-lg font-semibold text-ink">{exercise.title}</h2>
        <p className="text-sm text-ink-soft">{exercise.description}</p>
      </div>

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

      {feedback && (
        <div
          className={`rounded-lg border px-4 py-2 text-sm ${
            FEEDBACK_STYLES[feedback.severity] ?? FEEDBACK_STYLES.info
          }`}
        >
          {feedback.message}
        </div>
      )}

      {permissionError && <p className="text-sm text-red-600">{permissionError}</p>}

      {!hasStopped && (
        <div className="flex gap-3">
          {!isActive ? (
            <button
              onClick={start}
              className="rounded-full bg-teal-600 px-5 py-2 text-sm font-medium text-white hover:bg-teal-700"
            >
              Start Exercise
            </button>
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

      {hasStopped && !markedDone && (
        <button
          onClick={handleMarkDone}
          className="flex items-center gap-2 rounded-full bg-teal-600 px-5 py-2 text-sm font-medium text-white hover:bg-teal-700"
        >
          <CheckCircle2 size={16} />
          Mark Complete
        </button>
      )}

      {markedDone && (
        <div className="flex items-center gap-2 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-800">
          <CheckCircle2 size={18} />
          Nice work — this exercise is complete.
        </div>
      )}

      <p className="text-xs text-ink-soft">
        Privacy: only pacing/volume numbers are sent from your device — your
        voice recording never leaves the browser during this exercise.
      </p>
    </div>
  );
}