import { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { calibrateDaf } from "./therapyApi";
import { DafTrial } from "../types/therapy";

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

  const recordTrial = async () => {
    const newTrials = [
      ...trials,
      { delay_ms: currentDelay, stutter_events: stutterEvents, speech_rate_wpm: speechRate },
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
      <p className="text-sm text-ink-soft">
        Read the passage aloud at a <strong className="text-ink">{currentDelay}ms</strong> delay,
        then record what happened.
      </p>

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
