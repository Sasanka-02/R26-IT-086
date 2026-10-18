/**
 * ExerciseSession – runs one therapy exercise (Component 4) and saves the result.
 *
 *   reading / pacing / clear_speech / loudness   highlighted passage at the adaptive target speed
 *                                               (Level 7: tone hints – questioning / excited / quoting)
 *   picture                                     describe the picture, guiding questions
 *   conversation                                spontaneous answer to a situation + prompt questions
 *                                               (same recording flow as picture – no fixed text)
 *   sustained_vowel                             hold "ahh" – longest steady voicing
 *   sound_drill                                 target-sound words / phrases / sentences + self-check
 *   daf                                         delayed auditory feedback (Web Audio delay node), after a
 *                                               5-trial calibration that finds and saves the best delay
 *   words                                       picture-card word round (ages 6–11), grown-up marks each word
 *   roleplay                                    real-life situation: the other person's lines + example answers
 *
 * Live exercises offer a breathing warm-up first; the result shows why the score is what it is.
 * Every attempt is recorded and kept in this browser (Need help / My recordings tabs); only numbers leave the
 * browser (voicing ratio, pauses, syllable count, rating) – never audio.
 * The backend scores the attempt, moves the level ladder and re-ranks the plan.
 * Ages 6–11 (playful theme): big buttons, a "🔊 Listen" model (speechSynthesis), stars and confetti.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft, ArrowRight, CheckCircle2, Frown, Headphones, LifeBuoy, Lightbulb, Loader2, Meh, MessagesSquare, Mic, PartyPopper, RotateCcw, Smile,
  Square, Star, Wind,
} from "lucide-react";
import { api } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import ListenButton from "../../components/ListenButton";
import { COLORS, ErrorBox, ScoreRing, Spinner } from "../../components/ui";
import BreathingWarmup from "../../components/therapy/BreathingWarmup";
import DafCalibration, { DAF_PASSAGES } from "../../components/therapy/DafCalibration";
import { NewBadges } from "../../components/therapy/Badges";
import WordRound from "../../components/therapy/WordRound";
import HelpPanel from "../../components/therapy/HelpPanel";
import QuestionAnswers from "../../components/therapy/QuestionAnswers";
import RecordingList from "../../components/therapy/RecordingList";
import { practiceRecordings, type PracticeRecording } from "../../utils/practiceRecordings";
import { usePracticeRecorder } from "./usePracticeRecorder";
import type { AttemptPayload, AttemptResult, Exercise, TherapyPlan, ToneHint } from "../../types/integration";
import { themeFor } from "../../utils/age";
import { TYPE_EMOJI, TYPE_LABEL } from "./labels";
import { useLiveCoach } from "./useLiveCoach";

type Phase = "ready" | "running" | "rate" | "saving" | "done";
const LIVE_TYPES = ["reading", "pacing", "clear_speech", "loudness", "picture", "conversation", "roleplay", "sustained_vowel", "sound_drill"];
const QA_TYPES = ["picture", "conversation", "roleplay"]; // example answers sit next to each question
const WARMUP_TYPES =["reading", "pacing", "clear_speech", "loudness", "picture", "conversation", "roleplay", "daf"];

const TONE_STYLE: Record<ToneHint["tone"], { mark: string; chip: string; icon: string }> = {
  questioning: { mark: "decoration-brand", chip: "bg-brand-soft text-navy", icon: "❓" },
  excited: { mark: "decoration-sun", chip: "bg-sun-soft text-warn", icon: "❗" },
  quoting: { mark: "decoration-lav-500", chip: "bg-lav-100 text-lav-600", icon: "❝" },
};

/** Word index -> the tone hint it belongs to (phrases are matched in the passage text). */
function toneByWord(passage: string, hints: ToneHint[] | undefined): (ToneHint | null)[] {
  const words = passage.split(/\s+/).filter(Boolean);
  const out: (ToneHint | null)[] = words.map(() => null);
  if (!hints?.length) return out;
  const starts: number[] = [];
  let pos = 0;
  for (const w of words) {
    pos = passage.indexOf(w, pos);
    starts.push(pos);
    pos += w.length;
  }
  for (const h of hints) {
    const at = passage.indexOf(h.phrase);
    if (at < 0) continue;
    words.forEach((w, i) => { if (starts[i] + w.length > at && starts[i] < at + h.phrase.length) out[i] = h; });
  }
  return out;
}

function Celebration({ score }: { score: number }) {
  const stars = score >= 80 ? 3 : score >= 60 ? 2 : 1;
  const pieces = ["🎉", "⭐", "🎈", "✨", "🌟", "🎊"];
  return (
    <div className="relative">
      <div className="pointer-events-none absolute inset-x-0 -top-6 h-0" aria-hidden>
        {Array.from({ length: 18 }).map((_, i) => (
          <span key={i} className="confetti-piece absolute text-xl" style={{ left: `${(i * 37) % 100}%`, animationDelay: `${(i % 6) * 0.12}s` }}>{pieces[i % pieces.length]}</span>
        ))}
      </div>
      <div className="flex justify-center gap-2" aria-label={`${stars} of 3 stars`}>
        {[1, 2, 3].map((n) => <Star key={n} size={44} className={n <= stars ? "fill-sun text-sun" : "text-line"} />)}
      </div>
    </div>
  );
}
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
  const [warmup, setWarmup] = useState(false);
  const [calibrating, setCalibrating] = useState(false);
  const [wordResult, setWordResult] = useState<{ got: number; total: number } | null>(null);
  const [tab, setTab] = useState<"exercise" | "recordings">("exercise");
  const [take, setTake] = useState<{ blob: Blob; url: string } | null>(null); // this attempt's recording
  const [recError, setRecError] = useState(false);
  const [recordings, setRecordings] = useState<PracticeRecording[]>([]);
  const recorder = usePracticeRecorder();

  const loadRecordings = useCallback(() => {
    if (activePatient) void practiceRecordings.list(activePatient.id, exerciseId).then(setRecordings);
  }, [activePatient, exerciseId]);
  useEffect(() => { loadRecordings(); }, [loadRecordings]);
  useEffect(() => () => { if (take) URL.revokeObjectURL(take.url); }, [take]);

  async function keepTake() {
    const blob = await recorder.stop();
    if (blob) setTake({ blob, url: URL.createObjectURL(blob) });
  }

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
  const tones = useMemo(() => toneByWord(ex?.passage ?? "", ex?.tone_hints), [ex]);
  const live = !!ex && LIVE_TYPES.includes(ex.type);
  const theme = themeFor(plan?.learner.theme);
  const playful = plan?.learner.theme === "playful";
  const dafPassage = useMemo(() => DAF_PASSAGES[Math.floor(Math.random() * DAF_PASSAGES.length)], []);

  // DAF: use the saved calibration, or calibrate first
  useEffect(() => {
    if (ex?.type !== "daf") return;
    if (ex.recommended_delay_ms) setDelay(ex.recommended_delay_ms);
    setCalibrating(!ex.recommended_delay_ms);
  }, [ex]);

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

  const finishWords = (got: number, total: number) => {
    setWordResult({ got, total });
    setElapsed((Date.now() - startedAt) / 1000);
    setPhase("rate");
    void keepTake();
  };

  const begin = useCallback(async () => {
    setElapsed(0); setWordIndex(0); setClear({}); setWordResult(null); setWarmup(false); setTab("exercise");
    setTake((t) => { if (t) URL.revokeObjectURL(t.url); return null; });
    setRecError(!(await recorder.start()));
    if (live) await coach.start();
    setStartedAt(Date.now());
    setPhase("running");
  }, [live, coach, recorder]);

  const finish = () => {
    coach.stop();
    setElapsed((Date.now() - startedAt) / 1000);
    setPhase("rate");
    void keepTake();
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
    if (ex.type === "words" && wordResult) {
      body.items_total = wordResult.total;
      body.items_clear = wordResult.got;
    }
    try {
      const res = await api.therapy.submit(activePatient.id, body);
      if (take) {
        await practiceRecordings.save({
          id: crypto.randomUUID(), patientId: activePatient.id, exerciseId: ex.id, exerciseTitle: ex.title, exerciseType: ex.type,
          createdAt: new Date().toISOString(), durationSec: body.duration_seconds, score: res.score, blob: take.blob,
        });
        loadRecordings();
      }
      setResult(res);
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
  if (ex.locked) return <ErrorBox message={ex.unlock_after ? "Do this level's picture description first to unlock this harder scene." : "Finish the previous level to unlock this exercise."} />;

  const next = result?.plan.today.find((e) => e.id !== ex.id);
  const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <Link to="/therapy-plan" className="inline-flex items-center gap-1 text-xs font-medium text-ink-muted hover:text-ink"><ArrowLeft size={14} /> My therapy plan</Link>

      <section className="card p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <span className="chip bg-lav-100 text-lav-600">
              {playful && ex.task_type ? `${TYPE_EMOJI[ex.task_type]} ` : ""}{TYPE_LABEL[ex.type]}{ex.level ? ` · ${ex.level}` : ""}{ex.bracket ? ` · Level ${ex.bracket} (${ex.bracket_label})` : ""}
            </span>
            <h1 className={`mt-2 font-extrabold ${playful ? "text-3xl" : "text-2xl"}`}>{ex.title}</h1>
            <p className="mt-1 text-ink-soft">{ex.description}</p>
            {ex.target_wpm && (
              <p className="mt-1 text-xs muted">Highlight speed {ex.target_wpm} words/min{ex.base_wpm && ex.base_wpm !== ex.target_wpm ? ` (adapted from ${ex.base_wpm} for you)` : ""}</p>
            )}
          </div>
          <div className="rounded-2xl bg-canvas px-4 py-2 text-center"><div className="font-mono text-2xl font-bold">{fmt(elapsed)}</div><div className="text-[11px] muted">time</div></div>
        </div>

        <div className="mt-5 flex flex-wrap gap-1 rounded-xl bg-canvas p-1" role="tablist" aria-label="Exercise sections">
          {([["exercise", "Exercise & help", <Mic key="m" size={15} />],
            ["recordings", `My recordings (${recordings.length})`, <Headphones key="r" size={15} />]] as const).map(([k, label, icon]) => (
            <button key={k} role="tab" aria-selected={tab === k} disabled={phase === "running" && k !== "exercise"} onClick={() => setTab(k)}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold transition disabled:opacity-40 ${tab === k ? "bg-white text-navy shadow-sm" : "text-ink-soft hover:text-ink"}`}>
              {icon}{label}
            </button>
          ))}
        </div>

        {tab === "recordings" && (
          <div className="mt-5">
            <p className="mb-3 text-sm text-ink-soft">Every attempt is recorded so you can hear your progress. Recordings stay on this device only. <Link to="/therapy/recordings" className="font-semibold text-brand hover:underline">All my recordings →</Link></p>
            <RecordingList items={recordings} showTitle={false} onDelete={(id) => void practiceRecordings.remove(id).then(loadRecordings)}
              empty="No recordings of this exercise yet – press Start and your voice is saved here." />
          </div>
        )}

        <div hidden={tab !== "exercise"}>
        <div className="mt-5 space-y-4">
          {/* content by type */}
          {words.length > 0 && (
            <>
              {theme.listen && <ListenButton text={ex.passage ?? ""} wpm={ex.target_wpm} big={playful} />}
              <div className={`rounded-2xl border border-line bg-[#FBFBFE] p-5 leading-relaxed ${playful ? "text-2xl tracking-wide" : "text-xl"}`}>
                {words.map((w, i) => {
                  const tone = tones[i];
                  const startsHint = tone && (i === 0 || tones[i - 1] !== tone);
                  const base = phase === "running" && i === wordIndex ? "rounded bg-sun-soft px-1 font-semibold text-ink" : phase === "running" && i < wordIndex ? "text-ink-muted" : "text-ink";
                  return (
                    <span key={i} className={`${base} ${tone ? `underline decoration-2 underline-offset-4 ${TONE_STYLE[tone.tone].mark}` : ""}`}>
                      {startsHint && <sup className={`chip mr-1 px-1.5 py-0 align-super text-[10px] no-underline ${TONE_STYLE[tone.tone].chip}`}>{TONE_STYLE[tone.tone].icon} {tone.tone}</sup>}
                      {w}{" "}
                    </span>
                  );
                })}
              </div>
              {!!ex.tone_hints?.length && (
                <ul className="grid gap-2 sm:grid-cols-2">
                  {ex.tone_hints.map((h) => (
                    <li key={h.phrase} className={`rounded-xl p-3 text-sm ${TONE_STYLE[h.tone].chip}`}>
                      <b>{TONE_STYLE[h.tone].icon} “{h.phrase}”</b><span className="block text-xs opacity-90">{h.hint}</span>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
          {ex.type === "picture" && (
            <div className="grid items-start gap-4 lg:grid-cols-[1.2fr_1fr]">
              {ex.image_url && <img src={ex.image_url} alt={ex.title} className="w-full rounded-2xl border border-line bg-white object-cover lg:sticky lg:top-24" />}
              <div className="space-y-3">
                {theme.listen && <ListenButton text={(ex.prompts ?? []).join(" ")} big={playful} />}
                <QuestionAnswers questions={ex.prompts ?? []} answers={ex.help?.examples ?? []} playful={playful} wpm={ex.target_wpm ?? 100} />
              </div>
            </div>
          )}
          {ex.type === "roleplay" && (
            <div className="space-y-3">
              <p className="rounded-2xl border border-lav-200 bg-lav-50 p-4 text-base text-ink"><b>Situation:</b> {ex.situation}</p>
              <QuestionAnswers speaker questions={ex.prompts ?? []} answers={ex.help?.examples ?? []} playful={playful} wpm={ex.target_wpm ?? 100} />
              <p className="text-xs muted">Take a calm breath before each answer, start softly and pause between ideas – just like a real conversation.</p>
            </div>
          )}
          {ex.type === "words" && ex.words && (
            phase === "running" ? <WordRound cards={ex.words} onDone={finishWords} /> : (
              <div className="flex flex-wrap justify-center gap-3 rounded-2xl bg-sun-soft p-5 text-4xl" aria-hidden>
                {ex.words.map((w) => <span key={w.text} title={w.text}>{w.emoji}</span>)}
              </div>
            )
          )}
          {wordResult && phase !== "running" && (
            <p className="rounded-xl bg-ok-soft p-3 text-center text-lg font-bold text-ink">{"⭐".repeat(wordResult.got)} {wordResult.got} of {wordResult.total} words said well!</p>
          )}
          {ex.type === "conversation" && (
            <div className="space-y-3">
              <div className={`flex gap-3 rounded-2xl border border-lav-200 bg-lav-50 p-5 ${playful ? "text-xl" : "text-lg"}`}>
                <MessagesSquare className="mt-1 shrink-0 text-lav-500" size={22} />
                <p className="text-ink">{ex.situation}</p>
              </div>
              {theme.listen && <ListenButton text={[ex.situation, ...(ex.prompts ?? [])].join(" ")} big={playful} />}
              <QuestionAnswers questions={ex.prompts ?? []} answers={ex.help?.examples ?? []} playful={playful} wpm={ex.target_wpm ?? 100} />
              <p className="text-xs muted">Press Start, then answer the questions out loud in your own words. There are no wrong answers – take your time.</p>
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
          {ex.type === "daf" && calibrating && phase === "ready" && (
            <DafCalibration patientId={activePatient.id}
              onCalibrated={(ms) => { setDelay(ms); window.setTimeout(() => setCalibrating(false), 1800); }}
              onSkip={() => { setDelay(150); setCalibrating(false); }} />
          )}
          {ex.type === "daf" && !calibrating && (
            <>
              <DafControls running={phase === "running"} delay={delay} setDelay={setDelay} />
              {phase === "ready" && (
                <button type="button" className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand hover:underline" onClick={() => setCalibrating(true)}>
                  <RotateCcw size={13} /> {ex.recommended_delay_ms ? `Recalibrate (saved: ${ex.recommended_delay_ms} ms)` : "Calibrate my delay"}
                </button>
              )}
              <div className="rounded-xl bg-canvas p-4"><p className="text-xs font-bold uppercase tracking-wide text-lav-600">{dafPassage.title}</p><p className="mt-1 text-lg">{dafPassage.text}</p></div>
            </>
          )}
          {warmup && phase === "ready" && <BreathingWarmup playful={playful} onDone={() => setWarmup(false)} />}

          {phase === "running" && (ex.type === "loudness" || ex.type === "sustained_vowel") && <LoudnessMeter level={coach.level} />}
          {phase === "running" && coach.message && (
            <div className={`rounded-xl border px-4 py-2 text-sm text-ink ${FEEDBACK_STYLE[coach.message.severity] ?? FEEDBACK_STYLE.info}`}>{coach.message.message}</div>
          )}
          {coach.error && <ErrorBox message={coach.error} />}
          {error && <ErrorBox message={error} />}
        </div>

        {/* controls */}
        <div className="mt-6">
          {phase === "ready" && !(ex.type === "daf" && calibrating) && !warmup && (
            <div className="flex flex-wrap items-center gap-3">
              <button className={`btn-primary ${theme.button}`} onClick={() => void begin()}><Mic size={playful ? 22 : 18} /> {ex.type === "words" ? (playful ? "Start the cards! 🃏" : "Start the round") : playful ? "Start! 🎤" : "Start"}</button>
              {WARMUP_TYPES.includes(ex.type) && (
                <button className="btn-lav" onClick={() => setWarmup(true)}><Wind size={15} /> {playful ? "Balloon breathing first 🎈" : "Breathing warm-up first (36 s)"}</button>
              )}
            </div>
          )}
          {phase === "running" && ex.type !== "words" && (
            <button className={`inline-flex items-center gap-2 rounded-xl bg-bad font-semibold text-white hover:brightness-110 ${theme.button}`} onClick={finish}><Square size={16} /> I'm done</button>
          )}
          {(phase === "rate" || phase === "saving") && (
            <div>
              {take && (
                <div className="mb-4 rounded-xl border border-lav-200 bg-lav-50 p-3">
                  <p className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-ink"><Headphones size={15} className="text-lav-600" /> Listen to yourself</p>
                  <audio controls src={take.url} className="h-9 w-full" />
                </div>
              )}
              {recError && <p className="mb-3 text-xs muted">Your voice couldn't be recorded on this browser, but your result still counts.</p>}
              <p className="mb-3 font-semibold">How did that feel?</p>
              <div className="flex flex-wrap gap-3">
                {([["easy", "Easy", <Smile key="e" />], ["ok", "Okay", <Meh key="o" />], ["hard", "Hard", <Frown key="h" />]] as const).map(([k, l, icon]) => (
                  <button key={k} className={`btn-outline ${playful ? "rounded-2xl px-7 py-4 text-lg" : "px-5 py-3"}`} disabled={phase === "saving"} onClick={() => void save(k)}>{icon} {l}</button>
                ))}
                {phase === "saving" && <Loader2 className="animate-spin self-center text-brand" />}
              </div>
            </div>
          )}
        </div>
        <section className="mt-6 border-t border-line pt-5" aria-label="Need help">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-bold text-ink"><LifeBuoy size={19} className="text-navy" /> Need help?</h2>
          <HelpPanel ex={ex} techniques={plan.focus.techniques} playful={playful} hideExamples={QA_TYPES.includes(ex.type)} />
        </section>
        </div>
        <p className="mt-4 text-xs muted">Privacy: your recordings are saved on this device only, so you can listen back. Only practice numbers (time, pauses, speed) and your rating are sent to SpeakFree.</p>
      </section>

      {phase === "done" && result && (
        <section className="card animate-step p-6">
          {theme.celebrate && <div className="mb-5"><Celebration score={result.score} /></div>}
          <div className="flex flex-col gap-6 md:flex-row md:items-center">
            <ScoreRing value={result.score} size={140} sub={result.verdict} />
            <div className="flex-1">
              {result.level_message && (
                <p className="mb-3 flex items-center gap-2 rounded-xl bg-ok-soft p-3 font-semibold text-ink"><PartyPopper size={18} className="text-ok" /> {result.level_message}</p>
              )}
              <ul className="space-y-1.5 text-sm text-ink-soft">{result.feedback.map((f) => <li key={f}>• {f}</li>)}</ul>
            </div>
          </div>
          {result.new_badges?.length > 0 && <div className="mt-4"><NewBadges badges={result.new_badges} /></div>}
          {result.breakdown.length > 0 && (
            <details className="mt-4 rounded-xl bg-canvas p-4 text-sm">
              <summary className="cursor-pointer font-bold text-ink">Why this score?</summary>
              <ul className="mt-2 space-y-1">
                {result.breakdown.map((b) => (
                  <li key={b.feature} className="flex justify-between gap-3">
                    <span className="text-ink-soft">{b.label}</span>
                    <span className={`font-mono font-semibold ${b.points >= 0 ? "text-ok" : "text-bad"}`}>{b.points >= 0 ? "+" : ""}{b.points}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs muted">The points add up to your score (0–100). They come from the numbers measured during the exercise and your rating.</p>
            </details>
          )}
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
