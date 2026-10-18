import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Bot, ClipboardList, Flame, HeartPulse, Image as ImageIcon, MessageSquareText, MessagesSquare, ShieldCheck, Sparkles } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useAssessment } from "../context/AssessmentContext";
import { ScoreRing } from "../components/ui";
import { friendlyStatus } from "../utils/friendlyStatus";
import type { SessionListItem } from "../types";
import type { PlanResponse } from "../types/integration";
import { BRACKETS } from "../utils/age";

export default function DashboardHome() {
  const { user, activePatient } = useAuth();
  const { completedCount, required } = useAssessment();
  const [sessions, setSessions] = useState<SessionListItem[] | null>(null);
  const [plan, setPlan] = useState<PlanResponse | null>(null);

  useEffect(() => {
    if (!activePatient) return;
    setSessions(null);
    setPlan(null);
    api.sessions(activePatient.id).then(setSessions).catch(() => setSessions([]));
    api.therapy.plan(activePatient.id).then(setPlan).catch(() => setPlan(null));
  }, [activePatient]);

  const bracket = BRACKETS.find((b) => b.id === activePatient?.age_bracket?.id);
  const latest = sessions?.length ? sessions[sessions.length - 1] : null;
  const recent = sessions ? [...sessions].reverse().slice(0, 5) : [];
  const progress = required.length ? Math.round((completedCount / required.length) * 100) : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-extrabold tracking-tight">Hello, {user?.full_name.split(" ")[0]} 👋</h1>
        <p className="mt-1 text-sm text-ink-soft">Welcome to SpeakFree – AI-based speech screening, adaptive therapy and practice support.</p>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <section className="card relative overflow-hidden p-6 lg:col-span-2">
          <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-lav-50" aria-hidden />
          {activePatient ? (
            <div className="relative">
              <div className="text-xs font-bold uppercase tracking-wider text-lav-600">Active patient</div>
              <div className="mt-1 text-2xl font-extrabold">{activePatient.full_name}</div>
              <div className="mt-1 text-sm muted">ID {activePatient.id} · Age {activePatient.age ?? "not set"}{activePatient.date_of_birth ? ` · DOB ${activePatient.date_of_birth}` : ""}</div>
              {bracket && (
                <div className="mt-4 rounded-xl border border-lav-200 bg-lav-50 p-4">
                  <div className="text-sm font-bold text-navy">Age bracket {bracket.id} · {bracket.label}</div>
                  <div className="mt-1 text-sm text-ink-soft">{bracket.focus}</div>
                </div>
              )}
              <div className="mt-5 flex flex-wrap items-center gap-4">
                <Link to="/assessment" className="btn-primary px-5 py-3">
                  <ClipboardList size={18} /> {completedCount > 0 ? "Continue assessment" : latest ? "Start a new screening" : "Start assessment"} <ArrowRight size={16} />
                </Link>
                {completedCount > 0 && (
                  <div className="min-w-[180px] flex-1">
                    <div className="mb-1 text-xs font-medium text-ink-soft">{completedCount} of {required.length} recordings · {progress}%</div>
                    <div className="h-2 rounded-full bg-lav-100"><div className="h-2 rounded-full bg-lav-600" style={{ width: `${progress}%` }} /></div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="relative">
              <div className="text-xl font-bold">Add your first patient</div>
              <p className="mt-2 muted">Use “Add patient” in the top bar. The age bracket and tasks are set automatically from the age.</p>
            </div>
          )}
        </section>

        <section className="card p-6">
          <div className="text-sm font-bold text-ink-soft">Latest screening</div>
          {latest ? (
            <Link to={`/sessions/${latest.session_id}`} className="mt-3 block">
              <div className="flex items-center gap-4">
                <ScoreRing value={latest.overall_speech_score} size={96} stroke={10} color={friendlyStatus(latest.severity_hint).color} />
                <div>
                  <div className="text-xl font-extrabold" style={{ color: friendlyStatus(latest.severity_hint).color }}>{friendlyStatus(latest.severity_hint).title}</div>
                  <div className="mt-1 text-xs muted">{new Date(latest.created_at).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })}</div>
                </div>
              </div>
              <div className="mt-4 text-sm font-semibold text-brand">See your results and next steps →</div>
            </Link>
          ) : (
            <p className="mt-3 text-sm muted">{sessions === null ? "Loading…" : "No screening analysed yet. Complete the three tasks and press Analyse Now."}</p>
          )}
        </section>
      </div>

      {/* Component 4: today's adaptive therapy practice (after the first screening) */}
      {plan?.has_profile && (
        <section className="flex flex-col gap-5 rounded-2xl bg-gradient-to-br from-navy to-lav-500 p-6 text-white shadow-nav md:flex-row md:items-center">
          <span className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-white/15"><HeartPulse size={28} /></span>
          <div className="flex-1">
            <div className="text-xs font-semibold uppercase tracking-widest text-white/70">Your therapy plan · {plan.focus.patient_name}</div>
            <div className="mt-1 text-xl font-extrabold">Today: {plan.today.map((e) => e.title.split(" - ")[0]).join(" · ")}</div>
            <div className="mt-1 text-sm font-semibold text-white/90">{plan.level.dashboard_text}</div>
            <div className="mt-1 flex flex-wrap gap-4 text-sm text-white/80">
              <span>{plan.level.label} · {plan.level.ages} tasks</span>
              <span className="inline-flex items-center gap-1"><Flame size={14} /> {plan.progress.streak_days}-day streak</span>
              <span>{plan.progress.total_sessions} exercises done</span>
            </div>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Link to={`/therapy/exercise/${plan.today[0].id}`} className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-bold text-navy hover:bg-lav-50">Start today's practice <ArrowRight size={16} /></Link>
            <Link to="/therapy/assistant" className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/40 px-4 py-3 text-sm font-semibold hover:bg-white/10"><Bot size={16} /> Assistant</Link>
          </div>
        </section>
      )}

      <div className="grid gap-5 md:grid-cols-3">
        {[
          { icon: <ImageIcon size={20} />, title: "Picture Description", text: "Describe an age-matched scene in your own words." },
          { icon: <MessageSquareText size={20} />, title: "Scenario Description", text: "Explain what you would do in an everyday situation." },
          { icon: <MessagesSquare size={20} />, title: "Pre-defined Questions", text: "Answer three short questions, one recording each." },
        ].map((c, i) => (
          <div key={c.title} className="card flex gap-3 p-5">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-lav-100 text-navy">{c.icon}</span>
            <div>
              <div className="font-bold">{i + 1}. {c.title}</div>
              <div className="text-sm text-ink-soft">{c.text}</div>
            </div>
          </div>
        ))}
      </div>

      <section className="card p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-bold">Recent screenings</h2>
          <Link to="/progress" className="text-sm font-semibold text-brand hover:underline">See progress →</Link>
        </div>
        {recent.length === 0 ? (
          <p className="text-sm muted">No screenings yet.</p>
        ) : (
          <ul className="divide-y divide-line">
            {recent.map((s) => (
              <li key={s.session_id}>
                <Link to={`/sessions/${s.session_id}`} className="-mx-2 flex items-center justify-between gap-4 rounded-lg px-2 py-3 hover:bg-canvas">
                  <div className="flex items-center gap-3">
                    <span className="grid h-9 w-9 place-items-center rounded-xl bg-lav-100 text-lav-600"><Sparkles size={16} /></span>
                    <div>
                      <div className="font-semibold">Screening · {s.recording_count} recordings</div>
                      <div className="text-xs muted">{new Date(s.created_at).toLocaleString()}</div>
                    </div>
                  </div>
                  <div className="text-right text-sm font-bold" style={{ color: friendlyStatus(s.severity_hint).color }}>{friendlyStatus(s.severity_hint).title}</div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="flex items-center gap-2 text-xs muted"><ShieldCheck size={14} /> Raw audio is deleted from the server right after analysis. Only derived scores are stored.</p>
    </div>
  );
}
