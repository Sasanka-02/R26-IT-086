/** Calm, paced breathing before speaking (3 rounds of in 4 s · hold 4 s · out 4 s). Ages 6–11 see a balloon game. */
import { useEffect, useState } from "react";
import { Wind } from "lucide-react";

const PHASES = [
  { label: "Breathe in", kid: "Smell the flower 🌸", seconds: 4, scale: 1 },
  { label: "Hold", kid: "Hold it…", seconds: 4, scale: 1 },
  { label: "Breathe out", kid: "Blow up the balloon 🎈", seconds: 4, scale: 0.55 },
];
const ROUNDS = 3;

export default function BreathingWarmup({ onDone, playful = false }: { onDone: () => void; playful?: boolean }) {
  const [step, setStep] = useState(0);
  const [left, setLeft] = useState(PHASES[0].seconds);
  const round = Math.floor(step / PHASES.length) + 1;
  const phase = PHASES[step % PHASES.length];

  useEffect(() => {
    if (round > ROUNDS) { onDone(); return; }
    const t = window.setTimeout(() => {
      if (left > 1) setLeft(left - 1);
      else { setStep(step + 1); setLeft(PHASES[(step + 1) % PHASES.length].seconds); }
    }, 1000);
    return () => window.clearTimeout(t);
  }, [step, left, round, onDone]);

  const text = playful ? phase.kid : phase.label;
  return (
    <div className="flex flex-col items-center gap-4 rounded-2xl border border-lav-200 bg-lav-50 p-6 text-center">
      <p className="flex items-center gap-2 text-sm font-semibold text-ink"><Wind size={16} className="text-lav-600" /> {playful ? "Balloon game 🎈" : "Breathing warm-up"} · round {Math.min(round, ROUNDS)} of {ROUNDS}</p>
      <div className="grid h-40 w-40 place-items-center">
        <div className={`grid h-36 w-36 place-items-center rounded-full ring-2 ${playful ? "bg-bad-soft ring-bad/30" : "bg-lav-100 ring-lav-400"}`}
          style={{ transform: `scale(${playful ? 1.55 - phase.scale : phase.scale})`, transition: `transform ${phase.seconds}s ease-in-out` }}>
          <span className="px-2 text-base font-bold text-navy">{text}</span>
        </div>
      </div>
      <p className="text-sm text-ink-soft" aria-live="polite">{text} · {left}</p>
      <button onClick={onDone} className="text-sm font-semibold text-brand hover:underline">Skip warm-up</button>
    </div>
  );
}
