import { useCallback, useRef, useState } from "react";
import { CheckCircle2, Headphones, Play, Square } from "lucide-react";
import { calibrateDaf } from "./therapyApi";
import { DafTrial } from "../types/therapy";
import { useDafPlayback } from "./useDafPlayback";
import RecordingPlayer from "../components/RecordingPlayer";
import DafMeter from "./DafMeter";
import { DAF_PASSAGES } from "./dafPassages";

const DELAY_OPTIONS = [50, 100, 150, 200, 300];

interface DafCalibrationProps {
  sessionId: string;
  onCalibrated: (delayMs: number) => void;
}

export default function DafCalibration({ sessionId, onCalibrated }: DafCalibrationProps) {
  const [trialIndex, setTrialIndex] = useState(0);
  const [trials, setTrials] = useState<DafTrial[]>([]);
  const [stutterEvents, setStutterEvents] = useState(0);
  const [speechRate, setSpeechRate] = useState(120);
  const [result, setResult] = useState<number | null>(null);

  const currentDelay = DELAY_OPTIONS[trialIndex];
  // A different passage for each trial, so trials compare delays, not practice.
  const passage = DAF_PASSAGES[trialIndex % DAF_PASSAGES.length];
  const passageWords = passage.text.split(/\s+/).length;
  const listenStartedRef = useRef(0);

  // Plays the student's voice back at this trial's delay while they read.
  // Records each trial (your own voice, without the delay) so you can listen
  // back and count the stutters afterwards, instead of while reading.
  const daf = useDafPlayback({ record: true });
  const [recordedTrial, setRecordedTrial] = useState<number | null>(null);
  const listening = daf.active;
  const micError = daf.error;
  const { stop: stopPlayback } = daf;

  /** Stops the delayed playback; returns the speech rate measured while
   *  listening (passage words / reading time), or null if there wasn't one. */
  const stopListening = useCallback((): number | null => {
    let measured: number | null = null;
    if (listenStartedRef.current) {
      const minutes = (Date.now() - listenStartedRef.current) / 60000;
      listenStartedRef.current = 0;
      if (minutes > 0.1) {
        measured = Math.round(passageWords / minutes);
        setSpeechRate(measured);
      }
    }
    stopPlayback();
    return measured;
  }, [passageWords, stopPlayback]);

  const startListening = () => {
    listenStartedRef.current = Date.now();
    setRecordedTrial(trialIndex);
    daf.start(currentDelay); // called straight from the click, so audio is allowed
  };

  const recordTrial = async () => {
    const measured = stopListening(); // still listening? use the rate just measured
    const newTrials = [
      ...trials,
      { delay_ms: currentDelay, stutter_events: stutterEvents, speech_rate_wpm: measured ?? speechRate },
    ];
    setTrials(newTrials);
    setStutterEvents(0);
    setSpeechRate(120);

    if (trialIndex + 1 < DELAY_OPTIONS.length) {
      setTrialIndex((i) => i + 1);
    } else {
      const res = await calibrateDaf(sessionId, newTrials);
      setResult(res.recommended_delay_ms);
      onCalibrated(res.recommended_delay_ms);
    }
  };

  if (result !== null) {
    return (
      <div className="flex items-center gap-3 rounded-2xl border border-teal-200 bg-teal-50 p-6">
        <CheckCircle2 className="text-teal-600" size={24} />
        <div>
          <p className="font-display font-semibold text-ink">Calibration complete</p>
          <p className="mt-0.5 text-sm text-ink-soft">
            Recommended delay: <strong className="text-teal-700">{result}ms</strong>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-2xl border border-teal-100 bg-white p-6">
      <div className="flex items-center justify-between">
        <h3 className="font-display font-semibold text-ink">DAF Calibration</h3>
        <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-700">
          Trial {trialIndex + 1} of {DELAY_OPTIONS.length}
        </span>
      </div>
      <ol className="grid gap-2 text-sm text-ink sm:grid-cols-4">
        {[
          "Put on headphones",
          "Press Start and read the passage aloud",
          "Press Stop when you finish",
          "Listen back and count how many times you got stuck",
        ].map((step, i) => (
          <li key={step} className="flex items-start gap-2 rounded-lg bg-paper px-3 py-2">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-teal-600 text-xs font-semibold text-white">
              {i + 1}
            </span>
            {step}
          </li>
        ))}
      </ol>

      {!listening ? (
        <button
          onClick={startListening}
          className="flex w-full items-center justify-center gap-2 rounded-2xl bg-teal-600 px-6 py-4 text-base font-semibold text-white shadow-sm hover:bg-teal-700 sm:w-auto"
        >
          <Play size={18} />
          Start trial {trialIndex + 1} — hear your voice {currentDelay}ms late
        </button>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => stopListening()}
            className="flex w-full items-center justify-center gap-2 rounded-2xl bg-red-600 px-6 py-4 text-base font-semibold text-white shadow-sm hover:bg-red-700 sm:w-auto"
          >
            <Square size={16} />
            Stop — I've finished reading
          </button>
          <span className="flex items-center gap-2 text-sm font-medium text-teal-700">
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-red-500" aria-hidden="true" />
            <Headphones size={15} /> Playing your voice back {currentDelay}ms late — read the passage now
          </span>
        </div>
      )}

      <div className="rounded-xl border border-teal-100 bg-paper p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">
          Passage {trialIndex + 1} · {passage.title}
        </p>
        <p className="mt-2 text-lg leading-relaxed text-ink">{passage.text}</p>
      </div>

      <DafMeter
        active={listening}
        level={daf.level}
        heardVoice={daf.heardVoice}
        calibrating={daf.calibrating}
        volume={daf.volume}
        onVolume={daf.setVolume}
      />
      {micError && <p className="text-sm text-red-600">{micError}</p>}

      {!listening && daf.recordingUrl && recordedTrial === trialIndex && (
        <div className="space-y-2">
          <RecordingPlayer src={daf.recordingUrl} label={`Listen back to trial ${trialIndex + 1} and count`} />
          <p className="rounded-lg bg-paper px-3 py-2 text-xs text-ink-soft">
            Count one each time you hear: a <strong className="text-ink">repeated sound or word</strong> (“b-b-bread”,
            “the the shop”), a <strong className="text-ink">stretched sound</strong> (“sssshop”), or a{" "}
            <strong className="text-ink">block</strong> — getting stuck silently before a word. Normal pauses for
            breath don't count.
          </p>
        </div>
      )}

      <div className="space-y-3">
        <div>
          <label className="text-sm font-medium text-ink">Stutter events observed</label>
          <input
            type="number"
            min={0}
            value={stutterEvents}
            onChange={(e) => setStutterEvents(Number(e.target.value))}
            className="mt-1 w-full rounded-lg border border-teal-100 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
          />
        </div>
        <div>
          <label className="text-sm font-medium text-ink">Speech rate (WPM)</label>
          <p className="text-xs text-ink-soft">Filled in from how long you took to read the passage — change it if needed.</p>
          <input
            type="number"
            min={0}
            value={speechRate}
            onChange={(e) => setSpeechRate(Number(e.target.value))}
            className="mt-1 w-full rounded-lg border border-teal-100 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
          />
        </div>
      </div>

      <button
        onClick={recordTrial}
        className="rounded-full bg-teal-600 px-5 py-2 text-sm font-medium text-white hover:bg-teal-700"
      >
        {trialIndex + 1 < DELAY_OPTIONS.length ? "Next Trial" : "Finish Calibration"}
      </button>
    </div>
  );
}
