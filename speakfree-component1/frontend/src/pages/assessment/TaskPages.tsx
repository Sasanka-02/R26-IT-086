/**
 * The three assessment pages:
 *   1. Picture Description   2. Scenario Description   3. Pre-defined Questions
 * plus the shared stepper that leads to step 4, "Analyse".
 */
import { useState, type ReactNode } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, CheckCircle2, Mic, Sparkles } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useAssessment } from "../../context/AssessmentContext";
import Recorder from "../../components/Recorder";
import { ErrorBox, SceneVisual, Spinner, StepBadge } from "../../components/ui";
import type { TaskType } from "../../types";

// =========================================================================== stepper
const STEPS = [
  { to: "/assessment/picture", label: "Picture Description" },
  { to: "/assessment/scenario", label: "Scenario Description" },
  { to: "/assessment/questions", label: "Pre-defined Questions" },
  { to: "/assessment/analyse", label: "Analyse" },
];

export function AssessmentStepper() {
  const { session, taskSet } = useAssessment();
  const rec = session?.recordings ?? {};
  const qItems = taskSet?.tasks.questions.items ?? [];
  const done = [!!rec.picture, !!rec.scenario, qItems.length > 0 && qItems.every((q) => rec[q.id]), false];
  return (
    <nav aria-label="Assessment steps" className="card overflow-x-auto px-4 py-3 scrollbar-thin">
      <ol className="flex min-w-max items-center gap-2">
        {STEPS.map((s, i) => (
          <li key={s.to} className="flex items-center gap-2">
            <NavLink to={s.to} className={({ isActive }) => `flex items-center gap-2 rounded-xl px-2.5 py-1.5 text-sm font-semibold transition ${isActive ? "bg-lav-100 text-navy" : "text-ink-soft hover:bg-canvas"}`}>
              <span className={`grid h-6 w-6 place-items-center rounded-full text-xs font-bold text-white ${done[i] ? "bg-ok" : i === 3 ? "bg-brand" : "bg-navy"}`}>
                {done[i] ? <CheckCircle2 size={14} /> : i === 3 ? <Sparkles size={12} /> : i + 1}
              </span>
              {s.label}
            </NavLink>
            {i < STEPS.length - 1 && <span className="h-px w-6 bg-line sm:w-10" aria-hidden />}
          </li>
        ))}
      </ol>
    </nav>
  );
}

// =========================================================================== shared frame
function useReady() {
  const { activePatient } = useAuth();
  const a = useAssessment();
  if (!activePatient) return { node: <div className="card p-8 text-center muted">No patient selected.</div>, a };
  if (a.taskError) return { node: <ErrorBox message={a.taskError} />, a };
  if (!a.taskSet || !a.session) return { node: <Spinner />, a };
  return { node: null, a };
}

function TaskFrame({ step, title, subtitle, children, recorder, back, next }: {
  step: number; title: string; subtitle: string; children: ReactNode; recorder: ReactNode;
  back: { to: string; label: string }; next: { to: string; label: string; ready: boolean };
}) {
  const navigate = useNavigate();
  return (
    <div className="space-y-6">
      <div>
        <Link to="/assessment" className="mb-2 inline-flex items-center gap-1 text-xs font-medium text-ink-muted hover:text-ink"><ArrowLeft size={14} /> All tasks</Link>
        <h1 className="text-[28px] font-extrabold tracking-tight">Assessment Tasks</h1>
      </div>
      <AssessmentStepper />
      <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
        <section className="card p-6">
          <div className="mb-1 flex items-center gap-3">
            <StepBadge n={step} />
            <h2 className="text-xl font-bold">{title}</h2>
          </div>
          <p className="mb-5 pl-11 text-sm text-ink-soft">{subtitle}</p>
          {children}
        </section>
        <aside className="card flex flex-col p-6">
          <h3 className="mb-4 flex items-center gap-2 font-bold"><Mic size={17} className="text-lav-500" /> Your recording</h3>
          {recorder}
        </aside>
      </div>
      <div className="flex items-center justify-between">
        <Link to={back.to} className="btn-ghost"><ArrowLeft size={16} /> {back.label}</Link>
        <button className={next.ready ? "btn-primary" : "btn-ghost"} onClick={() => navigate(next.to)}>
          {next.ready ? "Save & Continue" : "Skip for now"} <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}

function SingleRecorder({ keyName, taskType, taskId, maxSeconds }: { keyName: string; taskType: TaskType; taskId: string; maxSeconds: number }) {
  const { session, saveRecording, removeRecording } = useAssessment();
  const saved = session?.recordings[keyName];
  return (
    <Recorder
      key={keyName}
      maxSeconds={maxSeconds}
      saved={saved}
      onSave={(a) => saveRecording({ key: keyName, taskType, taskId, ...a })}
      onClear={() => removeRecording(keyName)}
    />
  );
}

// =========================================================================== 1. picture
export function PicturePage() {
  const { node, a } = useReady();
  if (node) return node;
  const t = a.taskSet!.tasks.picture;
  return (
    <TaskFrame step={1} title="Picture Description" subtitle={t.instructions}
      back={{ to: "/assessment", label: "All tasks" }}
      next={{ to: "/assessment/scenario", label: "Scenario", ready: !!a.session!.recordings.picture }}
      recorder={<SingleRecorder keyName="picture" taskType="picture" taskId={t.id} maxSeconds={t.max_seconds} />}>
      <div className="mb-3 text-sm font-semibold text-navy">{t.title}</div>
      <SceneVisual visual={t.visual} imageUrl={t.image_url} tone="park" className="h-72" />
      <div className="mt-4 rounded-xl bg-lav-50 p-4 text-sm text-ink-soft">
        <b className="text-ink">Try to mention:</b> who is in the picture, what they are doing, where they are, and what might happen next.
        Speak for as long as you like, up to {Math.round(t.max_seconds / 60 * 10) / 10} minutes.
      </div>
    </TaskFrame>
  );
}

// =========================================================================== 2. scenario
export function ScenarioPage() {
  const { node, a } = useReady();
  if (node) return node;
  const t = a.taskSet!.tasks.scenario;
  return (
    <TaskFrame step={2} title="Scenario Description" subtitle={t.instructions}
      back={{ to: "/assessment/picture", label: "Picture" }}
      next={{ to: "/assessment/questions", label: "Questions", ready: !!a.session!.recordings.scenario }}
      recorder={<SingleRecorder keyName="scenario" taskType="scenario" taskId={t.id} maxSeconds={t.max_seconds} />}>
      <div className="mb-3 text-sm font-semibold text-navy">{t.title}</div>
      <SceneVisual visual={t.visual} imageUrl={t.image_url} alt={t.title} tone="indoor" className="h-56" />
      <blockquote className="mt-4 rounded-xl border-l-4 border-lav-500 bg-lav-50 p-4 text-[15px] leading-relaxed text-ink">{t.prompt}</blockquote>
    </TaskFrame>
  );
}

// =========================================================================== 3. pre-defined questions
export function QuestionsPage() {
  const { node, a } = useReady();
  const [index, setIndex] = useState(0);
  const navigate = useNavigate();
  if (node) return node;
  const t = a.taskSet!.tasks.questions;
  const rec = a.session!.recordings;
  const q = t.items[Math.min(index, t.items.length - 1)];
  const answered = t.items.filter((i) => rec[i.id]).length;
  const isLast = index >= t.items.length - 1;

  return (
    <div className="space-y-6">
      <div>
        <Link to="/assessment" className="mb-2 inline-flex items-center gap-1 text-xs font-medium text-ink-muted hover:text-ink"><ArrowLeft size={14} /> All tasks</Link>
        <h1 className="text-[28px] font-extrabold tracking-tight">Assessment Tasks</h1>
      </div>
      <AssessmentStepper />
      <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
        <section className="card p-6">
          <div className="mb-1 flex items-center gap-3">
            <StepBadge n={3} />
            <h2 className="text-xl font-bold">Pre-defined Questions</h2>
            <span className="chip ml-auto bg-lav-100 text-lav-600">{answered} / {t.items.length} answered</span>
          </div>
          <p className="mb-5 pl-11 text-sm text-ink-soft">{t.instructions}</p>

          <div className="mb-5 flex flex-wrap gap-2" role="tablist">
            {t.items.map((item, i) => (
              <button key={item.id} role="tab" aria-selected={i === index} onClick={() => setIndex(i)}
                className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-semibold transition ${i === index ? "border-navy bg-navy text-white" : "border-line bg-white text-ink-soft hover:bg-canvas"}`}>
                {rec[item.id] ? <CheckCircle2 size={15} className={i === index ? "text-white" : "text-ok"} /> : <span className="font-mono text-xs">Q{i + 1}</span>}
                Question {i + 1}
              </button>
            ))}
          </div>

          <div className="rounded-2xl bg-gradient-to-br from-lav-50 to-lav-100 p-6">
            <div className="text-xs font-bold uppercase tracking-wider text-lav-600">Question {index + 1} of {t.items.length}</div>
            <p className="mt-2 text-2xl font-bold leading-snug text-ink">{q.prompt}</p>
            <p className="mt-3 text-xs text-ink-soft">Answer in full sentences. Up to {q.max_seconds} seconds.</p>
          </div>
        </section>
        <aside className="card flex flex-col p-6">
          <h3 className="mb-4 flex items-center gap-2 font-bold"><Mic size={17} className="text-lav-500" /> Your answer</h3>
          <SingleRecorder keyName={q.id} taskType="questions" taskId={q.id} maxSeconds={q.max_seconds} />
        </aside>
      </div>
      <div className="flex items-center justify-between">
        {index > 0
          ? <button className="btn-ghost" onClick={() => setIndex(index - 1)}><ArrowLeft size={16} /> Previous question</button>
          : <Link to="/assessment/scenario" className="btn-ghost"><ArrowLeft size={16} /> Scenario</Link>}
        {isLast ? (
          <button className="btn-primary" onClick={() => navigate("/assessment/analyse")}>Continue to Analyse <ArrowRight size={16} /></button>
        ) : (
          <button className={rec[q.id] ? "btn-primary" : "btn-ghost"} onClick={() => setIndex(index + 1)}>
            {rec[q.id] ? "Next question" : "Skip for now"} <ArrowRight size={16} />
          </button>
        )}
      </div>
    </div>
  );
}
