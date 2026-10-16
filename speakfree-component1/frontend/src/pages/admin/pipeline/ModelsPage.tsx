/**
 * ModelsPage (admin) – the methods behind Components 2–4: C2 equations, C3 model card with
 * held-out metrics and confusion matrices, and the C4 adaptive-engine settings.
 */
import { useEffect, useState } from "react";
import { Brain, Cpu, Sigma } from "lucide-react";
import { api } from "../../../api/client";
import { Card, ErrorBox, Spinner } from "../../../components/ui";
import { ConfusionMatrix, EquationCard, StatTile } from "../../../components/charts";
import type { ModelsInfo } from "../../../types/integration";

const TITLES: Record<string, string> = {
  dysarthria_real_torgo: "Stage 1 · Dysarthria (TORGO, real data)",
  disorder_classifier: "Stage 2 · Disorder classifier",
  severity_estimator: "Stage 2 · Severity estimator (L1–L4)",
  stuttering_multilabel: "Stage 2 · Stuttering events (multi-label)",
};
const SHOW = ["accuracy", "balanced_accuracy", "macro_f1", "roc_auc", "f1", "mae_levels", "within_one_level", "ece_top1", "hamming_loss"];

export default function ModelsPage() {
  const [data, setData] = useState<ModelsInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.admin.models().then(setData).catch((e: Error) => setError(e.message)); }, []);
  if (error) return <ErrorBox message={error} />;
  if (!data) return <Spinner />;
  const card = data.component3.model_card;
  const c4 = data.component4;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-extrabold tracking-tight">Models &amp; Methods</h1>
        <p className="text-sm text-ink-soft">Every formula and model the backend pipeline uses, with stored validation metrics.</p>
      </div>

      <Card title="Component 2 · articulation score" icon={<Sigma size={18} className="text-navy" />}>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {data.component2.equations.map((e) => <EquationCard key={e.id} id={e.id} name={e.name} formula={e.formula} />)}
        </div>
        <p className="mt-3 text-xs muted">Fillers removed: {data.component2.fillers.join(", ")} · levels: {data.component2.level_bands.map((b) => `${b.label} ≥ ${b.min}`).join(" · ")}</p>
      </Card>

      <Card title="Component 3 · severity model cascade" icon={<Brain size={18} className="text-navy" />}
        right={<span className="chip bg-lav-100 text-lav-600">{data.component3.health.models_trained} models loaded · {data.component3.health.model_version}</span>}>
        {card ? (
          <>
            <ol className="mb-4 list-decimal space-y-1 pl-5 text-sm text-ink-soft">{card.cascade.map((c) => <li key={c}>{c}</li>)}</ol>
            <div className="grid gap-5 lg:grid-cols-2">
              {Object.entries(card.models).map(([key, m]) => {
                const metrics = (m.metrics ?? {}) as Record<string, unknown>;
                const cm = metrics.confusion_matrix as number[][] | undefined;
                return (
                  <div key={key} className="rounded-xl border border-line p-4">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-sm font-bold">{TITLES[key] ?? key}</h3>
                      <span className={`chip ${m.data_source.startsWith("TORGO") ? "bg-ok-soft" : "bg-warn-soft"} text-ink`}>{m.data_source}</span>
                    </div>
                    <p className="text-xs muted">{m.algorithm}{m.validation ? ` · ${m.validation}` : ""}</p>
                    <div className="mt-3 grid grid-cols-3 gap-2">
                      {SHOW.filter((k) => typeof metrics[k] === "number").slice(0, 3).map((k) => (
                        <StatTile key={k} label={k.replace(/_/g, " ")} value={(metrics[k] as number).toFixed(3)} />
                      ))}
                    </div>
                    {cm && <div className="mt-3"><ConfusionMatrix matrix={cm} labels={(metrics.confusion_matrix_labels as (string | number)[]) ?? []} /></div>}
                    {key === "stuttering_multilabel" && metrics.per_label_f1 ? (
                      <p className="mt-3 text-xs text-ink-soft">Per-label F1: {Object.entries(metrics.per_label_f1 as Record<string, number>).map(([l, v]) => `${l} ${v.toFixed(2)}`).join(" · ")}</p>
                    ) : null}
                  </div>
                );
              })}
            </div>
            <p className="mt-4 rounded-lg bg-warn-soft p-3 text-xs text-ink">{card.disclaimer}</p>
            <p className="mt-2 text-xs muted">Feature vector ({card.feature_order.length}): {card.feature_order.join(", ")}</p>
          </>
        ) : <p className="text-sm muted">model_card.json not found – run python training/train_all.py in speakfree-component3/backend.</p>}
      </Card>

      <Card title="Component 4 · adaptive therapy engine" icon={<Cpu size={18} className="text-navy" />}>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile label="LinUCB α (explore)" value={c4.bandit.alpha} sub={`context dim ${c4.bandit.context_dim}`} />
          <StatTile label="C3 category prior β" value={c4.bandit.category_beta} sub={`difficulty penalty ${c4.bandit.difficulty_penalty}`} />
          <StatTile label="Strong / weak" value={`${c4.thresholds.strong} / ${c4.thresholds.weak}`} sub="level-ladder thresholds" />
          <StatTile label="Assistant intents" value={`${c4.intent_classifier.accuracy}%`} sub={`LOO accuracy · ${c4.intent_classifier.intents} intents, ${c4.intent_classifier.examples} examples`} />
        </div>
        <div className="mt-5 grid gap-5 lg:grid-cols-2">
          <div className="overflow-x-auto">
            <h3 className="mb-2 text-sm font-bold">Category mapping (C3 → C4)</h3>
            <table className="w-full text-sm">
              <thead><tr className="border-b border-line text-left text-xs uppercase muted"><th className="py-1.5">C3 disorder</th><th>Focus</th><th>Patient sees</th><th>Ladder</th></tr></thead>
              <tbody className="divide-y divide-line">
                {Object.entries(c4.foci).map(([k, f]) => (
                  <tr key={k}><td className="py-1.5">{f.c3_disorder}</td><td>{f.admin_name}</td><td>“{f.patient_name}”</td><td className="font-mono text-xs">{f.ladder_type}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="overflow-x-auto">
            <h3 className="mb-2 text-sm font-bold">Dose &amp; starting level by severity</h3>
            <table className="w-full text-sm">
              <thead><tr className="border-b border-line text-left text-xs uppercase muted"><th className="py-1.5">Level</th><th>Sessions/wk</th><th>Min</th><th>Exercises</th><th>Start</th></tr></thead>
              <tbody className="divide-y divide-line">
                {Object.entries(c4.dose_by_severity).map(([l, d]) => (
                  <tr key={l}><td className="py-1.5">L{l}</td><td>{d.sessions_per_week}</td><td>{d.minutes_per_session}</td><td>{d.exercises_per_session}</td><td>{c4.start_level_by_severity[l]}</td></tr>
                ))}
              </tbody>
            </table>
            <h3 className="mb-2 mt-4 text-sm font-bold">Attempt score weights</h3>
            <p className="font-mono text-xs text-ink-soft">{Object.entries(c4.scoring_weights).map(([k, v]) => `${k} ${v > 0 ? "+" : ""}${v}`).join(" · ")}</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
