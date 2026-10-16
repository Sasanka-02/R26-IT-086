/**
 * PipelineOverview (admin) – every finalised screening and what the backend pipeline produced:
 * C1 screening → C2 articulation score → C3 severity model → C4 therapy focus.
 * Patients never see this page; it is the admin's view of the integrated system.
 */
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, ArrowRight, Brain, CheckCircle2, Dumbbell, Mic, Search, Sigma, Users, Workflow } from "lucide-react";
import { api } from "../../../api/client";
import { DISORDER_COLOR, DISORDER_LABEL, DISORDER_ORDER, DisorderChip, FOCUS_LABEL, SeverityChip, StackedBar, StatTile,
  StatusChip, severityColor, SEVERITY_NAME } from "../../../components/charts";
import { Card, ErrorBox, Spinner } from "../../../components/ui";
import type { PipelineOverview as Overview } from "../../../types/integration";

const STAGES = [
  { n: "C1", title: "Speech screening", text: "Whisper log-prob confidence, acoustic features, TORGO windows", icon: <Mic size={18} /> },
  { n: "C2", title: "Articulation score", text: "A = 100 × (0.5·C + 0.5·CWR), pooled per session", icon: <Sigma size={18} /> },
  { n: "C3", title: "Severity model", text: "TORGO RF → disorder RF + severity RF + uncertainty", icon: <Brain size={18} /> },
  { n: "C4", title: "Adaptive therapy", text: "Category focus, LinUCB plan, AI assistant", icon: <Dumbbell size={18} /> },
];

export function PipelineFlow({ active }: { active?: string }) {
  return (
    <ol className="grid gap-3 md:grid-cols-4">
      {STAGES.map((s, i) => (
        <li key={s.n} className={`relative rounded-2xl border p-4 ${active === s.n ? "border-navy bg-brand-soft" : "border-line bg-white"}`}>
          <div className="flex items-center gap-2">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-navy text-white">{s.icon}</span>
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wide text-lav-600">Component {s.n.slice(1)}</div>
              <div className="text-sm font-bold text-ink">{s.title}</div>
            </div>
          </div>
          <p className="mt-2 text-xs text-ink-soft">{s.text}</p>
          {i < STAGES.length - 1 && <ArrowRight size={18} className="absolute -right-3 top-1/2 hidden -translate-y-1/2 text-lav-400 md:block" />}
        </li>
      ))}
    </ol>
  );
}

export default function PipelineOverview() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    api.admin.pipeline().then(setData).catch((e: Error) => setError(e.message));
  }, []);

  const rows = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    return data.runs.filter((r) =>
      (filter === "all" || r.primary_disorder === filter || (filter === "failed" && r.status !== "completed")) &&
      (!q || `${r.patient_name} ${r.patient_id}`.toLowerCase().includes(q)));
  }, [data, query, filter]);

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Spinner />;
  const k = data.kpis;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-[28px] font-extrabold tracking-tight"><Workflow className="text-navy" /> Analysis Pipeline</h1>
        <p className="text-sm text-ink-soft">Every finalised screening runs through Components 2 → 3 → 4 in the backend. Patients only see their results and therapy plan.</p>
      </div>

      <PipelineFlow />

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Sessions processed" value={k.sessions} sub={`${k.completed} completed · ${k.failed} need attention`} icon={<CheckCircle2 size={18} />} />
        <StatTile label="Avg. articulation (C2)" value={k.average_articulation ?? "–"} sub="Session score, 0–100" icon={<Sigma size={18} />} />
        <StatTile label="Therapy exercises (C4)" value={k.therapy_attempts} sub="completed by all patients" icon={<Activity size={18} />} />
        <StatTile label="Active in therapy" value={k.active_patients_7d} sub="patients practising in the last 7 days" icon={<Users size={18} />} />
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <Card title="Disorder classification (C3)">
          <StackedBar data={DISORDER_ORDER.map((d) => ({ key: d, label: DISORDER_LABEL[d], value: k.disorders[d] ?? 0, color: DISORDER_COLOR[d] }))} />
        </Card>
        <Card title="Severity level (C3)">
          <StackedBar data={[1, 2, 3, 4].map((l) => ({ key: String(l), label: `L${l} ${SEVERITY_NAME[l]}`, value: k.severity[String(l)] ?? 0, color: severityColor(l) }))} />
        </Card>
      </section>

      <Card title="Screening sessions" right={
        <div className="flex flex-wrap gap-2">
          <label className="relative">
            <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted" />
            <input className="input w-56 py-2 pl-9 text-sm" placeholder="Search patient" value={query} onChange={(e) => setQuery(e.target.value)} />
          </label>
          <select className="input w-44 py-2 text-sm" value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter">
            <option value="all">All results</option>
            {DISORDER_ORDER.map((d) => <option key={d} value={d}>{DISORDER_LABEL[d]}</option>)}
            <option value="failed">Needs attention</option>
          </select>
        </div>
      }>
        {rows.length === 0 ? (
          <p className="py-6 text-center text-sm muted">No screenings match. Sessions appear here as soon as a patient presses “Analyse Now”.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs uppercase tracking-wide muted">
                  <th className="py-2 pr-3">Patient</th><th className="pr-3">Date</th><th className="pr-3">C1 score</th>
                  <th className="pr-3">C2 articulation</th><th className="pr-3">C3 disorder</th><th className="pr-3">C3 severity</th>
                  <th className="pr-3">C4 focus</th><th className="pr-3">Status</th><th />
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {rows.map((r) => (
                  <tr key={r.session_id} className="hover:bg-canvas">
                    <td className="py-2.5 pr-3"><div className="font-semibold text-ink">{r.patient_name}</div><div className="text-xs muted">{r.patient_id}</div></td>
                    <td className="whitespace-nowrap pr-3 text-ink-soft">{new Date(r.created_at).toLocaleDateString()}<div className="text-xs muted">{new Date(r.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</div></td>
                    <td className="pr-3 font-mono">{r.c1_overall_score?.toFixed(1) ?? "–"}</td>
                    <td className="pr-3 font-mono font-semibold">{r.articulation_score?.toFixed(1) ?? "–"}</td>
                    <td className="pr-3"><DisorderChip disorder={r.primary_disorder} /></td>
                    <td className="pr-3"><SeverityChip level={r.severity_level} /></td>
                    <td className="pr-3 text-ink-soft">{r.therapy_focus ? FOCUS_LABEL[r.therapy_focus] : "–"}</td>
                    <td className="pr-3"><StatusChip status={r.status} /></td>
                    <td className="text-right">
                      <Link to={`/admin/pipeline/${r.session_id}`} className="inline-flex items-center gap-1 text-xs font-semibold text-brand hover:underline">Open <ArrowRight size={13} /></Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
