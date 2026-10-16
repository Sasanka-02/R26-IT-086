import { useEffect, useState } from "react";
import { Wind } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const PHASES = [
  { label: "Breathe in", seconds: 4, scale: 1 },
  { label: "Hold", seconds: 4, scale: 1 },
  { label: "Breathe out", seconds: 4, scale: 0.55 },
];
const ROUNDS = 3;
// Children see the same breathing as a balloon game.
const KID_LABELS: Record<string, string> = {
  "Breathe in": "Smell the flower 🌸",
  Hold: "Hold it…",
  "Breathe out": "Blow up the balloon 🎈",
};

/** Calm, paced breathing before speaking — a common fluency-shaping warm-up. */
export default function BreathingWarmup({ onDone }: { onDone: () => void }) {
  const { user } = useAuth();
  const kid = user?.age_group === "child";
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
        <Wind size={16} className="text-teal-600" /> {kid ? "Balloon game 🎈" : "Breathing warm-up"} · round{" "}
        {Math.min(round, ROUNDS)} of {ROUNDS}
      </p>
      <div className="flex h-40 w-40 items-center justify-center">
        <div
          className={`flex h-36 w-36 items-center justify-center rounded-full ring-2 ${
            kid ? "bg-[#FF9AA2]/40 ring-[#FF9AA2]" : "bg-teal-600/15 ring-teal-600/40"
          }`}
          style={{
            // The balloon grows as the child blows out; the calm circle shrinks.
            transform: `scale(${kid ? 1.55 - phase.scale : phase.scale})`,
            transition: `transform ${phase.seconds}s ease-in-out`,
          }}
        >
          <span className={`font-display font-semibold ${kid ? "text-base text-[#1f2937]" : "text-lg text-teal-800"}`}>
            {kid ? KID_LABELS[phase.label] : phase.label}
          </span>
        </div>
      </div>
      <p className="text-sm text-ink-soft" aria-live="polite">
        {kid ? KID_LABELS[phase.label] : phase.label} · {remaining}
      </p>
      <button onClick={onDone} className="text-sm font-medium text-teal-700 hover:underline">
        Skip warm-up
      </button>
    </div>
  );
}
