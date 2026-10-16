/**
 * ExerciseSession – runs one therapy exercise (Component 4) and saves the result.
 *
 *   reading / pacing / clear_speech / loudness   highlighted passage at the adaptive target speed
 *   picture                                     describe the picture, guiding questions
 *   sustained_vowel                             hold "ahh" – longest steady voicing
 *   sound_drill                                 target-sound words / phrases / sentences + self-check
 *   daf                                         delayed auditory feedback (Web Audio delay node)
 *
 * Only numbers leave the browser (voicing ratio, pauses, syllable count, rating) – never audio.
 * The backend scores the attempt, moves the level ladder and re-ranks the plan.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, CheckCircle2, Frown, Headphones, Loader2, Meh, Mic, PartyPopper, Smile, Square, Wind } from "lucide-react";
import { api } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { COLORS, ErrorBox, ScoreRing, Spinner } from "../../components/ui";
import type { AttemptPayload, AttemptResult, Exercise, TherapyPlan } from "../../types/integration";
import { TYPE_LABEL } from "./TherapyPlan";
import { useLiveCoach } from "./useLiveCoach";

type Phase = "ready" | "running" | "rate" | "saving" | "done";
const LIVE_TYPES = ["reading", "pacing", "clear_speech", "loudness", "picture", "sustained_vowel", "sound_drill"];
const FEEDBACK_STYLE: Record<string, string> = {
  success: "border-ok/30 bg-ok-soft", warning: "border-warn/40 bg-warn-soft", info: "border-lav-200 bg-lav-50",
};

function LoudnessMeter({ level, target = 0.06 }: { level: number; target?: number }) {
  const v = Math.min(1, level / (target * 2));
  const ok = level >= target;
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs font-semibold"><span className="text-ink-soft">Loudness</span><span style={{ color: ok ? COLORS.ok : COLORS.warn }}>{ok ? "Strong voice ✓" : "A bit louder"}</span></div>
      <div className="relative h-4 rounded-full bg-[#EEF0F7]">
        <div className="h-4 rounded-full transition-[width] duration-150" style={{ width: `${v * 100}%`, background: ok ? COLORS.ok : COLORS.warn }} />
        <div className="absolute top-[-4px] h-6 w-0.5 bg-ink" style={{ left: "50%" }} title="target" />
      </div>
    </div>
  );
}

function DafControls({ running, delay, setDelay }: { running: boolean; delay: number; setDelay: (v: number) => void }) {
  const ctxRef = useRef<{ ctx: AudioContext; node: DelayNode; stream: MediaStream } | null>(null);
  useEffect(() => {
    if (!running) return;
    let cancelled = false;
    navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
      if (cancelled) { stream.getTracks().forEach((t) => t.stop()); return; }
      const ctx = new AudioContext();
      const node = ctx.createDelay(2.0);
      node.delayTime.value = delay / 1000;
      ctx.createMediaStreamSource(stream).connect(node);
      node.connect(ctx.destination);
      ctxRef.current = { ctx, node, stream };
    }).catch(() => undefined);
    return () => {
      cancelled = true;
      ctxRef.current?.stream.getTracks().forEach((t) => t.stop());
      void ctxRef.current?.ctx.close();
      ctxRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running]);
  useEffect(() => { if (ctxRef.current) ctxRef.current.node.delayTime.value = delay / 1000; }, [delay]);
  return (
    <div className="rounded-xl border border-line bg-canvas p-4">
      <label className="text-sm font-semibold">Delay: {delay} ms</label>
      <input type="range" min={50} max={300} step={10} value={delay} onChange={(e) => setDelay(Number(e.target.value))} className="mt-2 w-full accent-[#1D4ED8]" />
      <p className="mt-2 flex items-center gap-1.5 text-xs muted"><Headphones size={14} /> Use headphones to avoid echo. Read any of the sentences below at a calm pace.</p>
    </div>
  );
}

export default function ExerciseSession() {
  const { exerciseId = "" } = useParams();
  const { activePatient } = useAuth();
  const navigate = useNavigate();
  const [plan, setPlan] = useState<TherapyPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("ready");
  const [startedAt, setStartedAt] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [wordIndex, setWordIndex] = useState(0);
  const [clear, setClear] = useState<Record<number, boolean>>({});
  const [delay, setDelay] = useState(150);
  const [result, setResult] = useState<AttemptResult | null>(null);

  useEffect(() => {
    if (!activePatient) return;
    api.therapy.plan(activePatient.id).then((p) => {
      if (!p.has_profile) navigate("/therapy-plan", { replace: true });
      else setPlan(p);
    }).catch((e: Error) => setError(e.message));
  }, [activePatient, navigate]);

  const ex: Exercise | undefined = useMemo(
    () => plan?.today.find((e) => e.id === exerciseId) ?? plan?.library.find((e) => e.id === exerciseId), [plan, exerciseId]);
  const coach = useLiveCoach(ex?.type ?? "pacing");
  const words = useMemo(() => (ex?.passage ?? "").split(/\s+/).filter(Boolean), [ex]);
  const live = !!ex && LIVE_TYPES.includes(ex.type);

  // timer + highlight
  useEffect(() => {
    if (phase !== "running") return;
    const t = window.setInterval(() => setElapsed((Date.now() - startedAt) / 1000), 200);
    return () => window.clearInterval(t);
  }, [phase, startedAt]);
  useEffect(() => {
    if (phase !== "running" || !ex?.target_wpm || !words.length) return;
    const t = window.setInterval(() => setWordIndex((i) => Math.min(words.length - 1, i + 1)), 60000 / ex.target_wpm);
    return () => window.clearInterval(t);
  }, [phase, ex, words.length]);

  const begin = useCallback(async () => {
    setElapsed(0); setWordIndex(0); setClear({});
    if (live) await coach.start();
    setStartedAt(Date.now());
    setPhase("running");
  }, [live, coach]);

  const finish = () => {
    coach.stop();
    setElapsed((Date.now() - startedAt) / 1000);
    setPhase("rate");
  };

  async function save(rating: "easy" | "ok" | "hard") {
    if (!activePatient || !ex) return;
    setPhase("saving");
    const s = coach.stats.current;
    const body: AttemptPayload = { exercise_id: ex.id, duration_seconds: Math.round(elapsed * 10) / 10, self_rating: rating };
    if (live && s.frames > 0) {
      body.live_session_id = coach.liveId.current;
      body.speaking_ratio = s.voicedFrames / s.frames;
      body.syllables = s.syllables;
    }
    if (ex.target_wpm) body.target_wpm = ex.target_wpm;
    if (ex.type === "sustained_vowel") body.max_phonation_sec = Math.round(s.longestRunSec * 10) / 10;
    if (ex.type === "sound_drill" && ex.items) {
      body.items_total = ex.items.length;
      body.items_clear = Object.values(clear).filter(Boolean).length;
    }
    try {
      setResult(await api.therapy.submit(activePatient.id, body));
      setPhase("done");
    } catch (e) {
      setError((e as Error).message);
      setPhase("rate");
    }
  }

  if (!activePatient) return <div className="card p-8 text-center muted">No patient selected.</div>;
  if (error && !plan) return <ErrorBox message={error} />;
  if (!plan) return <Spinner />;
  if (!ex) return <ErrorBox message="This exercise isn't part of your plan." />;
  if (ex.locked) return <ErrorBox message="Finish the previous level to unlock this exercise." />;

  const next = result?.plan.today.find((e) => e.id !== ex.id);
  const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <Link to="/therapy-plan" className="inline-flex items-center gap-1 text-xs font-medium text-ink-muted hover:text-ink"><ArrowLeft size={14} /> My therapy plan</Link>

      <section className="card p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <span className="chip bg-lav-100 text-lav-600">{TYPE_LABEL[ex.type]}{ex.level ? ` · ${ex.level}` : ""}</span>
            <h1 className="mt-2 text-2xl font-extrabold">{ex.title}</h1>
            <p className="mt-1 text-ink-soft">{ex.description}</p>
            {ex.target_wpm && (
              <p className="mt-1 text-xs muted">Highlight speed {ex.target_wpm} words/min{ex.base_wpm && ex.base_wpm !== ex.target_wpm ? ` (adapted from ${ex.base_wpm} for you)` : ""}</p>
            )}
          </div>
          <div className="rounded-2xl bg-canvas px-4 py-2 text-center"><div className="font-mono text-2xl font-bold">{fmt(elapsed)}</div><div className="text-[11px] muted">time</div></div>
        </div>

        <div className="mt-5 space-y-4">
          {/* content by type */}
          {words.length > 0 && (
            <div className="rounded-2xl border border-line bg-[#FBFBFE] p-5 text-xl leading-relaxed">
              {words.map((w, i) => (
                <span key={i} className={phase === "running" && i === wordIndex ? "rounded bg-sun-soft px-1 font-semibold text-ink" : phase === "running" && i < wordIndex ? "text-ink-muted" : "text-ink"}>{w} </span>
              ))}
            </div>
          )}
          {ex.type === "picture" && (
            <div className="grid gap-4 md:grid-cols-[1.3fr_1fr]">
              {ex.image_url && <img src={ex.image_url} alt={ex.title} className="w-full rounded-2xl border border-line object-cover" />}
              <ul className="space-y-2">{(ex.prompts ?? []).map((p) => <li key={p} className="rounded-xl bg-lav-50 p-3 text-sm">{p}</li>)}</ul>
            </div>
          )}
          {ex.type === "sustained_vowel" && (
            <div className="grid place-items-center rounded-2xl bg-lav-50 p-8 text-center">
              <Wind size={36} className="text-lav-500" />
              <div className="mt-2 text-5xl font-extrabold text-navy">{coach.stats.current.longestRunSec.toFixed(1)} s</div>
              <div className="text-sm muted">longest steady "ahh" · goal {ex.target_seconds} s</div>
            </div>
          )}
          {ex.type === "sound_drill" && ex.items && (
            <div>
              <p className="mb-2 text-sm text-ink-soft">Say each one slowly. Tap the ones that felt clear.</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {ex.items.map((item, i) => (
                  <button key={i} type="button" disabled={phase !== "running"} onClick={() => setClear((c) => ({ ...c, [i]: !c[i] }))}
                    className={`flex items-center justify-between rounded-xl border p-3 text-left text-lg font-semibold transition ${clear[i] ? "border-ok bg-ok-soft text-ink" : "border-line bg-white text-ink"} disabled:opacity-70`}>
                    {item}{clear[i] && <CheckCircle2 size={18} className="text-ok" />}
                  </button>
                ))}
              </div>
            </div>
          )}
          {ex.type === "daf" && (
            <>
              <DafControls running={phase === "running"} delay={delay} setDelay={setDelay} />
              <p className="rounded-xl bg-canvas p-4 text-lg">The quick brown fox jumps over the lazy dog. I like to walk to the market on Saturday mornings.</p>
            </>
          )}

          {phase === "running" && (ex.type === "loudness" || ex.type === "sustained_vowel") && <LoudnessMeter level={coach.level} />}
          {phase === "running" && coach.message && (
            <div className={`rounded-xl border px-4 py-2 text-sm text-ink ${FEEDBACK_STYLE[coach.message.severity] ?? FEEDBACK_STYLE.info}`}>{coach.message.message}</div>
          )}
          {coach.error && <ErrorBox message={coach.error} />}
          {error && <ErrorBox message={error} />}
        </div>

        {/* controls */}
        <div className="mt-6">
          {phase === "ready" && (
            <button className="btn-primary px-6 py-3 text-base" onClick={() => void begin()}><Mic size={18} /> Start</button>
          )}
          {phase === "running" && (
            <button className="inline-flex items-center gap-2 rounded-xl bg-bad px-6 py-3 font-semibold text-white hover:brightness-110" onClick={finish}><Square size={16} /> I'm done</button>
          )}
          {(phase === "rate" || phase === "saving") && (
            <div>
              <p className="mb-3 font-semibold">How did that feel?</p>
              <div className="flex flex-wrap gap-3">
                {([["easy", "Easy", <Smile key="e" />], ["ok", "Okay", <Meh key="o" />], ["hard", "Hard", <Frown key="h" />]] as const).map(([k, l, icon]) => (
                  <button key={k} className="btn-outline px-5 py-3" disabled={phase === "saving"} onClick={() => void save(k)}>{icon} {l}</button>
                ))}
                {phase === "saving" && <Loader2 className="animate-spin self-center text-brand" />}
              </div>
            </div>
          )}
        </div>
        <p className="mt-4 text-xs muted">Privacy: your voice stays on this device. Only practice numbers (time, pauses, speed) and your rating are saved.</p>
      </section>

      {phase === "done" && result && (
        <section className="card animate-step p-6">
          <div className="flex flex-col gap-6 md:flex-row md:items-center">
            <ScoreRing value={result.score} size={140} sub={result.verdict} />
            <div className="flex-1">
              {result.level_message && (
                <p className="mb-3 flex items-center gap-2 rounded-xl bg-ok-soft p-3 font-semibold text-ink"><PartyPopper size={18} className="text-ok" /> {result.level_message}</p>
              )}
              <ul className="space-y-1.5 text-sm text-ink-soft">{result.feedback.map((f) => <li key={f}>• {f}</li>)}</ul>
            </div>
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            {next && <Link to={`/therapy/exercise/${next.id}`} className="btn-primary" onClick={() => { setPhase("ready"); setResult(null); }}>Next: {next.title} <ArrowRight size={15} /></Link>}
            <button className="btn-ghost" onClick={() => { setResult(null); setPhase("ready"); setElapsed(0); }}>Try again</button>
            <Link to="/therapy-plan" className="btn-ghost">Back to my plan</Link>
          </div>
        </section>
      )}
    </div>
  );
}
