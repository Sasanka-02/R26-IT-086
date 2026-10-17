import { useEffect, useMemo, useRef, useState } from "react";
import { Mic, Square, Volume2 } from "lucide-react";
import { TherapyExercise, WordItem } from "../types/therapy";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import AudioVisualizer from "../components/AudioVisualizer";
import RecordingPlayer from "../components/RecordingPlayer";
import CompletionPanel from "./CompletionPanel";

type Mark = "got" | "almost" | "hard";

const MARKS: { value: Mark; emoji: string; label: string; className: string }[] = [
  { value: "got", emoji: "😊", label: "Got it", className: "bg-[#7BD389] hover:bg-[#68c777]" },
  { value: "almost", emoji: "😐", label: "Almost", className: "bg-[#FFD166] hover:bg-[#f5c450]" },
  { value: "hard", emoji: "😟", label: "Hard", className: "bg-[#FF9AA2] hover:bg-[#f7858f]" },
];

// Bright card backgrounds, cycled per card. Text on them is always dark.
const CARD_COLOURS = ["#FFE6A7", "#C7F0DB", "#CFE3FF", "#FFD6E8", "#E5D9FF", "#FFE0C7"];
const BURST = ["⭐", "🌟", "✨", "🎉", "⭐", "🌟", "✨", "🎈"];
const MAX_CARDS = 10;
const SPEECH_RATE = 0.7;

function speak(text: string) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = SPEECH_RATE;
  utterance.pitch = 1.05;
  window.speechSynthesis.speak(utterance);
}

/** Stars that fly out from the card when a word is said well. */
function StarBurst({ id }: { id: number }) {
  const pieces = useMemo(
    () =>
      BURST.map((emoji, i) => {
        const angle = (i / BURST.length) * 2 * Math.PI;
        return {
          emoji,
          style: {
            "--dx": `${Math.round(Math.cos(angle) * 140)}px`,
            "--dy": `${Math.round(Math.sin(angle) * 110)}px`,
            "--rot": `${(i % 2 ? 1 : -1) * 40}deg`,
          } as React.CSSProperties,
        };
      }),
    [id] // a new id means a new burst
  );
  return (
    <div aria-hidden="true">
      {pieces.map((p, i) => (
        <span key={`${id}-${i}`} className="word-burst-piece" style={p.style}>
          {p.emoji}
        </span>
      ))}
    </div>
  );
}

function SyllableBeats({ count }: { count: number }) {
  return (
    <span className="flex items-center justify-center gap-1.5" aria-label={`${count} beats`}>
      {Array.from({ length: count }, (_, i) => (
        <span key={i} className="h-2.5 w-2.5 rounded-full bg-[#1f2937]/40" />
      ))}
    </span>
  );
}

/** Child-friendly picture-card round: one big picture and word at a time. */
export default function WordPracticeExercise({ exercise }: { exercise: TherapyExercise }) {
  const cards: WordItem[] = (exercise.words ?? []).slice(0, MAX_CARDS);
  const recorder = useAudioRecorder();
  const [index, setIndex] = useState(0);
  const [marks, setMarks] = useState<Mark[]>([]);
  const [burst, setBurst] = useState<number | null>(null);
  const startedAtRef = useRef(Date.now());
  const advanceTimer = useRef<number | null>(null);

  const done = marks.length === cards.length && cards.length > 0;
  const card = cards[Math.min(index, cards.length - 1)];
  const got = marks.filter((m) => m === "got").length;
  const almost = marks.filter((m) => m === "almost").length;
  const elapsed = useMemo(() => (done ? (Date.now() - startedAtRef.current) / 1000 : 0), [done]);
  const passed = done && got >= Math.ceil(cards.length * 0.75);

  // Stop speech, timers and the microphone when leaving the screen. The
  // recorder's clear function changes with every recording, so the latest one
  // is kept in a ref and only called on unmount.
  const clearRef = useRef(recorder.clearRecording);
  clearRef.current = recorder.clearRecording;
  useEffect(
    () => () => {
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
      if (advanceTimer.current) window.clearTimeout(advanceTimer.current);
      clearRef.current();
    },
    []
  );

  const toggleRecording = () => {
    if (recorder.isRecording) {
      recorder.stopRecording();
    } else {
      recorder.clearRecording();
      recorder.startRecording();
    }
  };

  const markCard = (mark: Mark) => {
    if (advanceTimer.current) return; // already moving to the next card
    if (recorder.isRecording) recorder.stopRecording();
    if (mark === "got") setBurst(Date.now());
    const next = [...marks, mark];
    advanceTimer.current = window.setTimeout(
      () => {
        advanceTimer.current = null;
        setMarks(next);
        setBurst(null);
        recorder.clearRecording();
        if (next.length < cards.length) setIndex((i) => i + 1);
      },
      mark === "got" ? 900 : 300
    );
  };

  if (cards.length === 0) return <p className="text-sm text-ink-soft">This exercise has no word cards.</p>;

  return (
    <div className="space-y-4 rounded-2xl border border-teal-100 bg-white p-4 sm:p-6">
      <div>
        <h2 className="font-display text-lg font-semibold text-ink">{exercise.title}</h2>
        <p className="text-sm text-ink-soft">{exercise.description}</p>
      </div>

      {/* Progress through the cards */}
      <div>
        <div className="mb-1 flex justify-between text-xs font-medium text-ink-soft">
          <span>
            Card {Math.min(marks.length + 1, cards.length)} of {cards.length}
          </span>
          <span>
            {"⭐".repeat(got)}
            <span className="sr-only">{got} stars</span>
          </span>
        </div>
        <div className="h-3 w-full overflow-hidden rounded-full bg-[#f1e9d2]">
          <div
            className="h-full rounded-full bg-[#7BD389] transition-all duration-500"
            style={{ width: `${(marks.length / cards.length) * 100}%` }}
          />
        </div>
      </div>

      {!done && (
        <>
          <div
            key={index}
            className="word-pop relative flex min-h-[18rem] flex-col items-center justify-center gap-3 overflow-hidden rounded-[2rem] px-4 py-8 text-center text-[#1f2937] shadow-sm"
            style={{ backgroundColor: CARD_COLOURS[index % CARD_COLOURS.length] }}
          >
            <span className="text-[6rem] leading-none sm:text-[7.5rem]" role="img" aria-label={card.text}>
              {card.emoji}
            </span>
            <p className="font-kid text-5xl font-extrabold tracking-wide sm:text-6xl">{card.text}</p>
            <SyllableBeats count={card.syllables} />
            {card.tip && <p className="text-base font-semibold text-[#1f2937]/70">💡 {card.tip}</p>}
            {burst !== null && <StarBurst id={burst} />}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => speak(card.text)}
              className="flex min-h-[3.5rem] items-center justify-center gap-2 rounded-2xl bg-[#CFE3FF] px-4 text-lg font-bold text-[#1f2937] hover:bg-[#bcd6fb]"
            >
              <Volume2 size={22} /> Listen
            </button>
            <button
              onClick={toggleRecording}
              className={`flex min-h-[3.5rem] items-center justify-center gap-2 rounded-2xl px-4 text-lg font-bold ${
                recorder.isRecording ? "bg-red-600 text-white hover:bg-red-700" : "bg-teal-600 text-white hover:bg-teal-700"
              }`}
            >
              {recorder.isRecording ? <Square size={20} /> : <Mic size={22} />}
              {recorder.isRecording ? "Stop" : "Say it"}
            </button>
          </div>

          {recorder.isRecording && (
            <AudioVisualizer analyserNode={recorder.analyserNode} isRecording={recorder.isRecording} height={70} />
          )}
          {recorder.permissionError && <p className="text-sm text-red-600">{recorder.permissionError}</p>}
          {recorder.audioUrl && !recorder.isRecording && (
            <RecordingPlayer key={recorder.audioUrl} src={recorder.audioUrl} label="Listen to yourself" />
          )}

          <div>
            <p className="mb-2 text-center text-sm font-semibold text-ink">How did that word go?</p>
            <div className="grid grid-cols-3 gap-2 sm:gap-3">
              {MARKS.map((m) => (
                <button
                  key={m.value}
                  onClick={() => markCard(m.value)}
                  className={`flex min-h-[4.5rem] flex-col items-center justify-center rounded-2xl px-2 text-[#1f2937] transition active:scale-95 ${m.className}`}
                >
                  <span className="text-3xl leading-none" aria-hidden="true">
                    {m.emoji}
                  </span>
                  <span className="mt-1 text-sm font-bold">{m.label}</span>
                </button>
              ))}
            </div>
          </div>
        </>
      )}

      {done && (
        <div className="space-y-4">
          <div className="flex flex-col items-center gap-2 rounded-[2rem] bg-[#FFF4CC] px-4 py-8 text-center text-[#1f2937]">
            <span className="word-sticker text-[5.5rem] leading-none" aria-hidden="true">
              {passed ? "🏆" : "🌈"}
            </span>
            <p className="font-kid text-4xl font-extrabold">{passed ? "Level complete!" : "Round complete!"}</p>
            <p className="text-lg font-semibold">
              {got} of {cards.length} words said well
              {almost > 0 ? ` · ${almost} almost` : ""}
            </p>
            <p className="text-2xl" aria-hidden="true">
              {"⭐".repeat(got)}
            </p>
            <p className="text-sm text-[#1f2937]/70">
              {passed
                ? "Brilliant! Save your result to unlock the next level."
                : "Every round makes the words easier. Try this level again any time."}
            </p>
          </div>
          <CompletionPanel
            metrics={{
              exercise_id: exercise.id,
              duration_seconds: elapsed,
              words_correct: got,
              words_total: cards.length,
            }}
          />
        </div>
      )}

      <p className="text-xs text-ink-soft">
        Grown-ups: tap 😊 when the word came out smoothly, 😐 if it was nearly there, 😟 if it was hard. Recordings stay
        on this device; only the score is saved.
      </p>
    </div>
  );
}
