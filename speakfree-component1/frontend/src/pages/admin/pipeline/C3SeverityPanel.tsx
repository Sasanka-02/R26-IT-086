/**
 * Component 3 dashboard – ★ NOVELTY: severity classification via a trained model cascade.
 *   stage 1  TORGO RandomForest on C1 acoustic windows → P(dysarthria)
 *   stage 2  disorder RF + severity RF + multi-label stuttering RF on the 17-feature vector
 *   fusion   rule-guarded unified severity score + uncertainty (explanation trail shown)
 */
import { AlertTriangle, Brain, Layers, ListOrdered, ShieldAlert, Waves } from "lucide-react";
import { Card, COLORS, SeverityGauge } from "../../../components/ui";
import { DISORDER_COLOR, DISORDER_LABEL, DISORDER_ORDER, HBars, SEVERITY_NAME, StatTile, severityColor } from "../../../components/charts";
import type { C3Report } from "../../../types/integration";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const SOURCE: Record<string, string> = {
  articulation_score: "C2 articulation", clear_word_ratio: "C2 articulation", kept_token_confidence: "C2 articulation",
  filler_rate: "C2 fluency events", repetition_rate: "C2 fluency events", prolongation_rate: "C2 fluency events",
  long_pauses_per_min: "C2 fluency events", dysarthria_probability: "C3 stage 1 (TORGO)",
};

export default function C3SeverityPanel({ c3 }: { c3: C3Report }) {
  const u = c3.uncertainty;
  const fallback = c3.model_status.any_untrained_fallback_used === true;
  const imp = c3.feature_importance.disorder_classifier;
  return (
    <div className="space-y-5">
      {fallback && (
        <div className="flex items-center gap-2 rounded-xl border border-warn/40 bg-warn-soft p-3 text-sm text-ink">
          <AlertTriangle size={16} className="text-warn" /> A model file was missing – a transparent rule-based fallback was used for part of this result.
        </div>
      )}

      <section className="grid gap-5 lg:grid-cols-[320px_1fr]">
        <Card title="Unified severity (fusion)">
          <SeverityGauge hint={c3.severity_level} label={c3.severity_label} risk={c3.risk_level.toLowerCase()} />
          <div className="mt-4 grid grid-cols-2 gap-2 text-center text-xs">
            <div className="rounded-lg bg-canvas p-2"><div className="muted">Disorder</div><div className="font-bold" style={{ color: COLORS.ink }}>{DISORDER_LABEL[c3.primary_disorder]}</div></div>
            <div className="rounded-lg bg-canvas p-2"><div className="muted">Risk</div><div className="font-bold">{c3.risk_level}</div></div>
            <div className="rounded-lg bg-canvas p-2"><div className="muted">Confidence</div><div className="font-bold">{pct(c3.confidence_score)} · {c3.confidence_band}</div></div>
            <div className="rounded-lg bg-canvas p-2"><div className="muted">E[level]</div><div className="font-bold">{c3.expected_level?.toFixed(2)}</div></div>
          </div>
          {c3.professional_review_recommended && (
            <p className="mt-3 flex items-center gap-1.5 rounded-lg bg-bad-soft p-2 text-xs text-ink"><ShieldAlert size={14} className="text-bad" /> Professional review recommended</p>
          )}
        </Card>

        <div className="grid gap-5 md:grid-cols-2">
          <Card title="Stage 2 · disorder classifier P(class)" icon={<Brain size={18} className="text-navy" />}>
            <HBars max={1} format={pct} data={DISORDER_ORDER.map((d) => ({
              key: d, label: DISORDER_LABEL[d], value: c3.disorder_breakdown[d] ?? 0, color: DISORDER_COLOR[d], highlight: d === c3.primary_disorder,
            }))} />
          </Card>
          <Card title="Stage 2 · severity estimator P(level)" icon={<ListOrdered size={18} className="text-navy" />}>
            <HBars max={1} format={pct} data={[1, 2, 3, 4].map((l) => ({
              key: String(l), label: `Level ${l} · ${SEVERITY_NAME[l]}`, value: c3.severity_breakdown[String(l)] ?? 0, color: severityColor(l),
              highlight: l === c3.unified_score.components_used.severity_model_level,
            }))} />
          </Card>
          <Card title="Stuttering events (multi-label)" icon={<Waves size={18} className="text-navy" />}>
            <HBars max={1} format={pct} data={(["repetition", "prolongation", "block"] as const).map((e) => ({
              key: e, label: e[0].toUpperCase() + e.slice(1), value: c3.stuttering_events[e] ?? 0, color: COLORS.lav,
              highlight: c3.stuttering_positive_events.includes(e), note: c3.stuttering_positive_events.includes(e) ? "positive (≥ 50%)" : undefined,
            }))} />
          </Card>
          <Card title="Stage 1 · TORGO acoustic model (real data)" icon={<Layers size={18} className="text-navy" />}>
            {c3.stage1_acoustic.probability === null ? (
              <p className="text-sm muted">No acoustic windows ({c3.stage1_acoustic.status.toLowerCase().replace(/_/g, " ")}) – the feature was imputed.</p>
            ) : (
              <>
                <div className="text-3xl font-extrabold">{pct(c3.stage1_acoustic.probability)}</div>
                <div className="text-xs muted">mean P(dysarthria) over {c3.stage1_acoustic.windows_used} windows of 3 s</div>
                <div className="mt-3">
                  <HBars max={1} format={pct} data={c3.stage1_acoustic.per_window.map((w, i) => ({
                    key: String(i), label: `${w.task_type} @ ${w.start_sec}s`, value: w.probability, color: DISORDER_COLOR.dysarthria,
                  }))} />
                </div>
              </>
            )}
          </Card>
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <Card title="Fusion explanation trail">
          <ol className="space-y-2 text-sm">
            {c3.unified_score.scoring_explanation.map((line, i) => (
              <li key={i} className="flex gap-2"><span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-navy text-[10px] font-bold text-white">{i + 1}</span>{line}</li>
            ))}
          </ol>
          <div className="mt-4 rounded-lg bg-lav-50 p-3 font-mono text-xs text-ink-soft">
            E[level] = Σ l·P(l) · rule 1: normal ⇒ level ≤ 2 · rule 2: A_C2 ≤ 45 or P(dys) ≥ 0.80 ⇒ level + 1
          </div>
          <h3 className="mt-4 text-sm font-bold">Recommendations</h3>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-ink-soft">{c3.recommendations.map((r) => <li key={r}>{r}</li>)}</ul>
        </Card>
        <Card title="What drives the disorder model (feature importance)">
          <HBars format={(v) => v.toFixed(3)} data={imp.map((f) => ({ key: f.feature, label: f.label, value: f.importance, color: COLORS.navy }))} empty="Fallback model – no importances" />
          <div className="mt-5 grid grid-cols-3 gap-3">
            <StatTile label="Entropy" value={u.normalised_entropy.toFixed(2)} sub="0 certain · 1 uniform" />
            <StatTile label="Tree spread" value={u.epistemic_std.toFixed(3)} sub="RF disagreement" />
            <StatTile label="Runtime" value={`${(c3.processing_time_seconds * 1000).toFixed(0)} ms`} sub={c3.model_version} />
          </div>
        </Card>
      </section>

      <Card title="Model input – 17-feature vector built from C1 + C2 (+ stage 1)">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-line text-left text-xs uppercase tracking-wide muted"><th className="py-2">Feature</th><th>Value</th><th>Source</th></tr></thead>
            <tbody className="divide-y divide-line">
              {c3.feature_vector.map((f) => (
                <tr key={f.feature}>
                  <td className="py-1.5 text-ink">{f.label}</td>
                  <td className="font-mono">{f.value.toFixed(3)}</td>
                  <td>{f.imputed ? <span className="chip bg-warn-soft text-ink">imputed default</span> : <span className="text-xs muted">{SOURCE[f.feature] ?? "C1 screening"}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs muted">{c3.disclaimer}</p>
      </Card>
    </div>
  );
}
