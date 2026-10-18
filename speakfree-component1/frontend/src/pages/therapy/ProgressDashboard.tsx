/**
 * Word ladder card for the (light) therapy plan page. The full progress dashboard is the dark-theme
 * My progress page (ProgressDark.tsx).
 */
import { Card } from "../../components/ui";
import type { WordLevelState } from "../../types/integration";

export function WordLadder({ words }: { words: WordLevelState }) {
  return (
    <Card title="Word practice ladder" icon={<span aria-hidden>🌟</span>} right={<span className="text-xs muted">{words.rounds} round{words.rounds === 1 ? "" : "s"}</span>}>
      <ol className="flex flex-wrap gap-1.5" aria-label="Word ladder">
        {Array.from({ length: words.ladder_size }, (_, i) => {
          const step = i + 1;
          const done = step < words.level || (words.mastered && step === words.level);
          const current = step === words.level && !words.mastered;
          const label = step <= words.word_levels ? `${step}` : `P${step - words.word_levels}`;
          return (
            <li key={step} title={step <= words.word_levels ? `Word level ${step}` : `Phrase stage ${step - words.word_levels}`}
              className={`grid h-9 min-w-[2.25rem] place-items-center rounded-full px-2 text-sm font-bold ${current ? "bg-sun text-ink shadow-sm" : done ? "bg-sun-soft text-warn" : "border border-dashed border-line text-ink-muted"}`}>
              {done ? "⭐" : label}
            </li>
          );
        })}
      </ol>
      <p className="mt-3 text-sm text-ink-soft">{words.progress_text}</p>
      <p className="mt-1 text-xs muted">Levels 1–7 are single words (easy sounds → long tricky words); P1–P3 are phrases, sentences and tongue twisters.</p>
    </Card>
  );
}
