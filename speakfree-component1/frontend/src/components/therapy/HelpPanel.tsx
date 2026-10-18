/**
 * HelpPanel – the "Need help" tab of every therapy exercise:
 *   1. Listen to a model (speech synthesis reads the passage / model answer aloud)
 *   2. How to do it – step by step
 *   3. Example answers – one per question, each with its own 🔊 Listen
 *   4. The speaking techniques for the learner's plan focus
 */
import { BookOpen, Headphones, Lightbulb, ListChecks, Sparkles } from "lucide-react";
import ListenButton from "../ListenButton";
import type { Exercise } from "../../types/integration";

export default function HelpPanel({ ex, techniques, playful }: { ex: Exercise; techniques: string[]; playful: boolean }) {
  const help = ex.help;
  if (!help) return <p className="text-sm muted">No help is available for this exercise yet.</p>;
  const prompts = ex.type === "picture" || ex.type === "conversation" || ex.type === "roleplay" ? ex.prompts ?? [] : [];
  return (
    <div className="space-y-5">
      <section className="flex flex-col gap-3 rounded-2xl border border-lav-200 bg-lav-50 p-4 sm:flex-row sm:items-center">
        <Headphones className="shrink-0 text-lav-600" />
        <div className="flex-1">
          <p className="font-bold text-ink">Listen to a model</p>
          <p className="text-sm text-ink-soft">{help.examples.length ? "Hear the example answers read slowly and clearly." : "Hear the text read slowly and clearly, then try it yourself."}</p>
        </div>
        <ListenButton text={help.model} wpm={ex.target_wpm ?? 100} big={playful} />
      </section>

      <section>
        <h3 className="mb-2 flex items-center gap-2 font-bold text-ink"><ListChecks size={17} className="text-navy" /> How to do it</h3>
        <ol className="space-y-2">
          {help.steps.map((s, i) => (
            <li key={s} className="flex gap-3 rounded-xl bg-canvas px-3 py-2.5 text-sm text-ink">
              <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-navy text-xs font-bold text-white">{i + 1}</span>{s}
            </li>
          ))}
        </ol>
      </section>

      {help.examples.length > 0 && (
        <section>
          <h3 className="mb-2 flex items-center gap-2 font-bold text-ink"><Lightbulb size={17} className="text-warn" /> {ex.type === "sound_drill" || ex.type === "words" ? "The words to say" : "Example answers"}</h3>
          <ul className="space-y-2">
            {help.examples.map((a, i) => (
              <li key={`${i}-${a}`} className="rounded-xl border border-sun/40 bg-sun-soft p-3">
                {prompts[i] && <p className="mb-1 text-xs font-bold uppercase tracking-wide text-warn">{prompts[i]}</p>}
                <div className="flex items-start justify-between gap-3">
                  <p className={`text-ink ${playful ? "text-lg" : "text-sm"}`}>{a}</p>
                  <ListenButton text={a} wpm={ex.target_wpm ?? 100} />
                </div>
              </li>
            ))}
          </ul>
          {prompts.length > 0 && <p className="mt-2 flex items-center gap-1.5 text-xs muted"><Sparkles size={13} /> These are only examples – your own words are just as good.</p>}
        </section>
      )}

      {ex.passage && !help.examples.length && (
        <section>
          <h3 className="mb-2 flex items-center gap-2 font-bold text-ink"><BookOpen size={17} className="text-navy" /> The text</h3>
          <p className="rounded-xl bg-canvas p-3 text-sm leading-relaxed text-ink">{ex.passage}</p>
        </section>
      )}

      {techniques.length > 0 && (
        <section>
          <h3 className="mb-2 font-bold text-ink">Speaking tips for your plan</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-ink-soft">{techniques.map((t) => <li key={t}>{t}</li>)}</ul>
        </section>
      )}
    </div>
  );
}
