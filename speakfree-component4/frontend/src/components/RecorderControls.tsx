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
          className="flex items-center gap-2 rounded-full bg-teal-600 px-5 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Mic size={16} />
          Start Recording
        </button>
      )}

      {isRecording && !isPaused && (
        <>
          <button
            type="button"
            onClick={onPause}
            className="flex items-center gap-2 rounded-full bg-teal-50 px-5 py-2 text-sm font-medium text-ink hover:bg-teal-100"
          >
            <Pause size={16} />
            Pause
          </button>
          <button
            type="button"
            onClick={onStop}
            className="flex items-center gap-2 rounded-full bg-red-600 px-5 py-2 text-sm font-medium text-white hover:bg-red-700"
          >
            <Square size={16} />
            Stop &amp; Submit
          </button>
        </>
      )}

      {isRecording && isPaused && (
        <>
          <button
            type="button"
            onClick={onResume}
            className="flex items-center gap-2 rounded-full bg-teal-600 px-5 py-2 text-sm font-medium text-white hover:bg-teal-700"
          >
            <Play size={16} />
            Resume
          </button>
          <button
            type="button"
            onClick={onStop}
            className="flex items-center gap-2 rounded-full bg-red-600 px-5 py-2 text-sm font-medium text-white hover:bg-red-700"
          >
            <Square size={16} />
            Stop &amp; Submit
          </button>
        </>
      )}

      {!isRecording && hasRecording && (
        <button
          type="button"
          onClick={onReset}
          className="flex items-center gap-2 rounded-full bg-teal-50 px-5 py-2 text-sm font-medium text-ink hover:bg-teal-100"
        >
          <RotateCcw size={16} />
          Record Again
        </button>
      )}
    </div>
  );
}
