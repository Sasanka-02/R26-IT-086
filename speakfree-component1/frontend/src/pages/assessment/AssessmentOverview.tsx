/**
 * Assessment Tasks overview – the three screening tasks as cards (mock-up layout), overall progress,
 * and the "Analyse Now" hand-off once every recording is captured.
 */
import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CheckCircle2, FileText, Image as ImageIcon, MessageSquareText, MessagesSquare, Sparkles, X } from "lucide-react";
import { api } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useAssessment } from "../../context/AssessmentContext";
import { ErrorBox, SceneVisual, Spinner, StepBadge } from "../../components/ui";

// Pre-load Whisper in the background the first time someone opens the tasks, so "Analyse Now" is faster.
let warmedUp = false;
function warmupOnce() {
  if (warmedUp) return;
  warmedUp = true;
  api.warmup().catch(() => { warmedUp = false; });
}

export function QuestionsIllustration({ count, className = "h-44" }: { count: number; className?: string }) {
  return (
    <div className={`relative overflow-hidden rounded-xl border border-line bg-gradient-to-br from-lav-50 to-lav-100 ${className}`} aria-hidden>
      <div className="absolute inset-0 flex flex-col justify-center gap-2.5 px-6">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className={`flex items-center gap-2 ${i % 2 ? "justify-end" : ""}`}>
            {i % 2 === 0 && <span className="grid h-7 w-7 place-items-center rounded-full bg-navy text-xs font-bold text-white">Q{i + 1}</span>}
            <div className={`h-7 rounded-2xl ${i % 2 ? "bg-lav-500/80" : "bg-white"} shadow-sm`} style={{ width: `${55 + ((i * 17) % 30)}%` }} />
            {i % 2 === 1 && <span className="grid h-7 w-7 place-items-center rounded-full bg-sun text-xs font-bold text-white">A</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

function TaskCard({ n, title, subtitle, done, status, children, to, action, icon }: {
  n: number; title: string; subtitle: string; done: boolean; status: string; children: ReactNode; to: string; action: string; icon: ReactNode;
}) {
  return (
    <section className={`card flex flex-col p-5 transition hover:shadow-lift ${done ? "ring-2 ring-ok/30" : ""}`}>
      <div className="mb-1 flex items-center gap-3">
        <StepBadge n={n} done={done} />
        <h2 className="text-lg font-bold">{title}</h2>
      </div>
      <p className="mb-4 pl-11 text-[13px] leading-snug text-ink-soft">{subtitle}</p>
      <div className="flex-1">{children}</div>
      <div className={`chip mt-4 self-start ${done ? "bg-ok-soft text-ok" : "bg-canvas text-ink-muted"}`}>
        {done && <CheckCircle2 size={13} />} {status}
      </div>
      <Link to={to} className="btn-outline mt-3 w-full py-3">{icon} {action}</Link>
    </section>
  );
}

function InstructionsModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/40 px-4" role="dialog" aria-modal onClick={onClose}>
      <div className="card w-full max-w-lg p-6" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-bold">How the screening works</h2>
          <button onClick={onClose} className="text-ink-muted" aria-label="Close"><X size={18} /></button>
        </div>
        <ol className="list-decimal space-y-2 pl-5 text-sm text-ink-soft">
          <li><b className="text-ink">Picture Description</b> – look at the picture and describe it in your own words.</li>
          <li><b className="text-ink">Scenario Description</b> – read the situation and explain what you would do.</li>
          <li><b className="text-ink">Pre-defined Questions</b> – answer each short question with one recording.</li>
          <li>When every task is recorded, press <b className="text-ink">Analyse Now</b>. SpeakFree transcribes each recording with Whisper, scores the confidence of every word, and shows your results.</li>
        </ol>
        <div className="mt-4 rounded-xl bg-lav-50 p-3 text-xs text-ink-soft">
          Tips: find a quiet room, keep the microphone 20–30 cm away, and speak at your normal pace. You can listen back and re-record any task before analysing.
          Recordings stay in this browser until you analyse, and are deleted from the server right after analysis.
        </div>
      </div>
    </div>
  );
}

export default function AssessmentOverview() {
  const { activePatient, user } = useAuth();
  const { taskSet, taskError, session, required, completedCount, allRecorded } = useAssessment();
  const navigate = useNavigate();
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    warmupOnce();
  }, []);

  if (!activePatient) {
    return (
      <div className="card p-8 text-center">
        <h1 className="text-xl font-bold">No patient yet</h1>
        <p className="mt-2 muted">{user?.role === "patient" ? "Your account has no patient profile." : "Use “Add patient” in the top bar to create your first patient."}</p>
      </div>
    );
  }
  if (taskError) return <ErrorBox message={taskError} />;
  if (!taskSet || !session) return <Spinner />;

  const { picture, scenario, questions } = taskSet.tasks;
  const rec = session.recordings;
  const answered = questions.items.filter((q) => rec[q.id]).length;
  const progress = required.length ? Math.round((completedCount / required.length) * 100) : 0;
  const whose = activePatient.is_self ? "your" : `${activePatient.full_name}'s`;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 className="text-[28px] font-extrabold tracking-tight text-ink">Assessment Tasks</h1>
          <p className="mt-1 text-sm text-ink-soft">Complete the tasks below to help us understand {whose} speech and communication.</p>
          <span className="chip mt-3 bg-lav-100 text-lav-600">Age {taskSet.age} · {taskSet.age_bracket.label} · Bracket {taskSet.age_bracket.id}</span>
        </div>
        <div className="card w-full p-4 md:w-80">
          <div className="text-sm font-semibold">Overall Progress</div>
          <div className="mt-2 flex items-center gap-3">
            <div className="h-2 flex-1 rounded-full bg-lav-100">
              <div className="h-2 rounded-full bg-lav-600 transition-all" style={{ width: `${progress}%` }} />
            </div>
            <span className="whitespace-nowrap text-xs font-medium text-ink-soft">{progress}% Complete</span>
          </div>
          <div className="mt-1.5 text-[11px] muted">{completedCount} of {required.length} recordings captured</div>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <TaskCard n={1} title="Picture Description" subtitle={picture.instructions} done={!!rec.picture}
          status={rec.picture ? "Recorded" : "Not started"} to="/assessment/picture" action="Describe the Picture" icon={<ImageIcon size={17} />}>
          <SceneVisual visual={picture.visual} imageUrl={picture.image_url} tone="park" />
        </TaskCard>
        <TaskCard n={2} title="Scenario Description" subtitle={scenario.instructions} done={!!rec.scenario}
          status={rec.scenario ? "Recorded" : "Not started"} to="/assessment/scenario" action="Describe the Scenario" icon={<MessageSquareText size={17} />}>
          <SceneVisual visual={scenario.visual} imageUrl={scenario.image_url} alt={scenario.title} tone="indoor" />
        </TaskCard>
        <TaskCard n={3} title="Pre-defined Questions" subtitle={`Answer ${questions.items.length} short questions, one recording each.`} done={answered === questions.items.length}
          status={`${answered} of ${questions.items.length} answered`} to="/assessment/questions" action="Answer the Questions" icon={<MessagesSquare size={17} />}>
          <QuestionsIllustration count={questions.items.length} />
        </TaskCard>
      </div>

      {/* Analyse Now */}
      <section className={`card flex flex-col gap-4 p-5 sm:flex-row sm:items-center ${allRecorded ? "border-brand/40 bg-brand-soft/40" : ""}`}>
        <div className={`grid h-12 w-12 shrink-0 place-items-center rounded-2xl ${allRecorded ? "bg-brand text-white" : "bg-canvas text-ink-muted"}`}>
          <Sparkles size={22} />
        </div>
        <div className="flex-1">
          <div className="font-bold">{allRecorded ? "All tasks recorded – ready for analysis" : "Analyse your speech"}</div>
          <p className="text-sm text-ink-soft">
            {allRecorded
              ? "Run the Component 1 analysis: Whisper transcription, word-level ASR confidence and acoustic features for every recording."
              : `Record all ${required.length} tasks to unlock the analysis (${required.length - completedCount} remaining).`}
          </p>
          {!allRecorded && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {required.filter((r) => !rec[r.key]).map((r) => (
                <Link key={r.key} to={r.taskType === "questions" ? "/assessment/questions" : `/assessment/${r.taskType}`}
                  className="chip bg-sun-soft text-warn hover:brightness-95" title={r.label}>
                  Missing: {r.label.split(" – ")[0]}
                </Link>
              ))}
            </div>
          )}
        </div>
        <button className="btn-primary px-6 py-3 text-[15px]" disabled={!allRecorded}
          onClick={() => navigate("/assessment/analyse", { state: { autostart: true } })}>
          <Sparkles size={17} /> Analyse Now
        </button>
      </section>

      <div className="flex flex-col gap-3 rounded-2xl border border-lav-200 bg-lav-50 p-4 sm:flex-row sm:items-center">
        <Sparkles className="shrink-0 text-lav-500" size={26} />
        <div className="flex-1">
          <div className="text-sm font-bold">Important</div>
          <p className="text-xs text-ink-soft">Please ensure you are in a quiet environment. Take your time and try your best. You can pause between tasks if needed.</p>
        </div>
        <button className="btn-lav bg-white" onClick={() => setShowHelp(true)}><FileText size={15} /> View Instructions</button>
      </div>
      {showHelp && <InstructionsModal onClose={() => setShowHelp(false)} />}
    </div>
  );
}
