import { useCallback, useRef, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { TherapyExercise } from "../types/therapy";
import { usePracticeHistory } from "../context/PracticeHistoryContext";

interface DafExerciseProps {
  exercise: TherapyExercise;
  initialDelayMs?: number;
}

export default function DafExercise({ exercise, initialDelayMs = 150 }: DafExerciseProps) {
  const { recordCompletion } = usePracticeHistory();
  const [isActive, setIsActive] = useState(false);
  const [delayMs, setDelayMs] = useState(initialDelayMs);
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const [hasStopped, setHasStopped] = useState(false);
  const [markedDone, setMarkedDone] = useState(false);

  const audioContextRef = useRef<AudioContext | null>(null);
  const delayNodeRef = useRef<DelayNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      audioContextRef.current.close();
    }
    audioContextRef.current = null;
    delayNodeRef.current = null;
    setIsActive(false);
    setHasStopped(true);
  }, []);

  const start = useCallback(async () => {
    setPermissionError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(stream);
      const delayNode = audioContext.createDelay(2.0);
      delayNode.delayTime.value = delayMs / 1000;

      source.connect(delayNode);
      delayNode.connect(audioContext.destination);

      audioContextRef.current = audioContext;
      delayNodeRef.current = delayNode;
      setIsActive(true);
    } catch (err) {
      setPermissionError(err instanceof Error ? err.message : "Microphone access failed.");
    }
  }, [delayMs]);

  const handleDelayChange = (value: number) => {
    setDelayMs(value);
    if (delayNodeRef.current) {
      delayNodeRef.current.delayTime.value = value / 1000;
    }
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

      <div className="rounded-xl border border-teal-100 bg-paper p-6">
        <label className="text-sm font-medium text-ink">Delay: {delayMs}ms</label>
        <input
          type="range"
          min={50}
          max={300}
          step={10}
          value={delayMs}
          onChange={(e) => handleDelayChange(Number(e.target.value))}
          className="mt-2 w-full accent-teal-600"
        />
        <p className="mt-3 text-xs text-ink-soft">
          Use headphones for best results, to avoid feedback echo through open
          speakers.
        </p>
      </div>

      {permissionError && <p className="text-sm text-red-600">{permissionError}</p>}

      {!hasStopped && (
        <div className="flex gap-3">
          {!isActive ? (
            <button
              onClick={start}
              className="rounded-full bg-teal-600 px-5 py-2 text-sm font-medium text-white hover:bg-teal-700"
            >
              Start Speaking
            </button>
          ) : (
            <button
              onClick={stop}
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
        Privacy: this exercise runs entirely in your browser — no audio or
        data is sent to any server.
      </p>
    </div>
  );
}