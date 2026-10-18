/**
 * EvidencePage (admin) – how well Component 4 works, measured:
 *   expert agreement (app score vs therapist 1–5 ratings) + ridge recalibration with leave-one-out,
 *   inter-rater agreement, plan reviews, System Usability Scale results, and the differentially
 *   private cohort report with its ε budget ledger. Federated learning is shown as a design only.
 */
import { useCallback, useEffect, useState } from "react";
import { ClipboardCheck, FlaskConical, Loader2, Network, ShieldCheck, Stethoscope, Users } from "lucide-react";
import { api } from "../../../api/client";
import { Bar, Card, COLORS, ErrorBox, Spinner } from "../../../components/ui";
import { HBars, StatTile } from "../../../components/charts";
import UsabilitySurvey from "../../../components/therapy/UsabilitySurvey";
import type { CohortReport, Evidence } from "../../../types/integration";

const fmt = (v: number | null | undefined, d = 1) => (v === null || v === undefined ? "–" : v.toFixed(d));

/** App score (y) against the therapist's rating (x); dashed line = perfect agreement. */
function AgreementScatter({ points }: { points: Evidence["scatter"] }) {
  const [hover, setHover] = useState<number | null>(null);
  if (points.length === 0) return <p className="text-sm muted">No rated attempts yet. Rate attempts 1–5 in a patient's therapy monitor.</p>;
  const W = 520, H = 260, L = 40, R = 14, T = 12, B = 32;
  const x = (r: number) => L + ((r - 1) / 4) * (W - L - R);
  const y = (s: number) => T + (1 - s / 100) * (H - T - B);
  const jitter = (i: number) => ((i * 37) % 11 - 5) * 3;
  const h = hover !== null ? points[hover] : null;
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="App score against therapist rating" onMouseLeave={() => setHover(null)}>
        {[0, 25, 50, 75, 100].map((v) => (
          <g key={v}><line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="#EEF0F7" /><text x={L - 6} y={y(v) + 3} textAnchor="end" fontSize={10} fill={COLORS.muted}>{v}</text></g>
        ))}
        {[1, 2, 3, 4, 5].map((r) => <text key={r} x={x(r)} y={H - 10} textAnchor="middle" fontSize={11} fill={COLORS.muted}>{r}</text>)}
        <line x1={x(1)} y1={y(0)} x2={x(5)} y2={y(100)} stroke={COLORS.muted} strokeDasharray="4 4" />
        {points.map((p, i) => (
          <circle key={i} cx={x(p.rating) + jitter(i)} cy={y(p.score)} r={hover === i ? 6 : 4.5} fill={COLORS.navy} stroke="#fff" strokeWidth={2}
            onMouseEnter={() => setHover(i)} />
        ))}
      </svg>
      <div className="mt-1 flex justify-between text-xs muted"><span>↑ app practice score</span><span>therapist rating (1–5) →</span></div>
      {h && (
        <div className="pointer-events-none absolute right-2 top-2 rounded-lg border border-line bg-white px-3 py-2 text-xs shadow-lift">
          <b className="text-ink">App {h.score} · therapist {h.rating}/5</b><div className="muted">{h.type}</div>
        </div>
      )}
    </div>
  );
}

function CohortCard() {
  const [eps, setEps] = useState(1);
  const [data, setData] = useState<CohortReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback((e: number) => {
    setBusy(true);
    setError(null);
    api.admin.cohort(e).then(setData).catch((err: Error) => setError(err.message)).finally(() => setBusy(false));
  }, []);
  useEffect(() => { load(1); }, [load]);

  return (
    <Card title="Differentially private cohort report" icon={<ShieldCheck size={18} className="text-navy" />}
      right={busy ? <Loader2 size={16} className="animate-spin text-brand" /> : undefined}>
      <p className="mb-3 text-sm text-ink-soft">Statistics across all patients, released with the Laplace mechanism (value + Lap(Δ/ε)). Asking again for the same data and ε returns the same release and spends no extra budget.</p>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold">ε =</span>
        {(data?.epsilon_options ?? [0.25, 0.5, 1, 2, 5]).map((o) => (
          <button key={o} onClick={() => { setEps(o); load(o); }} className={`chip ${o === eps ? "bg-navy text-white" : "bg-canvas text-ink-soft hover:bg-lav-100"}`}>{o}</button>
        ))}
        <span className="text-xs muted">smaller ε = more privacy, more noise</span>
      </div>
      <ErrorBox message={error} />
      {data && (
        <div className="space-y-5">
          <div>
            <div className="mb-1 flex justify-between text-xs font-semibold text-ink-soft"><span>Privacy budget (cohort releases)</span><span className="font-mono text-ink">ε {data.budget.epsilon_spent} / {data.budget.epsilon_threshold}</span></div>
            <Bar value={(data.budget.epsilon_spent / data.budget.epsilon_threshold) * 100} color={data.budget.exhausted ? COLORS.bad : COLORS.lav} className="h-2.5" />
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <StatTile label="Patients (exact)" value={data.patients} />
            <StatTile label="Mean score (noisy)" value={data.mean_score} />
            <StatTile label="ε per statistic group" value={data.epsilon_per_group} sub="4 groups (sequential composition)" />
          </div>
          <div className="grid gap-5 lg:grid-cols-3">
            <div><h3 className="mb-2 text-sm font-bold">Attempts by type</h3><HBars format={(v) => String(v)} data={data.by_type.filter((d) => d.value > 0).map((d) => ({ ...d }))} empty="All counts are zero after noise" /></div>
            <div><h3 className="mb-2 text-sm font-bold">Patients by practice level</h3><HBars format={(v) => String(v)} data={data.levels.map((d) => ({ ...d }))} /></div>
            <div><h3 className="mb-2 text-sm font-bold">Scores by band</h3><HBars format={(v) => String(v)} data={data.score_bands.map((d) => ({ ...d }))} /></div>
          </div>
          <p className="text-xs muted">{data.note}</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-line text-left text-xs uppercase tracking-wide muted"><th className="py-2">ε</th><th>Expected count error</th><th>Expected mean-score error</th></tr></thead>
              <tbody className="divide-y divide-line">{data.accuracy.map((a) => (
                <tr key={a.epsilon} className={a.epsilon === eps ? "bg-brand-soft/60" : ""}><td className="py-1.5 font-mono">{a.epsilon}</td><td className="font-mono">± {a.count_error}</td><td className="font-mono">± {a.mean_score_error}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      )}
    </Card>
  );
}

export default function EvidencePage() {
  const [ev, setEv] = useState<Evidence | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.admin.evidence().then(setEv).catch((e: Error) => setError(e.message)); }, []);
  if (error) return <ErrorBox message={error} />;
  if (!ev) return <Spinner />;
  const { agreement: ag, usability: sus, plan_reviews: pr } = ev;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-[28px] font-extrabold tracking-tight"><FlaskConical className="text-navy" /> Evidence & Validation</h1>
        <p className="text-sm text-ink-soft">Component 4 – how well the practice score, the adaptive plans and the app itself work, measured against therapists and users.</p>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Rated attempts" value={ag.n} sub={`${ag.attempts} attempts · min ${ag.min_ratings} to recalibrate`} />
        <StatTile label="Score vs therapist (MAE)" value={fmt(ag.current?.mae)} sub={`Pearson r ${fmt(ag.current?.pearson_r, 2)} · strong agreement ${fmt(ag.current?.strong_agreement, 0)}%`} />
        <StatTile label="Plans judged appropriate" value={pr.appropriate_pct === null ? "–" : `${pr.appropriate_pct}%`} sub={`${pr.n} reviews · acceptable ${pr.acceptable_pct ?? "–"}%`} />
        <StatTile label="Usability (SUS)" value={fmt(sus.overall.mean)} sub={sus.overall.n ? `${sus.overall.band} · n = ${sus.overall.n} · benchmark ${sus.benchmark}` : "no responses yet"} />
      </section>

      <section className="grid gap-5 lg:grid-cols-[1.3fr_1fr]">
        <Card title="Expert agreement – practice score vs therapist rating" icon={<Stethoscope size={18} className="text-navy" />}>
          <AgreementScatter points={ev.scatter} />
          <p className="mt-3 text-xs muted">Ratings map to the score scale (1 → 0 … 5 → 100). Points on the dashed line agree perfectly.</p>
        </Card>
        <Card title="Recalibration (ridge, leave-one-out)">
          {ag.current && (
            <table className="w-full text-sm">
              <thead><tr className="border-b border-line text-left text-xs uppercase tracking-wide muted"><th className="py-2">Weights</th><th>MAE</th><th>r</th><th>±15 pts</th><th>Strong</th></tr></thead>
              <tbody className="divide-y divide-line">
                <tr><td className="py-1.5 font-semibold">Current</td><td className="font-mono">{fmt(ag.current.mae)}</td><td className="font-mono">{fmt(ag.current.pearson_r, 2)}</td><td className="font-mono">{fmt(ag.current.within_15, 0)}%</td><td className="font-mono">{fmt(ag.current.strong_agreement, 0)}%</td></tr>
                {ag.calibrated && <tr><td className="py-1.5 font-semibold">Calibrated</td><td className="font-mono">{fmt(ag.calibrated.mae)}</td><td className="font-mono">{fmt(ag.calibrated.pearson_r, 2)}</td><td className="font-mono">{fmt(ag.calibrated.within_15, 0)}%</td><td className="font-mono">{fmt(ag.calibrated.strong_agreement, 0)}%</td></tr>}
              </tbody>
            </table>
          )}
          {ag.weights ? (
            <>
              <h3 className="mt-4 text-sm font-bold">Proposed weights</h3>
              <ul className="mt-2 space-y-1 text-xs">{ag.weights.map((w) => (
                <li key={w.feature} className="flex justify-between gap-2"><span className="text-ink-soft">{w.label}</span><span className="font-mono text-ink">{w.current} → <b>{w.calibrated}</b></span></li>
              ))}</ul>
              <p className="mt-3 rounded-lg bg-lav-50 p-2 text-xs text-ink-soft">{ag.calibrated?.method}. This is a proposal: the live weights in scoring.py only change after review.</p>
            </>
          ) : <p className="mt-3 text-sm muted">At least {ag.min_ratings} ratings are needed to re-estimate the weights ({ag.n} so far).</p>}
          <p className="mt-4 text-sm"><b>Inter-rater:</b> {ev.inter_rater.pairs ? `${ev.inter_rater.pairs} attempts rated by two therapists · weighted κ ${fmt(ev.inter_rater.weighted_kappa, 2)} · exact ${fmt(ev.inter_rater.exact_agreement, 0)}%` : "no attempt rated by two therapists yet"}</p>
        </Card>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <Card title="Plan reviews by therapists" icon={<ClipboardCheck size={18} className="text-navy" />}>
          <HBars format={(v) => String(v)} data={Object.entries(pr.counts).map(([k, v]) => ({ key: k, label: pr.labels[k], value: v, color: k === "appropriate" ? COLORS.ok : k === "partly" ? COLORS.warn : COLORS.bad }))} />
          <ul className="mt-4 space-y-2 text-sm">
            {pr.recent.length === 0 ? <li className="muted">No reviews yet – judge a plan in a patient's therapy monitor.</li> : pr.recent.map((r, i) => (
              <li key={i} className="rounded-xl border border-line p-3">
                <div className="flex flex-wrap justify-between gap-2 text-xs muted"><span><b className="text-ink">{r.patient}</b> · {r.plan.level}</span><span>{new Date(r.at).toLocaleString()}</span></div>
                <p className="mt-1 font-semibold">{pr.labels[r.verdict]}{r.note ? <span className="font-normal text-ink-soft"> – {r.note}</span> : ""}</p>
                <p className="mt-1 text-xs muted">{r.plan.today.map((t) => t.title).join(" · ")}</p>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Usability – System Usability Scale" icon={<Users size={18} className="text-navy" />}>
          {sus.overall.n === 0 ? <p className="text-sm muted">No responses yet. Patients are invited after {3} exercises.</p> : (
            <>
              <p className="text-sm">Mean <b>{sus.overall.mean}</b>{sus.overall.ci95 ? ` (95% CI ${sus.overall.ci95[0]}–${sus.overall.ci95[1]})` : ""} · SD {sus.overall.sd} · <b>{sus.overall.band}</b> · benchmark {sus.benchmark}</p>
              <ul className="mt-2 flex flex-wrap gap-2 text-xs">{Object.entries(sus.by_role).map(([role, s]) => <li key={role} className="chip bg-canvas capitalize text-ink">{role}: {s.mean} (n {s.n})</li>)}</ul>
              <h3 className="mt-4 text-sm font-bold">Mean answer per statement (1–5)</h3>
              <HBars max={5} format={(v) => v.toFixed(2)} data={sus.items.filter((i) => i.mean_answer !== null).map((i) => ({
                key: String(i.number), label: `${i.number}. ${i.text}`, value: i.mean_answer ?? 0, color: i.positive ? COLORS.navy : COLORS.lav,
                note: i.positive ? "positive statement – higher is better" : "negative statement – lower is better",
              }))} />
              <p className="mt-2 text-xs muted">Navy = positive statements (higher is better) · lavender = negative statements (lower is better).</p>
              {sus.comments.length > 0 && <ul className="mt-3 space-y-1.5 text-sm">{sus.comments.slice(0, 5).map((c, i) => <li key={i} className="rounded-lg bg-canvas p-2">“{c.comment}” <span className="text-xs muted">– {c.role}, {c.score}</span></li>)}</ul>}
            </>
          )}
          <div className="mt-4"><UsabilitySurvey force /></div>
        </Card>
      </section>

      <CohortCard />

      <Card title="Federated learning (SO4) – architecture design" icon={<Network size={18} className="text-navy" />}>
        <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
          {Object.entries(ev.federated).map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3 border-b border-line py-1.5"><dt className="capitalize muted">{k.replace(/_/g, " ")}</dt><dd className="text-right font-semibold text-ink">{String(v)}</dd></div>
          ))}
        </dl>
        <p className="mt-3 text-xs muted">Documented design only – a real federated training loop needs many client devices. Raw audio never leaves a device in either design.</p>
      </Card>
    </div>
  );
}
