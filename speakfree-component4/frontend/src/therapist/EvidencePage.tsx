import { useEffect, useState } from "react";
import { CohortReport, EvidenceReport, FitMetrics } from "../types/therapist";
import { getCohortReport, getEvidence } from "./therapistApi";
import { AgreementScatter, HorizontalBars, MultiLineChart } from "./charts";
import { formatDate, Panel, PortalHeader, StatTile } from "./ui";

function MetricsRow({ label, m, note }: { label: string; m: FitMetrics | null; note?: string }) {
  return (
    <tr className="border-b border-teal-50 last:border-0">
      <td className="py-2 pr-3 text-ink">
        {label}
        {note && <span className="block text-xs text-ink-soft">{note}</span>}
      </td>
      <td className="py-2 pr-3 text-right text-ink">{m ? m.mae : "—"}</td>
      <td className="py-2 pr-3 text-right text-ink">{m ? m.rmse : "—"}</td>
      <td className="py-2 pr-3 text-right text-ink">{m?.pearson_r ?? "—"}</td>
      <td className="py-2 text-right text-ink">{m ? `${m.within_15}%` : "—"}</td>
    </tr>
  );
}

function ExpertValidation({ scoring, ratings }: Pick<EvidenceReport, "scoring" | "ratings">) {
  const v = scoring.validation;
  return (
    <Panel
      title="1 · Expert validation of the score"
      subtitle="Therapists rate attempts 1–5 on each student's page. Every rating is compared with the app's score."
    >
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Expert ratings collected" value={scoring.n_ratings} hint={`${scoring.min_ratings} needed to calibrate`} />
        <StatTile
          label="Scoring model in use"
          value={scoring.active === "calibrated" ? "Calibrated" : "Starting values"}
          hint={scoring.fitted_at ? `updated ${formatDate(scoring.fitted_at, true)}` : undefined}
        />
        <StatTile label="Mean error (shown scores)" value={v ? v.shown_scores.mae : "—"} hint="points out of 100" />
        <StatTile label="Correlation with therapist" value={v?.shown_scores.pearson_r ?? "—"} hint="Pearson r (1 = perfect)" />
      </div>

      {ratings.length === 0 ? (
        <p className="mt-4 rounded-xl bg-paper p-4 text-sm text-ink-soft">
          No expert ratings yet. Open a student, then use the <strong>Expert rating</strong> column in “All work”
          to rate attempts. Results appear here immediately.
        </p>
      ) : (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div>
            <p className="text-sm font-medium text-ink">App score vs therapist score</p>
            <p className="text-xs text-ink-soft">Each dot is one rated attempt; the diagonal line is perfect agreement.</p>
            <AgreementScatter
              data={ratings.map((r) => ({ auto: r.auto_score, expert: r.expert_score, title: r.title }))}
            />
          </div>
          <div className="overflow-x-auto">
            <p className="text-sm font-medium text-ink">Agreement with the therapist</p>
            <table className="mt-2 w-full text-left text-sm tabular-nums">
              <thead className="text-xs text-ink-soft">
                <tr className="border-b border-teal-100">
                  <th className="py-2 pr-3 font-medium">Model</th>
                  <th className="py-2 pr-3 text-right font-medium">MAE</th>
                  <th className="py-2 pr-3 text-right font-medium">RMSE</th>
                  <th className="py-2 pr-3 text-right font-medium">r</th>
                  <th className="py-2 text-right font-medium">Within ±15</th>
                </tr>
              </thead>
              <tbody>
                <MetricsRow label="Scores students saw" m={v?.shown_scores ?? null} />
                <MetricsRow label="Starting-value model" m={v?.prior_model ?? null} />
                <MetricsRow
                  label="Calibrated model"
                  m={v?.calibrated_model_loo ?? null}
                  note="Leave-one-out: each rating is predicted by a model fitted without it"
                />
              </tbody>
            </table>
            <p className="mt-2 text-xs text-ink-soft">
              MAE = mean absolute error, RMSE = root-mean-square error (lower is better).
            </p>
          </div>
        </div>
      )}
    </Panel>
  );
}

function Constants({ scoring }: Pick<EvidenceReport, "scoring">) {
  return (
    <Panel
      title="2 · Where the score's constants come from"
      subtitle={`score = Σ weight × factor (clipped to 0–100). Weights start from documented values and are re-estimated from expert ratings by ridge regression (λ = ${scoring.ridge_lambda ?? 4}) once ${scoring.min_ratings} ratings exist.`}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm tabular-nums">
          <thead className="text-xs text-ink-soft">
            <tr className="border-b border-teal-100">
              <th className="py-2 pr-3 font-medium">Factor</th>
              <th className="py-2 pr-3 text-right font-medium">Starting weight</th>
              <th className="py-2 pr-3 text-right font-medium">Current weight</th>
              <th className="py-2 text-right font-medium">Change from evidence</th>
            </tr>
          </thead>
          <tbody>
            {scoring.features.map((f) => {
              const change = Math.round((f.current - f.prior) * 10) / 10;
              return (
                <tr key={f.feature} className="border-b border-teal-50 last:border-0">
                  <td className="py-2 pr-3 text-ink">{f.label}</td>
                  <td className="py-2 pr-3 text-right text-ink-soft">{f.prior}</td>
                  <td className="py-2 pr-3 text-right font-semibold text-ink">{f.current}</td>
                  <td className="py-2 text-right text-ink-soft">{change === 0 ? "—" : (change > 0 ? "+" : "") + change}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {(["strong", "weak"] as const).map((k) => (
          <div key={k} className="rounded-xl bg-paper px-4 py-3 text-sm">
            <p className="font-semibold text-ink">
              “{k === "strong" ? "Strong" : "Difficult"}” threshold: {scoring.thresholds[k]}
              <span className="font-normal text-ink-soft"> (starting value {scoring.prior_thresholds[k]})</span>
            </p>
            <p className="mt-1 text-xs text-ink-soft">
              {scoring.threshold_accuracy[k] !== null
                ? `Chosen as the cut-off that best matches therapist judgements — ${scoring.threshold_accuracy[k]}% balanced accuracy.`
                : "Needs at least 3 rated attempts on each side before it is learned from ratings."}
            </p>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function AdaptiveEvaluation({ adaptive }: Pick<EvidenceReport, "adaptive">) {
  const series = Object.entries(adaptive.labels).map(([key, label]) => ({ key, label }));
  return (
    <Panel
      title="3 · Adaptive learning engine (LinUCB) — simulation"
      subtitle={`${adaptive.students} simulated students with known best exercises, ${adaptive.rounds} sessions each (seed ${adaptive.seed}, reproducible). Same noise for every strategy.`}
    >
      <MultiLineChart
        data={adaptive.curves}
        xKey="round"
        series={series}
        unit="reward"
        xFormatter={(v) => `Session ${v}`}
      />
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm tabular-nums">
          <thead className="text-xs text-ink-soft">
            <tr className="border-b border-teal-100">
              <th className="py-2 pr-3 font-medium">Strategy</th>
              <th className="py-2 pr-3 text-right font-medium">Avg reward</th>
              <th className="py-2 pr-3 text-right font-medium">Last 10 sessions</th>
              <th className="py-2 pr-3 text-right font-medium">Regret (lower better)</th>
              <th className="py-2 text-right font-medium">Picks best exercise</th>
            </tr>
          </thead>
          <tbody>
            {adaptive.summary.map((s) => (
              <tr key={s.strategy} className="border-b border-teal-50 last:border-0">
                <td className="py-2 pr-3 font-medium text-ink">{s.label}</td>
                <td className="py-2 pr-3 text-right text-ink">{s.average_reward}</td>
                <td className="py-2 pr-3 text-right text-ink">{s.final_10_reward}</td>
                <td className="py-2 pr-3 text-right text-ink">{s.cumulative_regret}</td>
                <td className="py-2 text-right text-ink">{s.best_exercise_rate}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function AssistantEvaluation({ assistant }: Pick<EvidenceReport, "assistant">) {
  return (
    <Panel
      title="4 · Assistant intent classifier"
      subtitle="Multinomial Naive Bayes on normalised words, evaluated by leave-one-out cross-validation."
    >
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Cross-validated accuracy" value={`${assistant.accuracy}%`} />
        <StatTile label="Intents" value={assistant.intents} />
        <StatTile label="Labelled examples" value={assistant.examples} />
        <StatTile
          label="Confidence threshold"
          value={assistant.confidence_threshold}
          hint="below this → language model or safe fallback"
        />
      </div>
    </Panel>
  );
}

function PrivateCohortReport() {
  const [epsilon, setEpsilon] = useState(1.0);
  const [report, setReport] = useState<CohortReport | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    getCohortReport(epsilon)
      .then((r) => {
        if (!active) return;
        setReport(r);
        setError(false);
      })
      .catch(() => active && setError(true));
    return () => {
      active = false;
    };
  }, [epsilon]);

  return (
    <Panel
      title="5 · Shareable cohort report (differential privacy)"
      subtitle="Statistics that leave the clinic are released with Laplace noise. Smaller ε = stronger privacy, more noise."
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-ink-soft">Privacy level ε:</span>
        {(report?.epsilon_options ?? [0.25, 0.5, 1, 2, 5]).map((e) => (
          <button
            key={e}
            onClick={() => setEpsilon(e)}
            className={`rounded-full border px-3 py-1 text-xs font-medium ${
              e === epsilon ? "border-teal-600 bg-teal-600 text-white" : "border-teal-100 text-ink-soft hover:border-teal-400"
            }`}
          >
            {e}
          </button>
        ))}
      </div>
      {error && <p className="mt-3 text-sm text-red-700">Couldn't load the cohort report.</p>}
      {report && (
        <>
          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <div>
              <p className="text-sm font-medium text-ink">Exercises by type (noisy)</p>
              <HorizontalBars data={report.by_type} labelKey="label" valueKey="value" unit="exercises" />
            </div>
            <div>
              <p className="text-sm font-medium text-ink">Students per level (noisy)</p>
              <HorizontalBars data={report.levels} labelKey="label" valueKey="value" unit="students" />
            </div>
            <div className="space-y-3">
              <StatTile label="Mean score (noisy)" value={report.mean_score} />
              <p className="text-xs text-ink-soft">
                ε = {report.epsilon} split over 4 statistic groups ({report.epsilon_per_group} each). Repeating the
                same request returns the same release, so noise cannot be averaged away.
              </p>
              <p className="text-xs text-ink-soft">
                Clinic budget used: {report.budget.epsilon_spent} of {report.budget.epsilon_threshold} ε.
              </p>
            </div>
          </div>
          <div className="mt-4 overflow-x-auto">
            <p className="text-sm font-medium text-ink">Privacy vs accuracy (expected error, 400 trials)</p>
            <table className="mt-2 w-full text-left text-sm tabular-nums">
              <thead className="text-xs text-ink-soft">
                <tr className="border-b border-teal-100">
                  <th className="py-2 pr-3 font-medium">ε</th>
                  <th className="py-2 pr-3 text-right font-medium">Count error (± exercises)</th>
                  <th className="py-2 text-right font-medium">Mean score error (± points)</th>
                </tr>
              </thead>
              <tbody>
                {report.accuracy.map((row) => (
                  <tr key={row.epsilon} className={`border-b border-teal-50 last:border-0 ${row.epsilon === epsilon ? "bg-teal-50/60" : ""}`}>
                    <td className="py-2 pr-3 text-ink">{row.epsilon}</td>
                    <td className="py-2 pr-3 text-right text-ink">{row.count_error}</td>
                    <td className="py-2 text-right text-ink">{row.mean_score_error}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Panel>
  );
}

export default function EvidencePage() {
  const [evidence, setEvidence] = useState<EvidenceReport | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    getEvidence()
      .then((e) => {
        if (!active) return;
        setEvidence(e);
        setError(false);
      })
      .catch(() => active && setError(true));
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="min-h-screen bg-paper">
      <PortalHeader />
      <main className="mx-auto max-w-6xl space-y-6 px-6 py-8">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold-600">Model evidence</p>
          <h1 className="mt-1 font-display text-3xl font-semibold text-ink">Validation &amp; evaluation</h1>
          <p className="mt-1 max-w-3xl text-sm text-ink-soft">
            How each part of the system is checked: the score against therapist ratings, where every constant
            comes from, how the adaptive engine compares with simpler strategies, how accurate the assistant is,
            and what privacy costs in accuracy.
          </p>
        </div>
        {error && (
          <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-ink" role="alert">
            We couldn't load the evidence report.
          </p>
        )}
        {!evidence && !error && <p className="text-sm text-ink-soft">Running evaluations...</p>}
        {evidence && (
          <>
            <ExpertValidation scoring={evidence.scoring} ratings={evidence.ratings} />
            <Constants scoring={evidence.scoring} />
            <AdaptiveEvaluation adaptive={evidence.adaptive} />
            <AssistantEvaluation assistant={evidence.assistant} />
          </>
        )}
        <PrivateCohortReport />
      </main>
    </div>
  );
}
