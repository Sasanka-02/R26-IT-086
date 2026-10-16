/**
 * ReportsPage – every printable report for the active patient in one place:
 * screening reports (one per screening) and the therapy progress report.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, FileText, HeartPulse, Mail } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { Spinner } from "../components/ui";
import type { SessionListItem } from "../types";
import type { PlanResponse } from "../types/integration";
import { friendlyStatus } from "../utils/friendlyStatus";

export default function ReportsPage() {
  const { activePatient } = useAuth();
  const [sessions, setSessions] = useState<SessionListItem[] | null>(null);
  const [plan, setPlan] = useState<PlanResponse | null>(null);

  useEffect(() => {
    if (!activePatient) return;
    setSessions(null);
    api.sessions(activePatient.id).then(setSessions).catch(() => setSessions([]));
    api.therapy.plan(activePatient.id).then(setPlan).catch(() => setPlan({ has_profile: false }));
  }, [activePatient]);

  if (!activePatient) return <div className="card p-8 text-center muted">No patient selected.</div>;
  if (!sessions || !plan) return <Spinner />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-extrabold tracking-tight">Reports</h1>
        <p className="mt-1 text-sm text-ink-soft">Printable reports for {activePatient.full_name} – save them as PDF to share with a therapist or school.</p>
      </div>

      <section className="card p-6">
        <h2 className="flex items-center gap-2 text-[15px] font-bold"><HeartPulse size={18} className="text-navy" /> Therapy progress report</h2>
        {plan.has_profile ? (
          <div className="mt-3 flex flex-col gap-4 md:flex-row md:items-center">
            <p className="flex-1 text-sm text-ink-soft">
              Plan “{plan.focus.patient_name}” · {plan.progress.total_sessions} exercises · {plan.progress.total_minutes} minutes practised ·
              current level {plan.level.label} · trend: {plan.progress.trend.label.toLowerCase()}.
            </p>
            <Link to="/therapy/report?print=1" target="_blank" className="btn-primary"><Download size={16} /> Download therapy report</Link>
          </div>
        ) : <p className="mt-3 text-sm muted">Available after your first screening, once your therapy plan has started.</p>}
      </section>

      <section className="card p-6">
        <h2 className="flex items-center gap-2 text-[15px] font-bold"><FileText size={18} className="text-navy" /> Screening reports</h2>
        {sessions.length === 0 ? (
          <p className="mt-3 text-sm muted">No screenings yet. <Link to="/assessment" className="font-semibold text-brand hover:underline">Start your first one</Link>.</p>
        ) : (
          <ul className="mt-3 divide-y divide-line">
            {[...sessions].reverse().map((s) => {
              const st = friendlyStatus(s.severity_hint);
              return (
                <li key={s.session_id} className="flex flex-wrap items-center gap-3 py-3">
                  <span className="h-3 w-3 rounded-full" style={{ background: st.color }} aria-hidden />
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-ink">Screening of {new Date(s.created_at).toLocaleDateString(undefined, { dateStyle: "long" })}</div>
                    <div className="text-xs muted">{st.title} · {s.recording_count} recordings</div>
                  </div>
                  <Link to={`/sessions/${s.session_id}`} className="btn-ghost py-2 text-xs">View results</Link>
                  <Link to={`/sessions/${s.session_id}/report?print=1`} target="_blank" className="btn-outline py-2 text-xs"><Download size={14} /> PDF</Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <p className="flex items-center gap-2 text-xs muted"><Mail size={14} /> Tip: save the PDF, then attach it to an e-mail to your therapist.</p>
    </div>
  );
}
