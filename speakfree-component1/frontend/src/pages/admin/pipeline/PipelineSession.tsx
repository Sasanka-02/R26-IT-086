/**
 * PipelineSession (admin) – one screening session through every component:
 *   C1 summary → C2 articulation (novelty) → C3 severity model (novelty) → C4 therapy profile.
 */
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Braces, Dumbbell, Loader2, RefreshCw, Target } from "lucide-react";
import { api } from "../../../api/client";
import { Card, ErrorBox, RiskBadge, ScoreRing, Spinner } from "../../../components/ui";
import { DISORDER_COLOR, FOCUS_LABEL, HBars, StatTile, StatusChip } from "../../../components/charts";
import type { Focus, PipelineDetail } from "../../../types/integration";
import { PipelineFlow } from "./PipelineOverview";
import C2ArticulationPanel from "./C2ArticulationPanel";
import C3SeverityPanel from "./C3SeverityPanel";

const TABS = [
  { key: "C1", label: "C1 · Screening" },
  { key: "C2", label: "C2 · Articulation" },
  { key: "C3", label: "C3 · Severity" },
  { key: "C4", label: "C4 · Therapy profile" },
] as const;
type Tab = (typeof TABS)[number]["key"];
const FOCUS_COLOR: Record<Focus, string> = {
  maintenance: DISORDER_COLOR.normal, fluency: DISORDER_COLOR.stuttering, motor_speech: DISORDER_COLOR.dysarthria, speech_sounds: DISORDER_COLOR.articulation,
};

function downloadJson(name: string, data: unknown) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

export default function PipelineSession() {
  const { sessionId = "" } = useParams();
  const [data, setData] = useState<PipelineDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("C2");
  const [busy, setBusy] = useState(false);

  const load = () => api.admin.pipelineRun(sessionId).then(setData).catch((e: Error) => setError(e.message));
  useEffect(() => { setData(null); void load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [sessionId]);

  async function rerun() {
    setBusy(true);
    try { await api.admin.rerunPipeline(sessionId); await load(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Spinner />;
  const c1 = data.c1_summary;
  const p = data.c4_profile;

  return (
    <div className="space-y-6">
      <Link to="/admin/pipeline" className="inline-flex items-center gap-1 text-xs font-medium text-ink-muted hover:text-ink"><ArrowLeft size={14} /> Pipeline</Link>
      <section className="card flex flex-col gap-4 p-5 md:flex-row md:items-center">
        <div className="flex-1">
          <h1 className="text-2xl font-extrabold">{data.patient.full_name} <span className="text-base font-medium muted">· {data.patient.age} y · {data.patient.id}</span></h1>
          <p className="text-sm text-ink-soft">Session {data.session_id.slice(0, 8)}… · processed {new Date(data.created_at).toLocaleString()} ·{" "}
            C2 {data.stage_timings.component2_ms ?? "–"} ms · C3 {data.stage_timings.component3_ms ?? "–"} ms · C4 {data.stage_timings.component4_ms ?? "–"} ms</p>
          {data.error && <p className="mt-1 text-sm text-bad">{data.error}</p>}
        </div>
        <StatusChip status={data.status} />
        <button className="btn-ghost" onClick={() => void rerun()} disabled={busy}>{busy ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />} Re-run C2→C4</button>
        <button className="btn-ghost" onClick={() => downloadJson(`pipeline-${sessionId}.json`, data)}><Braces size={15} /> JSON</button>
      </section>

      <PipelineFlow active={tab} />

      <nav className="flex flex-wrap gap-2" role="tablist">
        {TABS.map((t) => (
          <button key={t.key} role="tab" aria-selected={tab === t.key} onClick={() => setTab(t.key)}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${tab === t.key ? "bg-navy text-white shadow-nav" : "bg-white text-ink-soft hover:bg-lav-50"}`}>
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "C1" && (
        <section className="grid gap-5 md:grid-cols-[auto_1fr]">
          <Card title="Component 1 session output">
            <div className="flex flex-col items-center gap-2"><ScoreRing value={c1.overall_speech_score} size={130} />
              <RiskBadge hint={c1.screening_indicator.severity_hint} label={c1.screening_indicator.label} /></div>
          </Card>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 content-start">
            <StatTile label="ASR confidence (Eq.3)" value={`${c1.overall_confidence_percent.toFixed(1)}%`} sub={`${c1.total_token_count} tokens`} />
            <StatTile label="Fluency" value={c1.fluency_score.toFixed(1)} />
            <StatTile label="Pronunciation" value={c1.pronunciation_score.toFixed(1)} />
            <StatTile label="Dysfluency ratio" value={`${(c1.dysfluency_ratio * 100).toFixed(1)}%`} sub={`${c1.dysfluency_candidate_count} of ${c1.word_count} words`} />
            <StatTile label="Speech rate" value={`${c1.acoustic_summary.words_per_minute.toFixed(0)} wpm`} />
            <StatTile label="Recordings" value={c1.recording_count} sub={c1.task_types.join(" · ")} />
            <Link to={`/admin/patients/${data.patient.id}/sessions/${data.session_id}`} className="btn-outline sm:col-span-2 lg:col-span-3">
              Open the full Component 1 dashboard <ArrowRight size={15} />
            </Link>
          </div>
        </section>
      )}

      {tab === "C2" && (data.c2 ? <C2ArticulationPanel c2={data.c2} /> : <ErrorBox message="Component 2 did not produce a report for this session." />)}
      {tab === "C3" && (data.c3 ? <C3SeverityPanel c3={data.c3} /> : <ErrorBox message="Component 3 did not run for this session." />)}

      {tab === "C4" && (p ? (
        <section className="grid gap-5 lg:grid-cols-2">
          <Card title="C3 → C4 hand-off: therapy profile" icon={<Dumbbell size={18} className="text-navy" />}>
            <div className="rounded-xl p-4 text-white" style={{ background: `linear-gradient(135deg, #1E3A8A, ${FOCUS_COLOR[p.focus]})` }}>
              <div className="text-xs font-semibold uppercase tracking-wide opacity-80">{FOCUS_LABEL[p.focus]}</div>
              <div className="text-xl font-extrabold">“{p.focus_name}”</div>
              <div className="text-xs opacity-80">what the patient sees – no diagnosis or level</div>
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div><dt className="text-xs muted">Severity → starting level</dt><dd className="font-semibold">L{p.severity_level} → {p.start_level}</dd></div>
              <div><dt className="text-xs muted">C3 confidence (bandit context)</dt><dd className="font-semibold">{(p.confidence * 100).toFixed(0)}%</dd></div>
              <div><dt className="text-xs muted">Flagged sounds → drills</dt><dd className="font-semibold">{p.flagged_sounds.join(", ") || "none"}</dd></div>
              <div><dt className="text-xs muted">Stuttering events</dt><dd className="font-semibold">{p.stuttering_events.join(", ") || "none"}</dd></div>
            </dl>
            {p.baseline.target_metric && (
              <p className="mt-4 flex items-center gap-2 rounded-lg bg-lav-50 p-3 text-sm"><Target size={16} className="text-lav-600" /> Screening goal: {p.baseline.target_metric.text}</p>
            )}
            <Link to={`/admin/patients/${data.patient.id}/therapy`} className="btn-primary mt-4 w-full">Open therapy monitor <ArrowRight size={15} /></Link>
          </Card>
          <Card title="Category prior for the bandit  P_C3(focus)">
            <HBars max={1} format={(v) => `${(v * 100).toFixed(1)}%`} data={(Object.keys(p.focus_probabilities) as Focus[]).map((f) => ({
              key: f, label: FOCUS_LABEL[f], value: p.focus_probabilities[f], color: FOCUS_COLOR[f], highlight: f === p.focus,
            }))} />
            <p className="mt-4 font-mono text-xs text-ink-soft">prior_j = β · (2·Σ_c P(c)·1[j targets c] − 1),  β = 0.20</p>
          </Card>
        </section>
      ) : <ErrorBox message="No therapy profile was created for this session." />)}
    </div>
  );
}
