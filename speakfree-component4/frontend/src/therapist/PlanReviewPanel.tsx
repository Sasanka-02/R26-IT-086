import { useState } from "react";
import { PlanReview, PlanVerdict, StudentDetail } from "../types/therapist";
import { reviewPlan } from "./therapistApi";
import { formatDate, Panel } from "./ui";

const VERDICTS: { key: PlanVerdict; label: string; className: string }[] = [
  { key: "appropriate", label: "Appropriate", className: "border-teal-600 text-teal-700 hover:bg-teal-50" },
  { key: "partly", label: "Partly appropriate", className: "border-gold-400 text-gold-600 hover:bg-gold-400/10" },
  { key: "not_appropriate", label: "Not appropriate", className: "border-red-600 text-red-700 hover:bg-red-600/10" },
];

const VERDICT_LABEL: Record<PlanVerdict, string> = {
  appropriate: "Appropriate",
  partly: "Partly appropriate",
  not_appropriate: "Not appropriate",
};

const SOURCE_LABEL: Record<string, string> = {
  therapist: "Assigned",
  level: "Reading level",
  bandit: "Adaptive engine",
};

/** Expert validation of the adaptive output: the therapist judges the plan
 *  the engine generated for this student right now. */
export default function PlanReviewPanel({
  email,
  plan,
  reviews,
  onSaved,
}: {
  email: string;
  plan: StudentDetail["plan"];
  reviews: PlanReview[];
  onSaved: () => void;
}) {
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);

  const submit = async (verdict: PlanVerdict) => {
    setSaving(true);
    setError(false);
    try {
      await reviewPlan(email, verdict, note);
      setNote("");
      onSaved();
    } catch {
      setError(true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Panel
      title="Validate this week's plan"
      subtitle="Is the plan the adaptive engine generated for this student clinically appropriate? Your judgement is saved with a copy of the plan and reported on the evidence page."
    >
      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <ul className="space-y-1.5 text-sm text-ink">
            {plan.why.map((line) => (
              <li key={line} className="text-ink-soft">{line}</li>
            ))}
          </ul>
          <ol className="mt-3 space-y-2">
            {plan.exercises.map((ex, i) => (
              <li key={ex.id} className="rounded-xl bg-paper px-3 py-2 text-sm">
                <span className="font-medium text-ink">
                  {i + 1}. {ex.title}
                </span>{" "}
                <span className="text-xs text-ink-soft">· {SOURCE_LABEL[ex.source]}</span>
                <span className="block text-xs text-ink-soft">{ex.explanation}</span>
              </li>
            ))}
          </ol>
        </div>
        <div className="no-print">
          <label className="text-xs font-medium text-ink-soft" htmlFor="plan-note">
            Note (optional) — e.g. what you would change
          </label>
          <textarea
            id="plan-note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={3}
            maxLength={2000}
            className="mt-1 w-full rounded-xl border border-teal-100 bg-white px-3 py-2 text-sm text-ink"
          />
          <div className="mt-2 flex flex-wrap gap-2">
            {VERDICTS.map((v) => (
              <button
                key={v.key}
                disabled={saving}
                onClick={() => submit(v.key)}
                className={`rounded-full border px-3 py-1.5 text-sm font-medium disabled:opacity-50 ${v.className}`}
              >
                {v.label}
              </button>
            ))}
          </div>
          {error && <p className="mt-2 text-sm text-red-700">Couldn't save the review. Try again.</p>}
          {reviews.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-semibold text-ink-soft">Earlier reviews of this student's plans</p>
              <ul className="mt-1 space-y-1 text-sm">
                {reviews.map((r) => (
                  <li key={r.id} className="text-ink">
                    {VERDICT_LABEL[r.verdict]}
                    <span className="text-xs text-ink-soft">
                      {" "}
                      · {r.plan.level} · {formatDate(r.at, true)} · {r.by}
                      {r.source === "synthetic" ? " (demo account — synthetic)" : ""}
                    </span>
                    {r.note && <span className="block text-xs text-ink-soft">“{r.note}”</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </Panel>
  );
}
