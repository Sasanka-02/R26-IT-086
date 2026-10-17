import { useRef, useState } from "react";
import { Play, Square } from "lucide-react";
import { TherapyExercise } from "../types/therapy";
import CompletionPanel from "./CompletionPanel";
import RecordingPlayer from "../components/RecordingPlayer";
import { useDafPlayback } from "./useDafPlayback";
import DafMeter from "./DafMeter";
import { DAF_PASSAGES } from "./dafPassages";

interface DafExerciseProps {
  exercise: TherapyExercise;
  initialDelayMs?: number;
}

export default function DafExercise({ exercise, initialDelayMs = 150 }: DafExerciseProps) {
  const daf = useDafPlayback({ record: true });
  const [delayMs, setDelayMs] = useState(initialDelayMs);
  const [passageIndex, setPassageIndex] = useState(0);
  const passage = DAF_PASSAGES[passageIndex];
  const [practisedSeconds, setPractisedSeconds] = useState<number | null>(null);
  const startedAtRef = useRef(0);
  const isActive = daf.active;
  const recordingUrl = daf.recordingUrl;
  const permissionError = daf.error;

  const start = () => {
    startedAtRef.current = Date.now();
    setPractisedSeconds(null);
    daf.start(delayMs);
  };

  const handleStop = () => {
    daf.stop();
    setPractisedSeconds((Date.now() - startedAtRef.current) / 1000);
  };

  const handleDelayChange = (value: number) => {
    setDelayMs(value);
    daf.setDelay(value);
  };

  return (
    <div className="space-y-4 rounded-2xl border border-teal-100 bg-white p-6">
      <div>
        <h2 className="font-display text-lg font-semibold text-ink">{exercise.title}</h2>
        <p className="text-sm text-ink-soft">{exercise.description}</p>
      </div>

      {!isActive ? (
        <button
          onClick={start}
          className="flex w-full items-center justify-center gap-2 rounded-2xl bg-teal-600 px-6 py-4 text-base font-semibold text-white shadow-sm hover:bg-teal-700 sm:w-auto"
        >
          <Play size={18} />
          Start speaking — hear your voice {delayMs}ms late
        </button>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleStop}
            className="flex w-full items-center justify-center gap-2 rounded-2xl bg-red-600 px-6 py-4 text-base font-semibold text-white shadow-sm hover:bg-red-700 sm:w-auto"
          >
            <Square size={16} />
            Stop
          </button>
          <span className="flex items-center gap-2 text-sm font-medium text-teal-700">
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-red-500" aria-hidden="true" />
            Playing your voice back {delayMs}ms late — read the passage aloud
          </span>
        </div>
      )}

      <div className="rounded-xl border border-teal-100 bg-paper p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">
            Read aloud · {passage.title}
          </p>
          <button
            onClick={() => setPassageIndex((i) => (i + 1) % DAF_PASSAGES.length)}
            className="rounded-full border border-teal-200 px-3 py-1 text-xs font-medium text-teal-700 hover:bg-teal-50"
          >
            Next passage
          </button>
        </div>
        <p className="mt-2 text-lg leading-relaxed text-ink">{passage.text}</p>
        <p className="mt-2 text-xs text-ink-soft">Or talk freely about your day — the delay works with any speech.</p>
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
        <p className="mt-3 rounded-lg border border-gold-400/50 bg-gold-400/10 px-3 py-2 text-xs font-medium text-ink">
          🎧 Put on headphones before you start. Through open speakers the delayed voice is picked up by the
          microphone again, which causes a loud echo and spoils the recording.
        </p>
      </div>

      <DafMeter
        active={isActive}
        level={daf.level}
        heardVoice={daf.heardVoice}
        calibrating={daf.calibrating}
        volume={daf.volume}
        onVolume={daf.setVolume}
      />

      {permissionError && <p className="text-sm text-red-600">{permissionError}</p>}


      {recordingUrl && !isActive && (
        <RecordingPlayer src={recordingUrl} label="Listen to your speech (your own voice, without the delay)" />
      )}

      {practisedSeconds !== null && !isActive && !daf.heardVoice && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-ink" role="alert">
          <p className="font-medium">We didn't hear you speaking, so this practice hasn't been scored.</p>
          <p className="mt-1 text-ink-soft">
            A score needs at least 2 seconds of your voice. Press Start, wait for “Get ready” to finish, then read
            the passage aloud. If you did speak, check the microphone selected for this site.
          </p>
        </div>
      )}

      {practisedSeconds !== null && !isActive && daf.heardVoice && (
        <CompletionPanel
          key={practisedSeconds}
          metrics={{ exercise_id: exercise.id, duration_seconds: practisedSeconds }}
          recordingUrl={recordingUrl}
        />
      )}

      <p className="text-xs text-ink-soft">
        Privacy: this exercise runs entirely in your browser — no audio
        is sent to any server. The recording is kept only in this page for you
        to listen back; only your practice time and rating are saved.
      </p>
    </div>
  );
}