/**
 * TherapyPlan – the patient's adaptive therapy plan (Component 4).
 * Built in the backend from the screening (C1 → C2 → C3), the learner's age bracket and every
 * completed exercise. Patient-safe: shows a friendly focus name, never a disorder label or severity level.
 *
 * Age-appropriate look (utils/age.ts THEMES): ages 6–11 bright + big + stars, 12–17 modern + clean,
 * 18+ calm + professional.
 */
import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, Award, Bot, CalendarDays, CheckCircle2, ClipboardList, Flame, HelpCircle, Lock, PlayCircle, RotateCcw, ShieldCheck, Sparkles, Star, Target,
  TrendingUp, UserCheck,
} from "lucide-react";
import { api } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { Bar, COLORS, ErrorBox, Spinner } from "../../components/ui";
import { TrendLine } from "../../components/charts";
import { HomeworkCard, TherapistNotesCard } from "../../components/therapy/TherapistCards";
import UsabilitySurvey from "../../components/therapy/UsabilitySurvey";
import { BRACKETS, themeFor } from "../../utils/age";
import type { Exercise, Goal, PlanResponse, TherapyPlan as Plan } from "../../types/integration";
import { TYPE_EMOJI, TYPE_LABEL } from "./labels";
import { WordLadder } from "./ProgressDashboard";

export { TYPE_EMOJI, TYPE_LABEL };

const CONFIDENCE_TEXT = { low: "still learning", medium: "fairly sure", high: "confident" } as const;

/** Goal bar fill: "at most" goals are full while at or under target and shrink as they go over. */
function goalFill(g: Goal) {
  if (g.current === null) return 0;
  if (g.direction === "at_most") return g.current <= g.target ? 100 : Math.max(10, 100 - (g.current - g.target) * 40);
  return Math.min(100, (g.current / Math.max(g.target, 1e-9)) * 100);
}
const LEVELS = ["beginner", "intermediate", "advanced"];
const LEVEL_NAME: Record<string, string> = { beginner: "Beginner", intermediate: "Intermediate", advanced: "Advanced" };

function ExerciseCard({ ex, big = false, playful = false }: { ex: Exercise; big?: boolean; playful?: boolean }) {
  return (
    <Link to={ex.locked ? "#" : `/therapy/exercise/${ex.id}`} aria-disabled={ex.locked}
      className={`group flex flex-col bg-white p-4 transition ${playful ? "rounded-3xl border-2" : "rounded-2xl border"} ${ex.locked ? "pointer-events-none border-dashed border-line opacity-60" : "border-line hover:border-brand hover:shadow-lift"}`}>
      {ex.image_url && big && <img src={ex.image_url} alt="" className="mb-3 h-28 w-full rounded-xl bg-canvas object-cover" />}
      {big && !ex.image_url && ex.words && (
        <div className="mb-3 flex h-28 items-center justify-center gap-3 rounded-xl bg-sun-soft text-4xl" aria-hidden>{ex.words.slice(0, 4).map((w) => <span key={w.text}>{w.emoji}</span>)}</div>
      )}
      {big && !ex.image_url && !ex.words && (ex.task_type || TYPE_EMOJI[ex.type]) && (
        <div className="mb-3 grid h-28 place-items-center rounded-xl bg-lav-50 text-5xl" aria-hidden>{TYPE_EMOJI[ex.task_type ?? ex.type]}</div>
      )}
      <div className="flex flex-wrap gap-1.5">
        {ex.source === "therapist" && <span className="chip bg-ok-soft px-2.5 py-0.5 text-ok"><UserCheck size={11} /> From your therapist</span>}
        {ex.source === "words" && <span className="chip bg-sun-soft px-2.5 py-0.5 text-warn"><Star size={11} /> Your word level</span>}
        <span className="chip bg-lav-100 px-2.5 py-0.5 text-lav-600">{playful && ex.task_type ? `${TYPE_EMOJI[ex.task_type]} ` : ""}{TYPE_LABEL[ex.type] ?? ex.type}</span>
        {ex.bracket && <span className="chip bg-brand-soft px-2.5 py-0.5 text-navy">Level {ex.bracket}</span>}
        {ex.level && <span className="chip bg-brand-soft px-2.5 py-0.5 text-navy">{LEVEL_NAME[ex.level]}</span>}
        {ex.locked && <span className="chip bg-canvas px-2.5 py-0.5 text-ink-muted"><Lock size={11} /> Locked</span>}
      </div>
      <h3 className={`mt-2 font-bold text-ink ${playful ? "text-lg" : ""}`}>{ex.title}</h3>
      <p className="mt-1 line-clamp-2 text-sm text-ink-soft">
        {ex.locked && ex.unlock_after ? "Do this level's picture description first to unlock this harder scene." : ex.reason ?? ex.description}
      </p>
      {big && ex.predicted_score !== undefined && (
        <p className="mt-2 text-xs font-medium text-lav-600">
          {ex.predicted_score !== null && ex.confidence
            ? `Expected score ≈ ${ex.predicted_score} · ${CONFIDENCE_TEXT[ex.confidence]}`
            : "New for you – the plan is learning what suits you"}
        </p>
      )}
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

/** Level 1–8 ladder: levels above the learner's range (age bracket + 1) are shown locked. */
function BracketLadder({ plan, playful }: { plan: Plan; playful: boolean }) {
  const { level } = plan;
  return (
    <ol className="grid grid-cols-8 gap-1.5" aria-label="Practice levels">
      {BRACKETS.map((b) => {
        const cur = b.id === level.bracket;
        const done = b.id < level.bracket || (cur && level.mastered);
        const out = b.id > level.max_bracket;
        return (
          <li key={b.id} title={`Level ${b.id} · ${b.label}`}
            className={`rounded-xl px-1 py-2 text-center text-xs font-bold ${cur ? "bg-navy text-white shadow-nav" : done ? "bg-ok-soft text-ok" : out ? "bg-canvas text-ink-muted/50" : "bg-canvas text-ink-muted"}`}>
            {done && !cur ? (playful ? "⭐" : <CheckCircle2 size={14} className="mx-auto" />) : out ? <Lock size={12} className="mx-auto" /> : b.id}
            <div className="mt-0.5 hidden text-[9px] font-medium opacity-80 sm:block">{b.label.replace("Ages ", "")}</div>
          </li>
        );
      })}
    </ol>
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
        <p className="mt-2 text-ink-soft">Complete the three short speaking tasks. We'll build a personal practice plan from your results and your age – it adapts every time you practise.</p>
        <Link to="/assessment" className="btn-primary mt-6 px-6 py-3">Start the screening <ArrowRight size={16} /></Link>
      </div>
    );
  }
  const plan = data as Plan;
  const { level, progress, learner } = plan;
  const theme = themeFor(learner.theme);
  const playful = learner.theme === "playful";
  const core = plan.library.filter((e) => e.bracket || e.unlock_after);
  const skill = plan.library.filter((e) => !e.bracket && e.type === plan.focus.ladder_type);
  const extras = plan.library.filter((e) => !e.bracket && !e.unlock_after && e.type !== plan.focus.ladder_type && !e.locked && e.focus.includes(plan.focus.key));
  const firstName = activePatient.full_name.split(" ")[0];

  return (
    <div className="space-y-6">
      {/* focus hero – the look follows the learner's age bracket */}
      <section className={`overflow-hidden rounded-3xl p-6 text-white shadow-nav sm:p-8 ${theme.hero}`}>
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center">
          <div className="flex-1">
            <div className="text-xs font-semibold uppercase tracking-widest text-white/75">{firstName}'s therapy plan · {learner.age_label}</div>
            <h1 className={`mt-1 font-extrabold ${playful ? "text-4xl" : "text-3xl"}`}>{theme.emoji && `${theme.emoji} `}{plan.focus.patient_name}</h1>
            <p className="mt-2 max-w-xl text-white/85">{plan.focus.tagline}</p>
            {/* ★ NOVELTY (Component 4): plain-language age-bracket level */}
            <p className="mt-4 max-w-xl rounded-2xl bg-white/15 px-4 py-3 text-sm font-semibold" style={{ background: "rgba(255,255,255,0.15)" }}>
              <Award size={16} className="mr-1.5 inline -translate-y-0.5" />{level.dashboard_text}
            </p>
          </div>
          <div className="grid shrink-0 grid-cols-3 gap-3 text-center">
            {[
              { v: plan.dose.sessions_per_week, l: "days / week" },
              { v: plan.dose.minutes_per_session, l: "minutes" },
              { v: progress.streak_days, l: "day streak" },
            ].map((s) => (
              <div key={s.l} className="rounded-2xl px-4 py-3 backdrop-blur" style={{ background: "rgba(255,255,255,0.12)" }}>
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

      <TherapistNotesCard patientId={activePatient.id} />
      <HomeworkCard homework={plan.homework} />

      {/* ★ NOVELTY (Component 4): today's exercises – the age bracket's reading / picture / conversation tasks, ordered by the bandit, plus extra practice */}
      <Section title={playful ? "Today's fun practice" : "Today's practice"} icon={<PlayCircle size={18} className="text-navy" />}
        right={<span className="text-xs muted">{plan.today.length} exercises · about {plan.dose.minutes_per_session} minutes</span>}>
        <div className="grid gap-4 md:grid-cols-3">
          {plan.today.map((ex) => <ExerciseCard key={ex.id} ex={ex} big playful={playful} />)}
        </div>
        <p className="mt-3 flex items-center gap-1.5 text-xs muted"><Sparkles size={13} className="text-lav-500" /> Your plan learns from every exercise you finish and picks what helps you most.</p>
        <details className="mt-4 rounded-xl border border-lav-200 bg-lav-50 px-4 py-3" open={playful ? undefined : true}>
          <summary className="flex cursor-pointer items-center gap-1.5 text-sm font-bold text-ink"><HelpCircle size={15} className="text-lav-600" /> Why this plan for you?</summary>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink">{plan.why.map((line) => <li key={line}>{line}</li>)}</ul>
        </details>
      </Section>

      {plan.word_level && <WordLadder words={plan.word_level} />}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* level ladder */}
        <Section title="Your level" icon={<Award size={18} className="text-navy" />}
          right={level.override ? <span className="chip bg-ok-soft text-ok"><UserCheck size={12} /> Set by your therapist</span> : undefined}>
          <BracketLadder plan={plan} playful={playful} />
          <p className="mt-3 text-sm text-ink-soft">{level.progress_text}</p>
          <div className="mt-2 flex gap-1.5">
            {Array.from({ length: level.needed_to_advance }).map((_, i) => (
              playful
                ? <Star key={i} size={22} className={i < level.strong_in_a_row ? "fill-sun text-sun" : "text-line"} />
                : <span key={i} className="h-2 flex-1 rounded-full" style={{ background: i < level.strong_in_a_row ? COLORS.ok : "#EEF0F7" }} />
            ))}
          </div>
          {plan.skill_level && (
            <div className="mt-4 rounded-xl bg-canvas p-3">
              <div className="text-xs font-bold uppercase tracking-wide text-ink-muted">Skill steps · {TYPE_LABEL[plan.focus.ladder_type]}</div>
              <ol className="mt-2 flex gap-1.5">
                {LEVELS.map((l, i) => (
                  <li key={l} className={`flex-1 rounded-lg p-1.5 text-center text-xs font-semibold ${i === plan.skill_level!.level_index ? "bg-navy text-white" : i < plan.skill_level!.level_index ? "bg-ok-soft text-ok" : "bg-white text-ink-muted"}`}>{LEVEL_NAME[l]}</li>
                ))}
              </ol>
              <p className="mt-2 text-xs text-ink-soft">{plan.skill_level.progress_text}</p>
            </div>
          )}
          <h3 className="mt-5 text-xs font-bold uppercase tracking-wide text-ink-muted">Your journey</h3>
          <ol className="mt-2 space-y-1.5 text-sm">
            {[...level.history].reverse().slice(0, 4).map((h, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full" style={{ background: h.direction === "down" ? COLORS.warn : h.direction === "start" || h.direction === "therapist" ? COLORS.lav : COLORS.ok }} />
                <span className="text-ink-soft">
                  <b className="text-ink">{h.direction === "start" ? `Started at ${h.to}` : h.direction === "mastered" ? "Top level completed" : h.direction === "therapist" ? `Your therapist set ${h.to}` : `${h.direction === "up" ? "Moved up" : "Moved back"} to ${h.to}`}</b>
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
              const frac = goalFill(g);
              return (
                <li key={g.id}>
                  <div className="flex justify-between gap-2 text-sm">
                    <span className={g.met ? "font-semibold text-ok" : "text-ink"}>{g.met && "✓ "}{g.text}
                      {g.source === "therapist" && <span className="chip ml-1.5 bg-ok-soft px-2 py-0 text-[10px] text-ok"><UserCheck size={10} /> therapist</span>}</span>
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
      <Section title="This week" icon={<CalendarDays size={18} className="text-navy" />}
        right={<span className="text-xs muted">Every practice day: your Level {level.bracket} reading, picture and conversation + extra practice</span>}>
        <div className="grid grid-cols-7 gap-2">
          {plan.week.map((d) => (
            <div key={d.date} className={`rounded-xl p-2 text-center sm:p-3 ${d.is_today ? "ring-2 ring-navy" : ""} ${d.active ? "bg-lav-50" : "bg-canvas"}`}
              title={d.exercises.map((e) => e.title).join(" · ")}>
              <div className="text-xs font-bold text-ink">{d.day}</div>
              <div className="mt-1 text-[11px] muted">{d.active ? `${d.minutes} min · ${d.exercises.length} ex` : "Rest"}</div>
              <div className="mt-2 grid h-7 place-items-center">
                {d.completed > 0 ? (playful ? <span className="text-lg">⭐</span> : <CheckCircle2 size={20} className="text-ok" />) : d.active ? <span className="h-2.5 w-2.5 rounded-full bg-lav-200" /> : null}
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
      <Section title="All exercises for you" icon={<ClipboardList size={18} className="text-navy" />}
        right={<span className="text-xs muted">Level {level.bracket} tasks ({level.ages}) + extra practice</span>}>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[...core, ...skill, ...extras].map((ex) => <ExerciseCard key={ex.id} ex={ex} playful={playful} />)}
        </div>
      </Section>

      <UsabilitySurvey />
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs muted">
        <span className="flex items-center gap-1.5"><ShieldCheck size={14} /> Your voice stays on this device during practice – only numbers are saved.</span>
        <span className="flex gap-4">
          <Link to="/progress" className="font-semibold text-brand hover:underline">My progress dashboard →</Link>
          <Link to="/therapy/privacy" className="font-semibold text-brand hover:underline">Privacy & my data →</Link>
        </span>
      </div>
    </div>
  );
}
