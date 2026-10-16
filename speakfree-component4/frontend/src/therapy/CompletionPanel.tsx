import { useState } from "react";
import { CheckCircle2, Sparkles, TrendingUp } from "lucide-react";
import { usePracticeHistory } from "../context/PracticeHistoryContext";
import { ExerciseResultInput, ExerciseResultResponse, SelfRating } from "../types/therapy";

const RATINGS: { value: SelfRating; label: string; hint: string }[] = [
  { value: "easy", label: "Easy", hint: "Felt smooth and comfortable" },
  { value: "ok", label: "Okay", hint: "A few bumps, but manageable" },
  { value: "hard", label: "Hard", hint: "Felt difficult today" },
];

const SCORE_TONE = (score: number) =>
  score >= 65
    ? "border-teal-200 bg-teal-50 text-teal-800"
    : score >= 45
    ? "border-gold-400/60 bg-gold-400/10 text-gold-600"
    : "border-amber-200 bg-amber-50 text-amber-900";

interface CompletionPanelProps {
  /** Metrics for this attempt, minus the self-rating the user picks here. */
  metrics: Omit<ExerciseResultInput, "self_rating">;
  onSaved?: (result: ExerciseResultResponse) => void;
}

export default function CompletionPanel({ metrics, onSaved }: CompletionPanelProps) {
  const { recordCompletion, hideScore } = usePracticeHistory();
  const [rating, setRating] = useState<SelfRating | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExerciseResultResponse | null>(null);

  const save = async () => {
    if (!rating) return;
    setSaving(true);
    setError(null);
    try {
      const saved = await recordCompletion({ ...metrics, self_rating: rating });
      setResult(saved);
      onSaved?.(saved);
    } catch {
      setError("We couldn't save this result. Check that the therapy service is running.");
    } finally {
      setSaving(false);
    }
  };

  if (result && hideScore) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-teal-200 bg-teal-50 p-4 text-sm text-teal-800">
        <CheckCircle2 size={18} />
        Saved. The app's score is hidden until the expert has rated this attempt.
      </div>
    );
  }

  if (result) {
    return (
      <div className="space-y-3">
        <div className={`rounded-xl border p-4 ${SCORE_TONE(result.score)}`}>
          <div className="flex items-center gap-2">
            <CheckCircle2 size={18} />
            <p className="font-semibold">
              Score {result.score} / 100 — {result.verdict}
            </p>
          </div>
          {result.feedback.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-6 text-sm">
              {result.feedback.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          )}
        </div>

        {result.breakdown.length > 0 && (
          <details className="rounded-xl border border-teal-100 bg-white p-4 text-sm">
            <summary className="cursor-pointer font-medium text-ink">How this score was worked out</summary>
            <table className="mt-3 w-full text-left tabular-nums">
              <thead className="text-xs text-ink-soft">
                <tr>
                  <th className="pb-1 font-medium">Factor</th>
                  <th className="pb-1 text-right font-medium">Your value</th>
                  <th className="pb-1 text-right font-medium">Points</th>
                </tr>
              </thead>
              <tbody>
                {result.breakdown.map((part) => (
                  <tr key={part.feature} className="border-t border-teal-50">
                    <td className="py-1 text-ink">{part.label}</td>
                    <td className="py-1 text-right text-ink-soft">
                      {part.feature === "intercept" ? "—" : part.value}
                    </td>
                    <td className={`py-1 text-right font-semibold ${part.points < 0 ? "text-amber-800" : "text-teal-700"}`}>
                      {part.points > 0 ? "+" : ""}
                      {part.points}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {result.measured_wpm && result.target_wpm && (
              <p className="mt-2 text-xs text-ink-soft">
                Measured speed ≈ {result.measured_wpm} words/min (target {result.target_wpm}), estimated
                from syllable peaks in your voice — audio never leaves your browser.
              </p>
            )}
            <p className="mt-2 text-xs text-ink-soft">
              The weights are calibrated against therapist ratings, so they reflect expert judgement rather
              than fixed guesses.
            </p>
          </details>
        )}

        {result.level_message && (
          <div className="flex items-start gap-2 rounded-xl border border-gold-400/60 bg-gold-400/10 p-4 text-sm text-ink">
            <Sparkles size={18} className="mt-0.5 shrink-0 text-gold-600" />
            <p className="font-medium">{result.level_message}</p>
          </div>
        )}

        <div className="flex items-start gap-2 rounded-xl bg-paper p-4 text-sm text-ink-soft">
          <TrendingUp size={18} className="mt-0.5 shrink-0 text-teal-600" />
          <p>
            Reading level: <strong className="text-ink">{result.level.label}</strong>.{" "}
            {result.level.progress_text}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-xl border border-teal-100 bg-paper p-4">
      <p className="text-sm font-medium text-ink">How did that feel?</p>
      <div className="grid gap-2 sm:grid-cols-3">
        {RATINGS.map((r) => (
          <button
            key={r.value}
            type="button"
            onClick={() => setRating(r.value)}
            className={`rounded-xl border px-3 py-2 text-left text-sm transition ${
              rating === r.value
                ? "border-teal-600 bg-teal-600 text-white"
                : "border-teal-100 bg-white text-ink hover:border-teal-400"
            }`}
          >
            <span className="block font-semibold">{r.label}</span>
            <span className={`text-xs ${rating === r.value ? "text-teal-50" : "text-ink-soft"}`}>
              {r.hint}
            </span>
          </button>
        ))}
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button
        type="button"
        onClick={save}
        disabled={!rating || saving}
        className="flex items-center gap-2 rounded-full bg-teal-600 px-5 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <CheckCircle2 size={16} />
        {saving ? "Saving..." : "Save & see my result"}
      </button>
    </div>
  );
}
