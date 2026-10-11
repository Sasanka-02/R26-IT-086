import { useEffect, useState } from "react";
import { Wind } from "lucide-react";

const PHASES = [
  { label: "Breathe in", seconds: 4, scale: 1 },
  { label: "Hold", seconds: 4, scale: 1 },
  { label: "Breathe out", seconds: 4, scale: 0.55 },
];
const ROUNDS = 3;

/** Calm, paced breathing before speaking — a common fluency-shaping warm-up. */
export default function BreathingWarmup({ onDone }: { onDone: () => void }) {
  const [step, setStep] = useState(0);
  const [remaining, setRemaining] = useState(PHASES[0].seconds);
  const round = Math.floor(step / PHASES.length) + 1;
  const phase = PHASES[step % PHASES.length];

  useEffect(() => {
    if (round > ROUNDS) {
      onDone();
      return;
    }
    const timer = window.setTimeout(() => {
      if (remaining > 1) {
        setRemaining(remaining - 1);
      } else {
        setStep(step + 1);
        setRemaining(PHASES[(step + 1) % PHASES.length].seconds);
      }
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [step, remaining, round, onDone]);

  return (
    <div className="flex flex-col items-center gap-4 rounded-xl border border-teal-100 bg-paper p-6 text-center">
      <p className="flex items-center gap-2 text-sm font-medium text-ink">
        <Wind size={16} className="text-teal-600" /> Breathing warm-up · round {Math.min(round, ROUNDS)} of {ROUNDS}
      </p>
      <div className="flex h-40 w-40 items-center justify-center">
        <div
          className="flex h-36 w-36 items-center justify-center rounded-full bg-teal-600/15 ring-2 ring-teal-600/40"
          style={{
            transform: `scale(${phase.scale})`,
            transition: `transform ${phase.seconds}s ease-in-out`,
          }}
        >
          <span className="font-display text-lg font-semibold text-teal-800">{phase.label}</span>
        </div>
      </div>
      <p className="text-sm text-ink-soft" aria-live="polite">
        {phase.label} · {remaining}
      </p>
      <button onClick={onDone} className="text-sm font-medium text-teal-700 hover:underline">
        Skip warm-up
      </button>
    </div>
  );
}
