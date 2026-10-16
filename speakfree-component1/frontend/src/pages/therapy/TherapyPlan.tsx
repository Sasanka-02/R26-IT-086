/**
 * TherapyPlan – the patient's adaptive therapy plan (Component 4).
 * Built in the backend from the screening (C1 → C2 → C3) and every completed exercise.
 * Patient-safe: shows a friendly focus name, never a disorder label or severity level.
 */
import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, Award, Bot, CalendarDays, CheckCircle2, ClipboardList, Flame, Lock, PlayCircle, RotateCcw, Sparkles, Target, TrendingUp,
} from "lucide-react";
import { api } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { Bar, COLORS, ErrorBox, Spinner } from "../../components/ui";
import { TrendLine } from "../../components/charts";
import type { Exercise, PlanResponse, TherapyPlan as Plan } from "../../types/integration";

export const TYPE_LABEL: Record<string, string> = {
  reading: "Reading", pacing: "Pacing", daf: "Delayed feedback", picture: "Picture talk", clear_speech: "Clear speech",
  loudness: "Loud & clear", sustained_vowel: "Breath support", sound_drill: "Sound practice",
};
const LEVELS = ["beginner", "intermediate", "advanced"];
const LEVEL_NAME: Record<string, string> = { beginner: "Beginner", intermediate: "Intermediate", advanced: "Advanced" };

function ExerciseCard({ ex, big = false }: { ex: Exercise; big?: boolean }) {
  return (
    <Link to={ex.locked ? "#" : `/therapy/exercise/${ex.id}`} aria-disabled={ex.locked}
      className={`group flex flex-col rounded-2xl border bg-white p-4 transition ${ex.locked ? "pointer-events-none border-dashed border-line opacity-60" : "border-line hover:border-brand hover:shadow-lift"}`}>
      {ex.image_url && big && <img src={ex.image_url} alt="" className="mb-3 h-28 w-full rounded-xl object-cover" />}
      <div className="flex flex-wrap gap-1.5">
        <span className="chip bg-lav-100 px-2.5 py-0.5 text-lav-600">{TYPE_LABEL[ex.type] ?? ex.type}</span>
        {ex.level && <span className="chip bg-brand-soft px-2.5 py-0.5 text-navy">{LEVEL_NAME[ex.level]}</span>}
        {ex.locked && <span className="chip bg-canvas px-2.5 py-0.5 text-ink-muted"><Lock size={11} /> Locked</span>}
      </div>
      <h3 className="mt-2 font-bold text-ink">{ex.title}</h3>
      <p className="mt-1 line-clamp-2 text-sm text-ink-soft">{ex.reason ?? ex.description}</p>
      <div className="mt-auto flex items-center justify-between pt-3 text-xs muted">
        <span>{ex.times_practised ? `Practised ${ex.times_practised}× · last ${ex.last_score}` : "New"}</span>
        {!ex.locked && <span className="inline-flex items-center gap-1 font-semibold text-brand">Start <ArrowRight size={13} className="transition group-hover:translate-x-0.5" /></span>}
      </div>
    </Link>
  );
}

function Section({ title, icon, children, right }: { title: string; icon: ReactNode; children: ReactNode; right?: ReactNode }) {
  return (
    <section className="card p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-[15px] font-bold text-ink">{icon}{title}</h2>{right}
      </div>
      {children}
    </section>
  );
}

export default function TherapyPlan() {
  const { activePatient } = useAuth();
  const [data, setData] = useState<PlanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activePatient) return;
    setData(null);
    api.therapy.plan(activePatient.id).then(setData).catch((e: Error) => setError(e.message));
  }, [activePatient]);

  if (!activePatient) return <div className="card p-8 text-center muted">No patient selected.</div>;
  if (error) return <ErrorBox message={error} />;
  if (!data) return <Spinner />;

  if (!data.has_profile) {
    return (
      <div className="card mx-auto max-w-2xl p-10 text-center">
        <span className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-lav-100 text-navy"><ClipboardList size={30} /></span>
        <h1 className="mt-4 text-2xl font-extrabold">Your therapy plan starts with a screening</h1>
        <p className="mt-2 text-ink-soft">Complete the three short speaking tasks. We'll build a personal practice plan from your results – it adapts every time you practise.</p>
        <Link to="/assessment" className="btn-primary mt-6 px-6 py-3">Start the screening <ArrowRight size={16} /></Link>
      </div>
    );
  }
  const plan = data as Plan;
  const { level, progress } = plan;
  const ladder = plan.library.filter((e) => e.type === plan.focus.ladder_type);
  const others = plan.library.filter((e) => e.type !== plan.focus.ladder_type && !e.locked && e.focus.includes(plan.focus.key));
  const firstName = activePatient.full_name.split(" ")[0];

  return (
    <div className="space-y-6">
      {/* focus hero */}
      <section className="overflow-hidden rounded-3xl bg-gradient-to-br from-navy via-[#2A3FB0] to-lav-500 p-6 text-white shadow-nav sm:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center">
          <div className="flex-1">
            <div className="text-xs font-semibold uppercase tracking-widest text-white/70">{firstName}'s therapy plan</div>
            <h1 className="mt-1 text-3xl font-extrabold">{plan.focus.patient_name}</h1>
            <p className="mt-2 max-w-xl text-white/85">{plan.focus.tagline}</p>
            <ul className="mt-4 flex flex-wrap gap-2">
              {plan.focus.techniques.map((t) => <li key={t} className="rounded-full bg-white/15 px-3 py-1 text-xs">{t.split(":")[0]}</li>)}
            </ul>
          </div>
          <div className="grid shrink-0 grid-cols-3 gap-3 text-center">
            {[
              { v: plan.dose.sessions_per_week, l: "days / week" },
              { v: plan.dose.minutes_per_session, l: "minutes" },
              { v: progress.streak_days, l: "day streak" },
            ].map((s) => (
              <div key={s.l} className="rounded-2xl bg-white/12 px-4 py-3 backdrop-blur" style={{ background: "rgba(255,255,255,0.12)" }}>
                <div className="text-2xl font-extrabold">{s.v}</div><div className="text-[11px] text-white/75">{s.l}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {plan.rescreen.recommended && (
        <div className="flex flex-col gap-3 rounded-2xl border border-sun/40 bg-sun-soft p-4 sm:flex-row sm:items-center">
          <RotateCcw className="text-sun" />
          <p className="flex-1 text-sm text-ink"><b>Time for a new screening.</b> It shows how far you've come and updates your plan ({plan.rescreen.reasons.join(", ")}).</p>
          <Link to="/assessment" className="btn-primary">Start screening</Link>
        </div>
      )}

      {/* ★ NOVELTY (Component 4): today's exercises picked by the adaptive plan (bandit + C3 category prior) */}
      {/* today */}
      <Section title="Today's practice" icon={<PlayCircle size={18} className="text-navy" />}
        right={<span className="text-xs muted">{plan.today.length} exercises · about {plan.dose.minutes_per_session} minutes</span>}>
        <div className="grid gap-4 md:grid-cols-3">
          {plan.today.map((ex) => <ExerciseCard key={ex.id} ex={ex} big />)}
        </div>
        <p className="mt-3 flex items-center gap-1.5 text-xs muted"><Sparkles size={13} className="text-lav-500" /> Your plan learns from every exercise you finish and picks what helps you most.</p>
      </Section>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* level ladder */}
        <Section title="Your level" icon={<Award size={18} className="text-navy" />}>
          <ol className="flex items-center gap-2">
            {LEVELS.map((l, i) => {
              const done = i < level.level_index || (level.mastered && i === level.level_index);
              const cur = i === level.level_index && !level.mastered;
              return (
                <li key={l} className="flex flex-1 items-center gap-2">
                  <div className={`flex-1 rounded-xl p-3 text-center text-sm font-semibold ${cur ? "bg-navy text-white shadow-nav" : done ? "bg-ok-soft text-ok" : "bg-canvas text-ink-muted"}`}>
                    {done ? <CheckCircle2 size={16} className="mx-auto mb-1" /> : null}{LEVEL_NAME[l]}
                  </div>
                </li>
              );
            })}
          </ol>
          <p className="mt-3 text-sm text-ink-soft">{level.progress_text}</p>
          <div className="mt-2 flex gap-1.5">
            {Array.from({ length: level.needed_to_advance }).map((_, i) => (
              <span key={i} className="h-2 flex-1 rounded-full" style={{ background: i < level.strong_in_a_row ? COLORS.ok : "#EEF0F7" }} />
            ))}
          </div>
          <h3 className="mt-5 text-xs font-bold uppercase tracking-wide text-ink-muted">Your journey</h3>
          <ol className="mt-2 space-y-1.5 text-sm">
            {[...level.history].reverse().slice(0, 4).map((h, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full" style={{ background: h.direction === "down" ? COLORS.warn : h.direction === "start" ? COLORS.lav : COLORS.ok }} />
                <span className="text-ink-soft">
                  <b className="text-ink">{h.direction === "start" ? `Started at ${h.to}` : h.direction === "mastered" ? "Top level completed" : `${h.direction === "up" ? "Moved up" : "Moved back"} to ${h.to}`}</b>
                  {h.at ? ` · ${new Date(h.at).toLocaleDateString()}` : ""}
                </span>
              </li>
            ))}
          </ol>
        </Section>

        {/* goals */}
        <Section title="Your goals" icon={<Target size={18} className="text-navy" />}>
          <ul className="space-y-3">
            {plan.goals.map((g) => {
              const frac = g.current === null ? 0 : g.id === "pauses" || g.id === "volume" ? (g.current <= g.target ? 100 : Math.max(10, 100 - (g.current - g.target) * 40)) : Math.min(100, (g.current / g.target) * 100);
              return (
                <li key={g.id}>
                  <div className="flex justify-between gap-2 text-sm">
                    <span className={g.met ? "font-semibold text-ok" : "text-ink"}>{g.met && "✓ "}{g.text}</span>
                    <span className="shrink-0 text-xs muted">{g.current ?? "–"} / {g.target} {g.screening_goal ? "" : g.unit}</span>
                  </div>
                  <div className="mt-1"><Bar value={frac} color={g.met ? COLORS.ok : COLORS.lav} className="h-1.5" /></div>
                </li>
              );
            })}
          </ul>
        </Section>
      </div>

      {/* week */}
      <Section title="This week" icon={<CalendarDays size={18} className="text-navy" />}>
        <div className="grid grid-cols-7 gap-2">
          {plan.week.map((d) => (
            <div key={d.date} className={`rounded-xl p-2 text-center sm:p-3 ${d.is_today ? "ring-2 ring-navy" : ""} ${d.active ? "bg-lav-50" : "bg-canvas"}`}>
              <div className="text-xs font-bold text-ink">{d.day}</div>
              <div className="mt-1 text-[11px] muted">{d.active ? `${d.minutes} min` : "Rest"}</div>
              <div className="mt-2 grid h-7 place-items-center">
                {d.completed > 0 ? <CheckCircle2 size={20} className="text-ok" /> : d.active ? <span className="h-2.5 w-2.5 rounded-full bg-lav-200" /> : null}
              </div>
            </div>
          ))}
        </div>
      </Section>

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <Section title="Your progress" icon={<TrendingUp size={18} className="text-navy" />}
          right={<span className="chip bg-lav-100 text-lav-600">{progress.trend.label}</span>}>
          <TrendLine points={progress.history.map((h) => ({ x: String(h.attempt), y: h.score, label: `${h.title} · ${new Date(h.completed_at).toLocaleDateString()}` }))}
            threshold={{ value: level.strong_threshold, label: "strong" }} />
          <p className="mt-2 text-sm text-ink-soft">{progress.trend.detail}</p>
        </Section>
        <section className="flex flex-col justify-between rounded-2xl border-2 border-brand/30 bg-brand-soft p-5">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold text-navy"><Bot size={20} /> Your AI practice assistant</h2>
            <p className="mt-1 text-sm text-ink-soft">Ask how you're doing, what to practise next, or for practice tips for “{plan.focus.patient_name}”.</p>
          </div>
          <Link to="/therapy/assistant" className="btn-primary mt-4">Chat with the assistant <ArrowRight size={15} /></Link>
          <div className="mt-4 flex items-center gap-2 text-xs muted"><Flame size={14} className="text-sun" /> {progress.total_sessions} exercises · {progress.total_minutes} minutes practised</div>
        </section>
      </div>

      {/* library */}
      <Section title="All exercises for you" icon={<ClipboardList size={18} className="text-navy" />}>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[...ladder, ...others].map((ex) => <ExerciseCard key={ex.id} ex={ex} />)}
        </div>
      </Section>
    </div>
  );
}
