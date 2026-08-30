import { Mic, Square, RotateCcw, Pause, Play } from "lucide-react";

interface RecorderControlsProps {
  isRecording: boolean;
  isPaused: boolean;
  hasRecording: boolean;
  disabled?: boolean;
  onStart: () => void;
  onStop: () => void;
  onPause: () => void;
  onResume: () => void;
  onReset: () => void;
}

/**
 * Zero-time-pressure controls: no countdowns, no auto-stop. The user is
 * always the one who decides when to start and stop.
 */
export default function RecorderControls({
  isRecording,
  isPaused,
  hasRecording,
  disabled = false,
  onStart,
  onStop,
  onPause,
  onResume,
  onReset,
}: RecorderControlsProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {!isRecording && !hasRecording && (
        <button
          type="button"
          onClick={onStart}
          disabled={disabled}
          className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-white font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Mic size={18} />
          Start Recording
        </button>
      )}

      {isRecording && !isPaused && (
        <>
          <button
            type="button"
            onClick={onPause}
            className="flex items-center gap-2 rounded-lg bg-slate-200 px-4 py-2 text-slate-800 font-medium hover:bg-slate-300"
          >
            <Pause size={18} />
            Pause
          </button>
          <button
            type="button"
            onClick={onStop}
            className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-white font-medium hover:bg-red-700"
          >
            <Square size={18} />
            Stop &amp; Submit
          </button>
        </>
      )}

      {isRecording && isPaused && (
        <>
          <button
            type="button"
            onClick={onResume}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-white font-medium hover:bg-brand-700"
          >
            <Play size={18} />
            Resume
          </button>
          <button
            type="button"
            onClick={onStop}
            className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-white font-medium hover:bg-red-700"
          >
            <Square size={18} />
            Stop &amp; Submit
          </button>
        </>
      )}

      {!isRecording && hasRecording && (
        <button
          type="button"
          onClick={onReset}
          className="flex items-center gap-2 rounded-lg bg-slate-200 px-4 py-2 text-slate-800 font-medium hover:bg-slate-300"
        >
          <RotateCcw size={18} />
          Record Again
        </button>
      )}
    </div>
  );
}
