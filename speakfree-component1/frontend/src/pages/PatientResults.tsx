/**
 * PatientResults – the simple, encouraging results view for patients, guardians and clinicians.
 * No equations and no raw acoustic data: a friendly status gauge, a plain-language summary of
 * strengths and areas to practise, clear next steps, a clinical report for a therapist, and support.
 * (The technical dashboard is admin-only: SessionDashboard.)
 */
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowRight,
  CalendarCheck,
  CheckCircle2,
  Download,
  Dumbbell,
  HeartHandshake,
  Image as ImageIcon,
  LifeBuoy,
  Mail,
  MessageSquareText,
  MessagesSquare,
  Mic,
  PartyPopper,
  RotateCcw,
  Stethoscope,
} from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { COLORS, ErrorBox, Spinner } from "../components/ui";
import { TASK_LABEL, type SessionSummary, type TaskType } from "../types";
import { friendlyStatus } from "../utils/friendlyStatus";

const SUPPORT_EMAIL = "support@speakfree.lk";

// --------------------------------------------------------------------------- plain-language mapping


type AreaKey = "pronunciation" | "fluency" | "clarity" | "sounds";
const AREAS: { key: AreaKey; name: string; noun: string; hint: string; score: (d: SessionSummary) => number }[] = [
  { key: "pronunciation", name: "Pronunciation", noun: "pronunciation", hint: "some words were hard to make out", score: (d) => d.pronunciation_score },
  { key: "fluency", name: "Fluency", noun: "fluency", hint: "some hesitations and pauses", score: (d) => d.fluency_score },
  { key: "clarity", name: "Clarity", noun: "clarity", hint: "parts of your speech were hard for us to follow", score: (d) => d.asr_accuracy_percent },
  { key: "sounds", name: "Speech sounds", noun: "speech sounds", hint: "a few speech sounds were tricky", score: (d) => d.articulation_score },
];

function rating(v: number): { word: string; color: string } {
  if (v >= 85) return { word: "Strong", color: COLORS.ok };
  if (v >= 70) return { word: "Good", color: COLORS.brand };
  if (v >= 55) return { word: "Keep practising", color: COLORS.warn };
  return { word: "Needs practice", color: COLORS.bad };
}

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const joinNames = (names: string[]) => (names.length <= 1 ? names.join("") : `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`);

function plainSummary(d: SessionSummary): string {
  const scored = AREAS.map((a) => ({ ...a, v: a.score(d) }));
  const strengths = scored.filter((a) => a.v >= 75).sort((x, y) => y.v - x.v).slice(0, 2);
  const weakest = scored.filter((a) => a.v < 70).sort((x, y) => x.v - y.v)[0];
  if (!weakest && strengths.length) return `Your ${joinNames(strengths.map((a) => a.noun))} ${strengths.length > 1 ? "are" : "is"} strong. Keep practising to stay confident!`;
  if (!weakest) return "You're doing well across the board. Keep practising to build confidence.";
  const strong = strengths.length ? `Your ${joinNames(strengths.map((a) => a.noun))} ${strengths.length > 1 ? "are" : "is"} strong, but we noticed ` : "We noticed ";
  return `${strong}${weakest.hint}. Let's work on ${weakest.noun}.`;
}

/** "/θ/ (th)" → "th", "/s/" → "s" */
function friendlySound(label: string): string {
  const paren = label.match(/\(([^)]+)\)/);
  return paren ? paren[1] : label.replace(/\//g, "").trim();
}

// --------------------------------------------------------------------------- widgets
function FriendlyGauge({ level }: { level: number }) {
  const angle = -90 + ((level - 0.5) / 4) * 180;
  const colors = [COLORS.ok, COLORS.brand, COLORS.warn, COLORS.bad];
  return (
    <svg viewBox="0 0 200 112" className="w-56" role="img" aria-label={friendlyStatus(level).title}>
      {colors.map((c, i) => {
        const a0 = Math.PI + (i / 4) * Math.PI + 0.03;
        const a1 = Math.PI + ((i + 1) / 4) * Math.PI - 0.03;
        const p = (a: number) => `${100 + 80 * Math.cos(a)},${100 + 80 * Math.sin(a)}`;
        return <path key={i} d={`M${p(a0)} A80,80 0 0 1 ${p(a1)}`} stroke={c} strokeWidth={18} strokeLinecap="round" fill="none" opacity={i + 1 === level ? 1 : 0.2} />;
      })}
      <g transform={`rotate(${angle} 100 100)`}><line x1={100} y1={100} x2={100} y2={38} stroke={COLORS.ink} strokeWidth={4} strokeLinecap="round" /></g>
      <circle cx={100} cy={100} r={7} fill={COLORS.ink} />
    </svg>
  );
}

const TASK_ICON: Record<TaskType, JSX.Element> = {
  reading: <Mic size={16} />,
  picture: <ImageIcon size={16} />,
  scenario: <MessageSquareText size={16} />,
  questions: <MessagesSquare size={16} />,
};

// --------------------------------------------------------------------------- page
export default function PatientResults() {
  const { sessionId = "" } = useParams();
  const { user } = useAuth();
  const [data, setData] = useState<SessionSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    setError(null);
    api.sessionSummary(sessionId).then(setData).catch((e: Error) => setError(e.message));
  }, [sessionId]);

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Spinner />;

  const patient = user?.patients.find((p) => p.id === data.patient_id);
  const firstName = (patient?.full_name ?? user?.full_name ?? "").split(" ")[0];
  const isSelf = patient?.is_self ?? true;
  const level = data.screening_indicator.severity_hint;
  const status = friendlyStatus(level);
  const summary = plainSummary(data);
  const sounds = data.phoneme_findings.filter((f) => f.status !== "ok").slice(0, 4).map((f) => friendlySound(f.sound));
  const date = new Date(data.created_at).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
  const reportUrl = `/sessions/${data.session_id}/report?print=1`;

  const mailBody = [
    "Hello,",
    "",
    `I completed a SpeakFree speech screening on ${date}${patient && !patient.is_self ? ` for ${patient.full_name}` : ""}.`,
    `Result: ${status.title} (screening level ${level} of 4, overall speech score ${data.overall_speech_score.toFixed(0)}/100).`,
    `Summary: ${summary}`,
    "",
    "I have attached the full SpeakFree clinical report (PDF) with the detailed measurements.",
    "",
    "Thank you.",
  ].join("\n");
  const mailto = `mailto:?subject=${encodeURIComponent(`SpeakFree screening results – ${patient?.full_name ?? user?.full_name ?? ""}`)}&body=${encodeURIComponent(mailBody)}`;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* reassurance */}
      <section className="flex items-start gap-4 rounded-2xl border border-ok/30 bg-ok-soft p-5">
        <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-ok text-white"><PartyPopper size={22} /></span>
        <div>
          <h1 className="text-xl font-extrabold text-ink">Well done{firstName ? `, ${firstName}` : ""}! Your screening is complete.</h1>
          <p className="mt-1 text-sm text-ink-soft">
            All {data.recording_count} recordings from {date} were received and analysed successfully. Here's what we found{isSelf ? "" : ` for ${patient?.full_name}`}.
          </p>
          <ul className="mt-3 flex flex-wrap gap-2">
            {data.tasks.map((t, i) => (
              <li key={t.analysis_id} className="chip bg-white text-ink-soft">
                <CheckCircle2 size={13} className="text-ok" /> {TASK_ICON[t.task_type]}
                {t.task_type === "questions" ? `Question ${data.tasks.slice(0, i + 1).filter((x) => x.task_type === "questions").length}` : TASK_LABEL[t.task_type]}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* status + plain summary */}
      <section className="card grid gap-6 p-6 md:grid-cols-[auto_1fr] md:items-center">
        <div className="flex flex-col items-center text-center">
          <FriendlyGauge level={level} />
          <div className="mt-1 text-xl font-extrabold" style={{ color: status.color }}>{status.title}</div>
        </div>
        <div>
          <h2 className="text-lg font-bold text-ink">Your results in plain words</h2>
          <p className="mt-2 text-[17px] leading-relaxed text-ink">{summary}</p>
          <p className="mt-2 text-sm text-ink-soft">{status.text}</p>
          {sounds.length > 0 && (
            <div className="mt-4">
              <div className="text-xs font-bold uppercase tracking-wide text-ink-muted">Sounds to practise</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {sounds.map((s) => <span key={s} className="chip bg-lav-100 font-mono text-sm text-lav-600">"{s}"</span>)}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* areas, no numbers */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {AREAS.map((a) => {
          const v = a.score(data);
          const r = rating(v);
          return (
            <div key={a.key} className="card p-4">
              <div className="text-sm font-semibold text-ink-soft">{a.name}</div>
              <div className="mt-1 text-lg font-extrabold" style={{ color: r.color }}>{r.word}</div>
              <div className="mt-2 h-2 rounded-full bg-[#EEF0F7]" aria-hidden>
                <div className="h-2 rounded-full" style={{ width: `${Math.max(8, Math.min(100, v))}%`, background: r.color }} />
              </div>
            </div>
          );
        })}
      </section>

      {/* next steps */}
      <section className="card p-6">
        <h2 className="text-lg font-bold text-ink">What to do next</h2>
        <p className="mt-1 text-sm text-ink-soft">Regular, short practice makes the biggest difference. Start right away:</p>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <Link to="/therapy-plan" className="group flex items-center gap-4 rounded-2xl bg-gradient-to-br from-navy to-[#3B3FB6] p-5 text-white shadow-nav transition hover:brightness-110">
            <span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-white/15"><HeartHandshake size={24} /></span>
            <span className="flex-1"><span className="block text-lg font-bold">Start My Therapy Plan</span><span className="text-sm text-white/75">A plan built around these results</span></span>
            <ArrowRight className="transition group-hover:translate-x-1" />
          </Link>
          <Link to="/therapy-plan" className="group flex items-center gap-4 rounded-2xl border-2 border-brand/30 bg-brand-soft p-5 text-navy transition hover:border-brand">
            <span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-white text-brand"><Dumbbell size={24} /></span>
            <span className="flex-1"><span className="block text-lg font-bold">Begin Today's Exercises</span><span className="text-sm text-ink-soft">Short, fun practice for today</span></span>
            <ArrowRight className="transition group-hover:translate-x-1" />
          </Link>
        </div>
        <Link to="/assessment" className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-brand hover:underline"><RotateCcw size={15} /> Take another screening later to track progress</Link>
      </section>

      {/* therapist export + support */}
      <div className="grid gap-5 md:grid-cols-2">
        <section className="card p-6">
          <h2 className="flex items-center gap-2 text-lg font-bold text-ink"><Stethoscope size={19} className="text-navy" /> For your therapist</h2>
          <p className="mt-1 text-sm text-ink-soft">The clinical report has all the detailed measurements, so you don't have to interpret them yourself.</p>
          <div className="mt-4 flex flex-col gap-2">
            <Link to={reportUrl} target="_blank" className="btn-primary py-3"><Download size={17} /> Download Clinical Report</Link>
            <a href={mailto} className="btn-outline py-3"><Mail size={17} /> Share Results with My Therapist</a>
          </div>
          <p className="mt-3 text-xs muted">Save the report as a PDF, then attach it to the e-mail.</p>
        </section>
        <section className="card p-6">
          <h2 className="flex items-center gap-2 text-lg font-bold text-ink"><LifeBuoy size={19} className="text-navy" /> We're here for you</h2>
          <p className="mt-1 text-sm text-ink-soft">
            Feeling unsure about your results? That's completely normal. This is a screening, not a diagnosis – a speech therapist can explain what it means for you.
          </p>
          <div className="mt-4 flex flex-col gap-2">
            <Link to="/appointments" className="btn-outline py-3"><CalendarCheck size={17} /> Speak to a Clinician</Link>
            <a href={`mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent("Question about my SpeakFree results")}`} className="btn-ghost py-3"><Mail size={17} /> Contact Support</a>
          </div>
        </section>
      </div>
    </div>
  );
}
