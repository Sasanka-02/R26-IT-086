/**
 * My progress – light theme, like the rest of the app.
 * Therapy practice dashboard first (ProgressDark), then the screening history.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Download } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { Spinner } from "../components/ui";
import type { SessionListItem } from "../types";
import type { PlanResponse } from "../types/integration";
import { friendlyStatus } from "../utils/friendlyStatus";
import ProgressDark, { D, DCard } from "./therapy/ProgressDark";

/** Overall speech score across screenings – one line, dots coloured by that screening's result. */
function ScreeningTrend({ points }: { points: SessionListItem[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 640, H = 200, pad = 34;
  if (points.length < 2) return <p className="text-sm" style={{ color: D.muted }}>Complete another screening to see how you're progressing over time.</p>;
  const x = (i: number) => pad + (i / (points.length - 1)) * (W - pad * 2);
  const y = (v: number) => H - pad - (v / 100) * (H - pad * 2);
  const h = hover !== null ? points[hover] : null;
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Overall speech score across screenings" onMouseLeave={() => setHover(null)}>
        {[0, 25, 50, 75, 100].map((v) => (
          <g key={v}><line x1={pad} x2={W - pad} y1={y(v)} y2={y(v)} stroke={D.line} /><text x={pad - 8} y={y(v) + 4} textAnchor="end" fontSize="10" fill={D.muted}>{v}</text></g>
        ))}
        <path d={points.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.overall_speech_score)}`).join("")} fill="none" stroke={D.accent} strokeWidth={2} />
        {points.map((p, i) => (
          <circle key={p.session_id} cx={x(i)} cy={y(p.overall_speech_score)} r={hover === i ? 7 : 5} fill={friendlyStatus(p.severity_hint).color} stroke={D.card} strokeWidth={2}
            onMouseEnter={() => setHover(i)} />
        ))}
      </svg>
      {h && (
        <div className="pointer-events-none absolute top-0 rounded-lg border px-3 py-2 text-xs" style={{ left: `${Math.min(70, (x(hover!) / W) * 100)}%`, background: "#FFFFFF", borderColor: D.line }}>
          <p className="font-semibold" style={{ color: D.ink }}>{Math.round(h.overall_speech_score)} · {friendlyStatus(h.severity_hint).title}</p>
          <p style={{ color: D.soft }}>{new Date(h.created_at).toLocaleDateString()}</p>
        </div>
      )}
    </div>
  );
}

export default function ProgressPage() {
  const { activePatient } = useAuth();
  const [sessions, setSessions] = useState<SessionListItem[] | null>(null);
  const [plan, setPlan] = useState<PlanResponse | null>(null);

  useEffect(() => {
    if (!activePatient) return;
    setSessions(null);
    setPlan(null);
    api.sessions(activePatient.id).then(setSessions).catch(() => setSessions([]));
    api.therapy.plan(activePatient.id).then(setPlan).catch(() => setPlan(null));
  }, [activePatient]);

  if (!activePatient) return <div className="rounded-2xl p-6" style={{ background: D.card, color: D.muted }}>No patient selected.</div>;
  if (!sessions) return <Spinner />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-bold tracking-tight" style={{ color: D.ink }}>My progress</h1>
          <p className="mt-1 text-sm" style={{ color: D.soft }}>{activePatient.full_name} · based only on the exercises and screenings completed with this account.</p>
        </div>
        {plan?.has_profile && (
          <Link to="/therapy/report?print=1" className="inline-flex items-center gap-1.5 rounded-full border px-4 py-1.5 text-sm font-medium"
            style={{ color: D.accent, borderColor: `${D.accent}66` }}>
            <Download size={14} /> Download report (PDF)
          </Link>
        )}
      </div>

      {plan?.has_profile ? <ProgressDark plan={plan} /> : (
        <DCard title="Your therapy dashboard starts after a screening">
          <p className="text-sm" style={{ color: D.soft }}>Complete the three screening tasks – your personal practice plan and these charts appear right after.</p>
          <Link to="/assessment" className="mt-3 inline-flex rounded-lg px-3 py-2 text-sm font-semibold" style={{ background: D.accent, color: "#FFFFFF" }}>Start the screening</Link>
        </DCard>
      )}

      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <DCard title="Screening score over time" subtitle="Overall speech score · dot colour = result of that screening">
          <ScreeningTrend points={sessions} />
        </DCard>
        <DCard title="Your screenings">
          {sessions.length === 0 ? (
            <p className="text-sm" style={{ color: D.muted }}>No screenings yet. <Link to="/assessment" className="font-semibold" style={{ color: D.accent }}>Start your first one</Link>.</p>
          ) : (
            <ul className="divide-y" style={{ borderColor: D.line }}>
              {[...sessions].reverse().slice(0, 6).map((s) => {
                const st = friendlyStatus(s.severity_hint);
                return (
                  <li key={s.session_id} style={{ borderColor: D.line }}>
                    <Link to={`/sessions/${s.session_id}`} className="-mx-2 flex items-center gap-3 rounded-lg px-2 py-3 hover:bg-canvas">
                      <span className="h-3 w-3 shrink-0 rounded-full" style={{ background: st.color }} aria-hidden />
                      <div className="flex-1">
                        <div className="text-sm font-semibold" style={{ color: D.ink }}>{st.title}</div>
                        <div className="text-xs" style={{ color: D.muted }}>{new Date(s.created_at).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })} · {s.recording_count} recordings</div>
                      </div>
                      <ArrowRight size={15} style={{ color: D.accent }} />
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </DCard>
      </div>
    </div>
  );
}
