import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download } from "lucide-react";
import { CohortReport, EvidenceReport, FitMetrics, SourceValidation } from "../types/therapist";
import { downloadPilotSheet, downloadRatingsSheet, getCohortReport, getEvidence } from "./therapistApi";
import { AgreementScatter, HorizontalBars, MultiLineChart } from "./charts";
import { formatDate, Panel, StatTile } from "./ui";
import AppShell from "../components/AppShell";

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

function SourceBlock({
  v,
  ratings,
}: {
  v: SourceValidation | null;
  ratings: EvidenceReport["ratings"];
}) {
  if (!v) {
    return (
      <p className="rounded-xl bg-paper p-4 text-sm text-ink-soft">
        {ratings.length === 1 ? "Only 1 rating so far — at least 2 are needed." : "No ratings from this source yet."}
      </p>
    );
  }
  const best = v.calibrated_model_loo ?? v.shown_scores;
  const sm = v.strong_match;
  const ir = v.inter_rater;
  return (
    <>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Ratings" value={v.n} hint={`${v.n_heard_audio} rated while listening to the recording`} />
        <StatTile
          label="Mean absolute error"
          value={best.mae}
          hint={v.calibrated_model_loo ? "calibrated model, leave-one-out" : "scores students saw"}
        />
        <StatTile label="Pearson r" value={best.pearson_r ?? "—"} hint="1 = perfect agreement" />
        <StatTile label="Within ±15 points" value={`${best.within_15}%`} />
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div>
          <p className="text-sm font-medium text-ink">App score vs expert score</p>
          <p className="text-xs text-ink-soft">Each dot is one rated attempt; the diagonal line is perfect agreement.</p>
          <AgreementScatter
            data={ratings.map((r) => ({ auto: r.auto_score, expert: r.expert_score, title: r.title }))}
          />
        </div>
        <div className="space-y-4">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm tabular-nums">
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
                <MetricsRow label="Scores students saw" m={v.shown_scores} />
                <MetricsRow label="Starting-value model" m={v.prior_model} />
                <MetricsRow
                  label="Calibrated model"
                  m={v.calibrated_model_loo}
                  note="Leave-one-out: each rating is predicted by a model fitted without it"
                />
              </tbody>
            </table>
          </div>
          <div className="rounded-xl bg-paper px-4 py-3 text-sm">
            <p className="font-semibold text-ink">Does “strong” match the expert's 4–5?</p>
            <p className="mt-1 text-ink">
              {sm.accuracy}% agreement on {sm.n} attempts (strong = score ≥ {sm.threshold}).
            </p>
            <p className="mt-0.5 text-xs text-ink-soft">
              Expert rated {sm.expert_good} as 4–5; the app called {sm.flagged_strong} strong. Sensitivity{" "}
              {sm.sensitivity ?? "—"}% · specificity {sm.specificity ?? "—"}% · based on the {sm.based_on}.
            </p>
          </div>
          <div className="rounded-xl bg-paper px-4 py-3 text-sm">
            <p className="font-semibold text-ink">Agreement between two raters</p>
            {ir.n_pairs === 0 ? (
              <p className="mt-1 text-xs text-ink-soft">
                Needs a second rater: a second therapist account rates the same attempts on the student pages.
              </p>
            ) : (
              <>
                <p className="mt-1 text-ink">
                  Cohen's kappa {ir.kappa ?? "—"} · weighted kappa {ir.weighted_kappa ?? "—"}
                </p>
                <p className="mt-0.5 text-xs text-ink-soft">
                  {ir.n_pairs} attempts rated twice · exact agreement {ir.exact_agreement}% · within one point{" "}
                  {ir.within_one}%. Weighted kappa uses quadratic weights (a 4-vs-5 disagreement costs less than
                  1-vs-5).
                </p>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

function ExpertValidation({ scoring, ratings }: Pick<EvidenceReport, "scoring" | "ratings">) {
  const [sheetError, setSheetError] = useState(false);
  const clinician = ratings.filter((r) => r.source === "clinician");
  const synthetic = ratings.filter((r) => r.source === "synthetic");
  const real = scoring.n_clinician > 0;
  return (
    <Panel
      title="1 · Expert validation of the score"
      subtitle="Therapists rate attempts 1–5 on each student's page. Every rating is compared with the app's score. Real clinician ratings and synthetic test data are always reported separately."
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div
          className={`max-w-3xl rounded-xl border px-4 py-3 text-sm text-ink ${
            real ? "border-teal-200 bg-teal-50/60" : "border-amber-200 bg-amber-50"
          }`}
          role="note"
        >
          {real ? (
            <>
              <strong>Scoring model fitted on {scoring.n_clinician} real clinician ratings.</strong> Synthetic ratings
              are left out of fitting and shown separately below.{" "}
              {scoring.active === "prior" &&
                `Starting values stay in use until ${scoring.min_ratings} clinician ratings exist.`}
            </>
          ) : (
            <>
              <strong>No clinician ratings yet.</strong> The results below use synthetic ratings generated by the demo
              seed script to test the pipeline. They are not expert validation. Ratings from a speech-language
              pathologist replace them automatically.
            </>
          )}
        </div>
        <button
          onClick={() => downloadRatingsSheet().catch(() => setSheetError(true))}
          className="no-print flex items-center gap-1.5 rounded-full border border-teal-200 px-4 py-1.5 text-sm font-medium text-teal-700 hover:bg-teal-50"
        >
          <Download size={14} />
          Rating sheet (CSV)
        </button>
      </div>
      {sheetError && <p className="mt-2 text-sm text-red-700">Couldn't download the rating sheet.</p>}

      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Clinician ratings" value={scoring.n_clinician} hint={`${scoring.min_ratings} needed to calibrate`} />
        <StatTile label="Synthetic ratings" value={scoring.n_synthetic} hint="seed script · pipeline testing only" />
        <StatTile
          label="Scoring model in use"
          value={scoring.active === "calibrated" ? "Calibrated" : "Starting values"}
          hint={scoring.data_source ? `fitted on ${scoring.data_source} ratings` : undefined}
        />
        <StatTile label="Last fitted" value={scoring.fitted_at ? formatDate(scoring.fitted_at) : "—"} />
      </div>

      <h3 className="mt-6 text-sm font-semibold text-ink">Real clinician ratings</h3>
      <div className="mt-2">
        {clinician.length === 0 ? (
          <p className="rounded-xl bg-paper p-4 text-sm text-ink-soft">
            None yet. Log in with a real therapist account and run a{" "}
            <Link to="/therapist/validation" className="font-medium text-teal-600 hover:underline">
              Validation session
            </Link>{" "}
            — a volunteer practises on this device and the SLP listens and rates each attempt. Results appear here
            immediately.
          </p>
        ) : (
          <SourceBlock v={scoring.validation_by_source.clinician} ratings={clinician} />
        )}
      </div>

      {synthetic.length > 0 && (
        <details className="mt-6 rounded-xl border border-dashed border-amber-200 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-ink">
            Synthetic data for pipeline testing ({synthetic.length} ratings) — not expert validation
          </summary>
          <p className="mb-3 mt-2 text-xs text-ink-soft">
            Made by a formula in scripts/seed_demo.py (and by @demo.local accounts). These only show that rating →
            calibration → evidence works end to end.
          </p>
          <SourceBlock v={scoring.validation_by_source.synthetic} ratings={synthetic} />
        </details>
      )}
    </Panel>
  );
}

function PlanValidation({ plan }: { plan: EvidenceReport["plan_validation"] }) {
  const stats = plan.clinician.n > 0 ? plan.clinician : null;
  return (
    <Panel
      title="4 · Expert validation of the adaptive plan"
      subtitle="A therapist judges the weekly plan generated for each student as appropriate, partly appropriate or not appropriate (from the student's page). Aim for 10+ plans across different students."
    >
      {stats ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatTile label="Plans reviewed" value={stats.n} hint={`${stats.students} students`} />
          <StatTile label="Judged appropriate" value={`${stats.appropriate_pct}%`} hint={`${stats.counts.appropriate} plans`} />
          <StatTile label="Appropriate or partly" value={`${stats.acceptable_pct}%`} hint={`${stats.counts.partly} partly`} />
          <StatTile label="Not appropriate" value={stats.counts.not_appropriate} />
        </div>
      ) : (
        <p className="rounded-xl bg-paper p-4 text-sm text-ink-soft">
          No clinician plan reviews yet. Open a student and use <strong>Validate this week's plan</strong>.
        </p>
      )}
      {plan.synthetic.n > 0 && (
        <p className="mt-3 text-xs text-ink-soft">
          Left out: {plan.synthetic.n} review{plan.synthetic.n === 1 ? "" : "s"} from demo accounts (synthetic).
        </p>
      )}
      {plan.recent.length > 0 && (
        <ul className="mt-4 space-y-1 text-sm">
          {plan.recent.map((r) => (
            <li key={r.at} className="text-ink">
              {plan.labels[r.verdict]}
              <span className="text-xs text-ink-soft">
                {" "}
                · {r.student} · {r.level} · {formatDate(r.at)}
                {r.source === "synthetic" ? " · synthetic" : ""}
              </span>
              {r.note && <span className="block text-xs text-ink-soft">“{r.note}”</span>}
            </li>
          ))}
        </ul>
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
  const live = adaptive.summary.find((s) => s.strategy === "linucb");
  const hybrid = adaptive.summary.find((s) => s.strategy === "hybrid");
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
      {live && hybrid && (
        <div className="mt-4 space-y-2 rounded-xl bg-paper px-4 py-3 text-sm text-ink">
          <p>
            <strong>Limitation:</strong> after {adaptive.rounds} sessions the live engine settles on each student's best
            exercise only {live.best_exercise_rate}% of the time. Its reward is still rising in the curve above, so it
            needs more sessions per student to converge; regret is already about half of a fixed plan's.
          </p>
          <p>
            <strong>Candidate improvement:</strong> adding exercise features (type and difficulty) lets evidence from
            one exercise inform similar ones. In this simulation it picks the best exercise {hybrid.best_exercise_rate}%
            of the time (vs {live.best_exercise_rate}%), with regret {hybrid.cumulative_regret} vs{" "}
            {live.cumulative_regret}. On other simulated cohorts its regret was slightly higher, so it is reported here
            rather than switched on. α was tuned for both on separate simulated students.
          </p>
        </div>
      )}
    </Panel>
  );
}

function AssistantEvaluation({ assistant }: Pick<EvidenceReport, "assistant">) {
  return (
    <Panel
      title="5 · Assistant intent classifier"
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

function UsabilityEvaluation({ usability }: Pick<EvidenceReport, "usability">) {
  const { overall, by_role, benchmark } = usability;
  return (
    <Panel
      title="6 · Usability (System Usability Scale)"
      subtitle={`Standard 10-item SUS questionnaire, scored 0–100. ${benchmark} is the commonly used average benchmark. Students are invited after 3 exercises; therapists can respond from the portal.`}
    >
      {overall.n === 0 ? (
        <p className="rounded-xl bg-paper p-4 text-sm text-ink-soft">
          No responses yet. Ask testers to complete a few exercises — the survey invitation appears on their
          Practice tab — and ask therapists to use the card at the top of the portal.
        </p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatTile
              label="Average SUS score"
              value={overall.mean ?? "—"}
              hint={`${overall.band} · ${overall.mean !== null && overall.mean >= benchmark ? "above" : "below"} the ${benchmark} benchmark`}
            />
            <StatTile
              label="95% confidence interval"
              value={overall.ci95 ? `${overall.ci95[0]}–${overall.ci95[1]}` : "—"}
              hint={overall.ci95 ? `SD ${overall.sd}` : "needs 2+ responses"}
            />
            <StatTile label="Student responses" value={by_role.student.n} hint={by_role.student.mean !== null ? `mean ${by_role.student.mean}` : undefined} />
            <StatTile label="Therapist responses" value={by_role.therapist.n} hint={by_role.therapist.mean !== null ? `mean ${by_role.therapist.mean}` : undefined} />
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm tabular-nums">
              <thead className="text-xs text-ink-soft">
                <tr className="border-b border-teal-100">
                  <th className="py-2 pr-3 font-medium">#</th>
                  <th className="py-2 pr-3 font-medium">Statement</th>
                  <th className="py-2 text-right font-medium">Mean answer (1–5)</th>
                </tr>
              </thead>
              <tbody>
                {usability.items.map((item) => (
                  <tr key={item.number} className="border-b border-teal-50 last:border-0">
                    <td className="py-2 pr-3 text-ink-soft">{item.number}</td>
                    <td className="py-2 pr-3 text-ink">
                      {item.text}
                      <span className="block text-xs text-ink-soft">
                        {item.positive ? "Positive statement — higher is better" : "Negative statement — lower is better"}
                      </span>
                    </td>
                    <td className="py-2 text-right font-semibold text-ink">{item.mean_answer ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {usability.comments.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium text-ink">Comments</p>
              <ul className="mt-2 space-y-2">
                {usability.comments.map((c) => (
                  <li key={c.submitted_at} className="rounded-lg bg-paper px-3 py-2 text-sm">
                    <p className="text-ink">“{c.comment}”</p>
                    <p className="text-xs text-ink-soft">
                      {c.role} · SUS {c.score} · {formatDate(c.submitted_at)}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </Panel>
  );
}

function PilotStudy({ pilot }: { pilot: EvidenceReport["pilot"] }) {
  const [sheetError, setSheetError] = useState(false);
  const s = pilot.summary;
  const pText =
    s.sign_test_p === null ? "—" : s.sign_test_p < 0.001 ? "< 0.001" : String(s.sign_test_p);
  return (
    <Panel
      title="7 · Pilot study — first week vs last week"
      subtitle={`Real users only (demo accounts excluded). First week = the ${pilot.rules.week_days} days from a participant's first practice; last week = the ${pilot.rules.week_days} days up to their latest. Included after ${pilot.rules.min_span_days}+ days of practice with ${pilot.rules.min_attempts_per_week}+ attempts in each week.`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <p className="max-w-3xl text-sm text-ink-soft">
          Ask 5–10 people to practise for 1–2 weeks. Results fill in automatically; report the mean change with its
          95% confidence interval, how many improved (sign test), and the SUS score in §6.
        </p>
        <button
          onClick={() => downloadPilotSheet().catch(() => setSheetError(true))}
          className="no-print flex items-center gap-1.5 rounded-full border border-teal-200 px-4 py-1.5 text-sm font-medium text-teal-700 hover:bg-teal-50"
        >
          <Download size={14} />
          Pilot data (CSV)
        </button>
      </div>
      {sheetError && <p className="mt-2 text-sm text-red-700">Couldn't download the pilot data.</p>}

      {s.participants === 0 ? (
        <p className="mt-4 rounded-xl bg-paper p-4 text-sm text-ink-soft">
          No participants with a full first and last week yet
          {s.not_yet_included > 0 ? ` (${s.not_yet_included} real user${s.not_yet_included === 1 ? " is" : "s are"} still practising)` : ""}.
        </p>
      ) : (
        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatTile label="Participants" value={s.participants} hint={s.not_yet_included ? `${s.not_yet_included} more still practising` : undefined} />
          <StatTile
            label="Average score"
            value={`${s.mean_first} → ${s.mean_last}`}
            hint="first week → last week"
          />
          <StatTile
            label="Mean change"
            value={`${(s.mean_change ?? 0) > 0 ? "+" : ""}${s.mean_change} pts`}
            hint={s.ci95 ? `95% CI ${s.ci95[0]} to ${s.ci95[1]}` : "CI needs 2+ participants"}
          />
          <StatTile
            label="Improved"
            value={`${s.improved} of ${s.participants}`}
            hint={`sign test p = ${pText}`}
          />
        </div>
      )}

      {pilot.participants.length > 0 && (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm tabular-nums">
            <thead className="text-xs text-ink-soft">
              <tr className="border-b border-teal-100">
                <th className="py-2 pr-3 font-medium">Participant</th>
                <th className="py-2 pr-3 text-right font-medium">Days</th>
                <th className="py-2 pr-3 text-right font-medium">First week</th>
                <th className="py-2 pr-3 text-right font-medium">Last week</th>
                <th className="py-2 pr-3 text-right font-medium">Change</th>
                <th className="py-2 text-right font-medium">Long pauses / reading</th>
              </tr>
            </thead>
            <tbody>
              {pilot.participants.map((p) => (
                <tr key={p.student} className={`border-b border-teal-50 last:border-0 ${p.included ? "" : "opacity-60"}`}>
                  <td className="py-2 pr-3 text-ink">
                    {p.name}
                    {!p.included && <span className="block text-xs text-ink-soft">Not yet included — {p.reason}</span>}
                  </td>
                  <td className="py-2 pr-3 text-right text-ink">{p.span_days}</td>
                  <td className="py-2 pr-3 text-right text-ink">
                    {p.first_week_score} <span className="text-xs text-ink-soft">({p.first_week_attempts})</span>
                  </td>
                  <td className="py-2 pr-3 text-right text-ink">
                    {p.last_week_score} <span className="text-xs text-ink-soft">({p.last_week_attempts})</span>
                  </td>
                  <td className={`py-2 pr-3 text-right font-semibold ${p.change > 0 ? "text-teal-600" : p.change < 0 ? "text-red-700" : "text-ink"}`}>
                    {p.change > 0 ? "+" : ""}
                    {p.change}
                  </td>
                  <td className="py-2 text-right text-ink">
                    {p.first_week_pauses ?? "—"} → {p.last_week_pauses ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-ink-soft">
            Numbers in brackets are attempts in that week. With under 14 days of practice the two weeks overlap;
            shared attempts count in both, which makes the change estimate conservative.
          </p>
        </div>
      )}
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
      title="8 · Shareable cohort report (differential privacy)"
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
    <AppShell>
      <main className="mx-auto max-w-6xl space-y-6">
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
            <PlanValidation plan={evidence.plan_validation} />
            <AssistantEvaluation assistant={evidence.assistant} />
            <UsabilityEvaluation usability={evidence.usability} />
            <PilotStudy pilot={evidence.pilot} />
          </>
        )}
        <PrivateCohortReport />
      </main>
    </AppShell>
  );
}
