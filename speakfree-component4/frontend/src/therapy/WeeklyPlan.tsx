import { useEffect, useState } from "react";
import { HelpCircle, ListChecks, Play } from "lucide-react";
import { getWeeklyPlan } from "./therapyApi";
import { usePracticeHistory } from "../context/PracticeHistoryContext";
import { WeeklyPlanResponse } from "../types/therapy";

const SOURCE_LABELS: Record<string, { label: string; className: string }> = {
  therapist: { label: "Assigned by therapist", className: "bg-gold-400/20 text-gold-600" },
  level: { label: "Your reading level", className: "bg-teal-100 text-teal-800" },
  bandit: { label: "Chosen by adaptive engine", className: "bg-paper text-ink-soft border border-teal-100" },
  words: { label: "Your word level", className: "bg-gold-400/20 text-gold-600" },
};

/** The bandit's uncertainty term (α·√(xᵀA⁻¹x), on the score scale) shrinks as an
 *  exercise is practised; shown as a plain confidence level. */
function confidenceLabel(uncertainty: number | null) {
  if (uncertainty === null) return "";
  if (uncertainty > 60) return "low confidence";
  if (uncertainty > 30) return "medium confidence";
  return "high confidence";
}

const TYPE_LABELS: Record<string, string> = {
  reading: "Reading",
  pacing: "Pacing",
  daf: "DAF",
  picture: "Picture",
  words: "Words",
  roleplay: "Role-play",
};

interface WeeklyPlanProps {
  onStart: (exerciseId: string) => void;
}

export default function WeeklyPlan({ onStart }: WeeklyPlanProps) {
  const { userId, version } = usePracticeHistory();
  const [plan, setPlan] = useState<WeeklyPlanResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    setError(false);
    getWeeklyPlan(userId)
      .then((data) => active && setPlan(data))
      .catch(() => active && setError(true));
    return () => {
      active = false;
    };
  }, [userId, version]);

  if (error) {
    return (
      <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-ink">
        We couldn't load your plan. Check that the therapy service is running.
      </p>
    );
  }
  if (!plan) return <p className="text-sm text-ink-soft">Building your plan...</p>;

  return (
    <div className="rounded-2xl border border-teal-100 bg-white p-6">
      <div className="flex items-center gap-2">
        <ListChecks className="text-teal-600" size={18} />
        <h3 className="font-display font-semibold text-ink">This Week's Plan</h3>
      </div>
      <p className="mt-1 text-sm text-ink-soft">
        Chosen for you by the adaptive learning engine from your own results. It updates
        every time you save an exercise.
      </p>
      <div className="mt-4 rounded-xl border border-teal-100 bg-teal-50/60 px-4 py-3">
        <p className="flex items-center gap-1.5 text-sm font-semibold text-ink">
          <HelpCircle size={15} className="text-teal-600" />
          Why this plan for you?
        </p>
        <ul className="mt-1.5 list-disc space-y-0.5 pl-5 text-sm text-ink">
          {plan.why.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </div>
      <ol className="mt-4 space-y-3">
        {plan.exercises.map((ex, i) => (
          <li key={ex.id} className="rounded-xl bg-paper px-4 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-teal-600 text-xs font-semibold text-white">
                  {i + 1}
                </span>
                <span className="text-sm font-medium text-ink">{ex.title}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-teal-100 px-2.5 py-1 text-xs font-medium text-teal-700">
                  {TYPE_LABELS[ex.type] ?? ex.type} · Level {ex.difficulty}
                </span>
                <button
                  onClick={() => onStart(ex.id)}
                  className="flex items-center gap-1 rounded-full bg-teal-600 px-3 py-1 text-xs font-medium text-white hover:bg-teal-700"
                >
                  <Play size={12} />
                  Start
                </button>
              </div>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${SOURCE_LABELS[ex.source].className}`}>
                {SOURCE_LABELS[ex.source].label}
              </span>
              <span className="text-xs text-ink-soft">
                {ex.predicted_score !== null
                  ? `Predicted score ≈ ${ex.predicted_score} · ${confidenceLabel(ex.uncertainty)} · practised ${ex.times_practised}×`
                  : "Not tried yet — the engine is exploring it"}
              </span>
            </div>
            <p className="mt-2 text-sm text-ink">{ex.explanation}</p>
            {ex.source === "bandit" && <p className="mt-1 text-xs text-ink-soft">{ex.reason}</p>}
          </li>
        ))}
      </ol>

      <details className="mt-5 rounded-xl bg-paper p-4 text-sm text-ink-soft">
        <summary className="cursor-pointer font-medium text-ink">How the plan is chosen</summary>
        <p className="mt-2">
          Exercises your therapist assigned come first, then the reading passage for your current level.
          The rest are chosen by a LinUCB contextual bandit that learns from your own scores: for each
          exercise it predicts your score and how unsure it is, then picks the best predicted score plus
          uncertainty. Exercises you haven't tried get a large uncertainty, so the plan keeps exploring
          instead of repeating the same thing.
        </p>
        <p className="mt-2">
          Your current context: level {Math.round(plan.context.level * 2) + 1} of 3 · recent average{" "}
          {plan.context.recent_average} · trend {plan.context.trend > 0 ? "+" : ""}
          {plan.context.trend} · comfort {plan.context.comfort}%.
        </p>
      </details>
    </div>
  );
}
