import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { COLORS, Spinner } from "../components/ui";
import type { SessionListItem } from "../types";
import { friendlyStatus } from "../utils/friendlyStatus";

/** Overall speech score across screenings – one simple line, no technical metrics. */
function TrendChart({ points }: { points: SessionListItem[] }) {
  const W = 640;
  const H = 220;
  const pad = 32;
  if (points.length < 2) return <p className="text-sm muted">Complete another screening to see how you're progressing over time.</p>;
  const x = (i: number) => pad + (i / (points.length - 1)) * (W - pad * 2);
  const y = (v: number) => H - pad - (v / 100) * (H - pad * 2);
  const path = points.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.overall_speech_score)}`).join("");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Overall speech score across screenings">
      {[0, 25, 50, 75, 100].map((v) => (
        <g key={v}>
          <line x1={pad} x2={W - pad} y1={y(v)} y2={y(v)} stroke="#E6E8F2" />
          <text x={6} y={y(v) + 4} fontSize="10" fill={COLORS.muted}>{v}</text>
        </g>
      ))}
      <path d={path} fill="none" stroke={COLORS.navy} strokeWidth={2.5} />
      {points.map((p, i) => <circle key={p.session_id} cx={x(i)} cy={y(p.overall_speech_score)} r={5} fill={friendlyStatus(p.severity_hint).color} />)}
    </svg>
  );
}

export default function ProgressPage() {
  const { activePatient } = useAuth();
  const [sessions, setSessions] = useState<SessionListItem[] | null>(null);

  useEffect(() => {
    if (!activePatient) return;
    setSessions(null);
    api.sessions(activePatient.id).then(setSessions).catch(() => setSessions([]));
  }, [activePatient]);

  if (!activePatient) return <div className="card p-6 muted">No patient selected.</div>;
  if (!sessions) return <Spinner />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-extrabold tracking-tight">My Progress</h1>
        <p className="mt-1 text-sm text-ink-soft">{activePatient.full_name} · how your speech is developing from one screening to the next.</p>
      </div>
      <section className="card p-6">
        <div className="mb-3 flex flex-wrap gap-5 text-xs font-medium text-ink-soft">
          <span className="flex items-center gap-2"><span className="h-0.5 w-5 bg-navy" /> Overall speech score</span>
          <span>Dot colour = result of that screening</span>
        </div>
        <TrendChart points={sessions} />
      </section>

      <section className="card p-6">
        <h2 className="mb-3 font-bold">Your screenings</h2>
        {sessions.length === 0 ? (
          <p className="text-sm muted">No screenings yet. <Link to="/assessment" className="font-semibold text-brand hover:underline">Start your first one</Link>.</p>
        ) : (
          <ul className="divide-y divide-line">
            {[...sessions].reverse().map((s) => {
              const st = friendlyStatus(s.severity_hint);
              return (
                <li key={s.session_id}>
                  <Link to={`/sessions/${s.session_id}`} className="-mx-2 flex items-center gap-4 rounded-lg px-2 py-3 hover:bg-canvas">
                    <span className="h-3 w-3 shrink-0 rounded-full" style={{ background: st.color }} aria-hidden />
                    <div className="flex-1">
                      <div className="font-semibold" style={{ color: st.color }}>{st.title}</div>
                      <div className="text-xs muted">{new Date(s.created_at).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })} · {s.recording_count} recordings</div>
                    </div>
                    <span className="flex items-center gap-1 text-sm font-semibold text-brand">View results <ArrowRight size={15} /></span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
