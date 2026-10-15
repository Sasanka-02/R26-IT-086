/**
 * AdminPatientProfile – one patient's profile header + chronological screening history.
 * Each session links to the technical session dashboard; each recording links to its
 * word-level results. Raw audio is never stored on the server, so it is marked "not retained".
 */
import { useEffect, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, CalendarDays, Image as ImageIcon, MessageSquareText, MessagesSquare, Mic, MicOff, UserRound } from "lucide-react";
import { api } from "../../api/client";
import { ErrorBox, RiskBadge, ScoreRing, Spinner } from "../../components/ui";
import { TASK_LABEL, type AdminPatientProfile as Profile, type TaskType } from "../../types";

const TASK_ICON: Record<TaskType, ReactNode> = {
  reading: <Mic size={15} />,
  picture: <ImageIcon size={15} />,
  scenario: <MessageSquareText size={15} />,
  questions: <MessagesSquare size={15} />,
};
const ACCOUNT_LABEL: Record<string, string> = {
  patient: "Self-registered patient",
  guardian: "Registered by parent / guardian",
  clinician: "Registered by clinician",
  admin: "Admin",
};
const fmtDateTime = (iso: string) => new Date(iso).toLocaleString();
const fmtDur = (s: number) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;

function Info({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide muted">{label}</dt>
      <dd className="mt-0.5 text-sm font-semibold text-ink">{children}</dd>
    </div>
  );
}

export default function AdminPatientProfile() {
  const { patientId = "" } = useParams();
  const [data, setData] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    api.admin.patient(patientId).then(setData).catch((e: Error) => setError(e.message));
  }, [patientId]);

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Spinner />;
  const p = data.patient;
  const qIndex = (recs: Profile["sessions"][number]["recordings"], i: number) =>
    recs.slice(0, i + 1).filter((r) => r.task_type === "questions").length;

  return (
    <div className="space-y-6">
      <Link to="/admin/patients" className="inline-flex items-center gap-1 text-xs font-medium text-ink-muted hover:text-ink"><ArrowLeft size={14} /> All patients</Link>

      {/* profile header */}
      <section className="card p-6">
        <div className="flex flex-col gap-5 md:flex-row md:items-center">
          <span className="grid h-16 w-16 shrink-0 place-items-center rounded-2xl bg-lav-100 text-navy"><UserRound size={30} /></span>
          <div className="flex-1">
            <h1 className="text-2xl font-extrabold text-ink">{p.full_name}</h1>
            <p className="text-sm text-ink-soft">{p.id} · {ACCOUNT_LABEL[p.owner_role] ?? p.owner_role}</p>
          </div>
          <RiskBadge hint={p.latest_severity_hint} label={p.latest_label} />
        </div>
        <dl className="mt-6 grid gap-4 border-t border-line pt-5 sm:grid-cols-2 lg:grid-cols-5">
          <Info label="Age · bracket">{p.age} years{p.age_bracket ? ` · ${p.age_bracket.id} (${p.age_bracket.label})` : ""}</Info>
          <Info label="Date of birth">{new Date(`${data.date_of_birth}T00:00:00`).toLocaleDateString()}</Info>
          <Info label="Registered">{new Date(p.registered_at).toLocaleDateString()}</Info>
          <Info label="Account">{p.owner_name}<span className="block truncate text-xs font-normal muted">{p.owner_email}</span></Info>
          <Info label="Sessions">{p.total_sessions}{p.latest_overall_score !== null && <span className="block text-xs font-normal muted">latest score {p.latest_overall_score.toFixed(0)}/100</span>}</Info>
        </dl>
      </section>

      {/* session history */}
      <section>
        <h2 className="mb-4 flex items-center gap-2 text-lg font-bold"><CalendarDays size={19} className="text-navy" /> Screening history</h2>
        {data.sessions.length === 0 ? (
          <div className="card p-8 text-center text-sm muted">This patient has not completed a screening yet.</div>
        ) : (
          <ol className="relative space-y-5 border-l-2 border-lav-200 pl-6">
            {data.sessions.map((s) => (
              <li key={s.session_id} className="relative">
                <span className="absolute -left-[33px] top-6 h-4 w-4 rounded-full border-4 border-canvas bg-navy" aria-hidden />
                <article className="card p-5">
                  <div className="flex flex-col gap-4 md:flex-row md:items-center">
                    <ScoreRing value={s.overall_speech_score} size={76} stroke={8} />
                    <div className="flex-1">
                      <div className="text-sm font-bold text-ink">{fmtDateTime(s.created_at)}</div>
                      <div className="mt-0.5 text-xs muted">
                        Overall speech score {s.overall_speech_score.toFixed(1)}/100 · ASR confidence {s.overall_confidence_percent.toFixed(1)}% · {s.recording_count} recordings
                      </div>
                      <div className="mt-2"><RiskBadge hint={s.severity_hint} label={s.label} /></div>
                    </div>
                    <Link to={`/admin/patients/${p.id}/sessions/${s.session_id}`} className="btn-primary self-start md:self-center">
                      Open session analysis <ArrowRight size={16} />
                    </Link>
                  </div>

                  <ul className="mt-4 divide-y divide-line rounded-xl border border-line">
                    {s.recordings.map((r, i) => (
                      <li key={r.analysis_id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2.5 text-sm">
                        <span className="grid h-7 w-7 place-items-center rounded-lg bg-lav-100 text-lav-600">{TASK_ICON[r.task_type]}</span>
                        <div className="min-w-0 flex-1">
                          <div className="truncate font-semibold text-ink">
                            {r.task_type === "questions" ? `Question ${qIndex(s.recordings, i)}` : TASK_LABEL[r.task_type]}
                            <span className="font-normal text-ink-soft"> · {r.title}</span>
                          </div>
                          <div className="text-xs muted">{fmtDur(r.duration_sec)} · ASR confidence {r.overall_confidence_percent.toFixed(0)}% · score {r.overall_speech_score.toFixed(0)}</div>
                        </div>
                        <span className="inline-flex items-center gap-1 text-xs text-ink-muted" title="Raw audio is deleted from the server right after analysis (privacy rule)">
                          <MicOff size={13} /> Audio not retained
                        </span>
                        <Link to={`/results/${r.analysis_id}`} className="text-xs font-semibold text-brand hover:underline">Word-level results</Link>
                      </li>
                    ))}
                  </ul>
                </article>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
