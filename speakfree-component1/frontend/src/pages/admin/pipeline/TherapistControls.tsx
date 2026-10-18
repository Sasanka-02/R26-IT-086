/**
 * Therapist controls in the therapy monitor (Component 4): alerts, homework (due date + attempts),
 * measurable goals, clinical notes (shared with the patient or private), plan review and 1–5
 * attempt ratings. Every change reloads the monitor so the plan the patient sees is shown at once.
 */
import { useState, type FormEvent } from "react";
import { AlertTriangle, BookOpenCheck, ClipboardCheck, Info, Lock, MessageSquareText, Plus, Target, Trash2, Users } from "lucide-react";
import { api } from "../../../api/client";
import { Card } from "../../../components/ui";
import type { AdminTherapy } from "../../../types/integration";

type Run = (fn: () => Promise<unknown>) => Promise<void>;

const ALERT_STYLE = { high: "border-bad/30 bg-bad-soft", medium: "border-sun/40 bg-sun-soft", info: "border-lav-200 bg-lav-50" };

export function AlertsCard({ alerts }: { alerts: AdminTherapy["therapist"]["alerts"] }) {
  if (!alerts.length) return null;
  return (
    <Card title="Alerts" icon={<AlertTriangle size={18} className="text-warn" />}>
      <ul className="grid gap-2 md:grid-cols-2">
        {alerts.map((a, i) => (
          <li key={i} className={`flex gap-2.5 rounded-xl border p-3 text-sm ${ALERT_STYLE[a.severity]}`}>
            {a.severity === "info" ? <Info size={16} className="mt-0.5 shrink-0 text-lav-600" /> : <AlertTriangle size={16} className={`mt-0.5 shrink-0 ${a.severity === "high" ? "text-bad" : "text-warn"}`} />}
            <span><b className="text-ink">{a.text}</b>{a.detail && <span className="block text-xs text-ink-soft">{a.detail}</span>}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function HomeworkRow({ patientId, item, run }: { patientId: string; item: AdminTherapy["therapist"]["homework"][number]; run: Run }) {
  const [due, setDue] = useState(item.due ?? "");
  const [times, setTimes] = useState(item.times);
  const dirty = due !== (item.due ?? "") || times !== item.times;
  return (
    <li className="grid items-center gap-2 rounded-xl bg-canvas p-3 text-sm sm:grid-cols-[1fr_auto_auto_auto]">
      <div className="min-w-0">
        <p className="truncate font-semibold text-ink">{item.title}</p>
        <p className={`text-xs ${item.overdue ? "font-semibold text-bad" : item.done ? "text-ok" : "muted"}`}>
          {item.done_count}/{item.times} done{item.overdue ? " · overdue" : item.done ? " · complete" : item.days_left !== null ? ` · ${item.days_left} days left` : ""}
        </p>
      </div>
      <input type="date" className="input py-1.5 text-xs" value={due} onChange={(e) => setDue(e.target.value)} aria-label="Due date" />
      <label className="flex items-center gap-1 text-xs muted">×<input type="number" min={1} max={20} className="input w-16 py-1.5 text-xs" value={times}
        onChange={(e) => setTimes(Math.max(1, Math.min(20, Number(e.target.value))))} aria-label="Attempts asked for" /></label>
      <button className="btn-primary px-3 py-1.5 text-xs" disabled={!dirty}
        onClick={() => void run(() => api.admin.setHomework(patientId, item.exercise_id, { due: due || null, times }))}>Save</button>
    </li>
  );
}

export function HomeworkAndGoals({ patientId, data, run }: { patientId: string; data: AdminTherapy; run: Run }) {
  const t = data.therapist;
  const [metric, setMetric] = useState(t.goal_metrics[0]?.metric ?? "average_score");
  const [target, setTarget] = useState(70);
  const meta = t.goal_metrics.find((m) => m.metric === metric);
  const addGoal = (e: FormEvent) => { e.preventDefault(); void run(() => api.admin.addGoal(patientId, metric, target)); };

  return (
    <section className="grid gap-5 lg:grid-cols-2">
      <Card title="Homework" icon={<BookOpenCheck size={18} className="text-navy" />}>
        {t.homework.length === 0 ? <p className="text-sm muted">No exercises assigned. Tick “Assign” in the ranking table below – assigned exercises come first in the patient's plan and appear here as homework.</p> : (
          <ul className="space-y-2">{t.homework.map((h) => <HomeworkRow key={h.exercise_id} patientId={patientId} item={h} run={run} />)}</ul>
        )}
        {t.daf_delay_ms && <p className="mt-3 text-xs muted">DAF calibrated by the patient: {t.daf_delay_ms} ms.</p>}
      </Card>
      <Card title="Therapist goals" icon={<Target size={18} className="text-navy" />}>
        <ul className="space-y-2 text-sm">
          {t.goals.length === 0 && <li className="muted">No goals set – the plan's automatic goals still apply.</li>}
          {t.goals.map((g) => (
            <li key={g.id} className="flex items-center justify-between gap-2 rounded-xl bg-canvas px-3 py-2">
              <span className={g.met ? "font-semibold text-ok" : "text-ink"}>{g.met ? "✓ " : ""}{g.text} <span className="text-xs muted">· now {g.current ?? "–"}</span></span>
              <button className="text-ink-muted hover:text-bad" aria-label={`Remove goal ${g.text}`} onClick={() => void run(() => api.admin.removeGoal(patientId, g.goal_id))}><Trash2 size={15} /></button>
            </li>
          ))}
        </ul>
        <form onSubmit={addGoal} className="mt-3 flex flex-wrap items-end gap-2">
          <label className="min-w-[200px] flex-1"><span className="label">Measure</span>
            <select className="input py-2" value={metric} onChange={(e) => setMetric(e.target.value)}>
              {t.goal_metrics.map((m) => <option key={m.metric} value={m.metric}>{m.label} ({m.direction === "at_least" ? "at least" : "at most"})</option>)}
            </select></label>
          <label className="w-24"><span className="label">Target</span>
            <input type="number" min={0} max={100} step={0.5} className="input py-2" value={target} onChange={(e) => setTarget(Number(e.target.value))} /></label>
          <button className="btn-primary py-2"><Plus size={15} /> Add {meta ? `(${meta.unit})` : ""}</button>
        </form>
      </Card>
    </section>
  );
}

export function NotesAndReview({ patientId, data, run }: { patientId: string; data: AdminTherapy; run: Run }) {
  const t = data.therapist;
  const [text, setText] = useState("");
  const [shared, setShared] = useState(true);
  const [verdict, setVerdict] = useState("appropriate");
  const [note, setNote] = useState("");
  return (
    <section className="grid gap-5 lg:grid-cols-2">
      <Card title="Clinical notes" icon={<MessageSquareText size={18} className="text-navy" />}>
        <form onSubmit={(e) => { e.preventDefault(); if (text.trim()) void run(() => api.admin.addNote(patientId, text, shared)).then(() => setText("")); }}>
          <textarea className="input" rows={3} maxLength={2000} placeholder="e.g. Great progress with easy onsets – keep the pacing exercise daily." value={text} onChange={(e) => setText(e.target.value)} />
          <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" className="h-4 w-4 accent-[#1E3A8A]" checked={shared} onChange={(e) => setShared(e.target.checked)} /> Share with the patient</label>
            <button className="btn-primary py-2" disabled={!text.trim()}><Plus size={15} /> Add note</button>
          </div>
        </form>
        <ul className="mt-4 max-h-80 space-y-2 overflow-y-auto pr-1 scrollbar-thin">
          {t.notes.length === 0 && <li className="text-sm muted">No notes yet.</li>}
          {t.notes.map((n) => (
            <li key={n.id} className="rounded-xl bg-canvas px-3 py-2 text-sm">
              <div className="flex flex-wrap items-center gap-2 text-xs muted">
                {n.shared ? <span className="chip bg-ok-soft px-2 py-0 text-ok"><Users size={10} /> shared{n.unread ? " · not read yet" : " · read"}</span>
                  : <span className="chip bg-line px-2 py-0 text-ink-soft"><Lock size={10} /> private</span>}
                <span>{n.by_name} · {new Date(n.at).toLocaleString()}</span>
              </div>
              <p className="mt-1 whitespace-pre-line text-ink">{n.text}</p>
            </li>
          ))}
        </ul>
      </Card>
      <Card title="Review this plan" icon={<ClipboardCheck size={18} className="text-navy" />}>
        <p className="text-sm text-ink-soft">Is today's plan right for this patient? Your verdict is stored with the plan exactly as it is now and feeds the evidence page.</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {Object.entries(t.plan_verdicts).map(([k, label]) => (
            <button key={k} type="button" onClick={() => setVerdict(k)} className={`chip py-1.5 ${verdict === k ? "bg-navy text-white" : "bg-canvas text-ink-soft hover:bg-lav-100"}`}>{label}</button>
          ))}
        </div>
        <input className="input mt-3" maxLength={1000} placeholder="Optional note (what would you change?)" value={note} onChange={(e) => setNote(e.target.value)} />
        <button className="btn-primary mt-3" onClick={() => void run(() => api.admin.reviewPlan(patientId, verdict, note || undefined)).then(() => setNote(""))}>Save review</button>
        <ul className="mt-4 space-y-1.5 text-sm">
          {t.plan_reviews.map((r) => <li key={r.id} className="flex justify-between gap-2"><span><b>{r.label}</b>{r.note ? <span className="text-ink-soft"> – {r.note}</span> : ""}</span><span className="shrink-0 text-xs muted">{new Date(r.at).toLocaleDateString()}</span></li>)}
        </ul>
      </Card>
    </section>
  );
}

/** 1–5 rating buttons for one attempt (the viewer's own rating is highlighted). */
export function RateAttempt({ attemptId, mine, others, run }: { attemptId?: number; mine?: number | null; others: number; run: Run }) {
  if (!attemptId) return <span className="muted">–</span>;
  return (
    <span className="inline-flex items-center gap-0.5" role="group" aria-label="Rate this attempt 1 to 5">
      {[1, 2, 3, 4, 5].map((r) => (
        <button key={r} type="button" onClick={() => void run(() => api.admin.rateAttempt(attemptId, r))}
          className={`h-6 w-6 rounded-md text-[11px] font-bold transition ${mine === r ? "bg-navy text-white" : "bg-canvas text-ink-soft hover:bg-lav-100"}`}>{r}</button>
      ))}
      {others > 0 && <span className="ml-1 text-[10px] muted" title="Ratings from other therapists">+{others}</span>}
    </span>
  );
}
