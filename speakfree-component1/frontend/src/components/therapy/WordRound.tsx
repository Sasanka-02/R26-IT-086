/**
 * Picture-card word round (ages 6–11): one big picture + word at a time, "🔊 Listen" model,
 * syllable beats and a gentle-start tip. A grown-up taps 😊 Got it / 😐 Almost / 😟 Hard.
 * Nothing is recorded or uploaded – the round's result is the number of words said well.
 */
import { useEffect, useRef, useState } from "react";
import { Volume2 } from "lucide-react";
import type { WordCard } from "../../types/integration";

type Mark = "got" | "almost" | "hard";
const MARKS: { value: Mark; emoji: string; label: string; className: string }[] = [
  { value: "got", emoji: "😊", label: "Got it", className: "bg-ok-soft hover:brightness-95 ring-ok/40" },
  { value: "almost", emoji: "😐", label: "Almost", className: "bg-sun-soft hover:brightness-95 ring-sun/40" },
  { value: "hard", emoji: "😟", label: "Hard", className: "bg-bad-soft hover:brightness-95 ring-bad/30" },
];
const CARD_BG = ["#FFF4DE", "#E8F7EE", "#E8EEFF", "#EFEBFF", "#FDECEC", "#F7F5FF"];

function speak(text: string) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 0.7;
  u.pitch = 1.05;
  window.speechSynthesis.speak(u);
}

export default function WordRound({ cards, onDone }: { cards: WordCard[]; onDone: (got: number, total: number) => void }) {
  const [index, setIndex] = useState(0);
  const [marks, setMarks] = useState<Mark[]>([]);
  const [burst, setBurst] = useState(false);
  const timer = useRef<number | null>(null);
  const card = cards[Math.min(index, cards.length - 1)];
  const got = marks.filter((m) => m === "got").length;

  useEffect(() => () => {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    if (timer.current) window.clearTimeout(timer.current);
  }, []);

  const mark = (m: Mark) => {
    if (timer.current) return;
    if (m === "got") setBurst(true);
    const next = [...marks, m];
    timer.current = window.setTimeout(() => {
      timer.current = null;
      setBurst(false);
      setMarks(next);
      if (next.length < cards.length) setIndex((i) => i + 1);
      else onDone(next.filter((x) => x === "got").length, cards.length);
    }, m === "got" ? 800 : 250);
  };

  if (!card) return null;
  return (
    <div className="space-y-4">
      <div>
        <div className="mb-1 flex justify-between text-xs font-semibold text-ink-soft">
          <span>Card {Math.min(marks.length + 1, cards.length)} of {cards.length}</span>
          <span aria-label={`${got} stars`}>{"⭐".repeat(got)}</span>
        </div>
        <div className="h-3 rounded-full bg-sun-soft"><div className="h-3 rounded-full bg-ok transition-all duration-500" style={{ width: `${(marks.length / cards.length) * 100}%` }} /></div>
      </div>
      <div key={index} className="animate-step relative flex min-h-[17rem] flex-col items-center justify-center gap-3 overflow-hidden rounded-[2rem] px-4 py-8 text-center"
        style={{ background: CARD_BG[index % CARD_BG.length] }}>
        <span className="text-[6rem] leading-none" role="img" aria-label={card.text}>{card.emoji}</span>
        <p className="text-5xl font-extrabold tracking-wide text-ink">{card.text}</p>
        <span className="flex gap-1.5" aria-label={`${card.syllables} beats`}>
          {Array.from({ length: card.syllables }, (_, i) => <span key={i} className="h-2.5 w-2.5 rounded-full bg-ink/40" />)}
        </span>
        {card.tip && <p className="text-base font-semibold text-ink-soft">💡 {card.tip}</p>}
        {burst && <div className="pointer-events-none absolute inset-x-0 top-6" aria-hidden>
          {["⭐", "🌟", "✨", "🎉", "⭐", "🌟"].map((e, i) => <span key={i} className="confetti-piece absolute text-2xl" style={{ left: `${10 + i * 15}%`, animationDelay: `${i * 0.06}s` }}>{e}</span>)}
        </div>}
      </div>
      <button type="button" onClick={() => speak(card.text)} className="flex w-full items-center justify-center gap-2 rounded-2xl bg-brand-soft py-4 text-lg font-bold text-navy hover:bg-lav-100">
        <Volume2 size={22} /> Listen
      </button>
      <div>
        <p className="mb-2 text-center text-sm font-semibold text-ink">Say it slowly, then: how did that word go?</p>
        <div className="grid grid-cols-3 gap-3">
          {MARKS.map((m) => (
            <button key={m.value} type="button" onClick={() => mark(m.value)}
              className={`flex min-h-[4.5rem] flex-col items-center justify-center rounded-2xl text-ink ring-1 transition active:scale-95 ${m.className}`}>
              <span className="text-3xl leading-none" aria-hidden>{m.emoji}</span><span className="mt-1 text-sm font-bold">{m.label}</span>
            </button>
          ))}
        </div>
      </div>
      <p className="text-xs muted">Grown-ups: tap 😊 when the word came out smoothly, 😐 if it was nearly there, 😟 if it was hard.</p>
    </div>
  );
}
