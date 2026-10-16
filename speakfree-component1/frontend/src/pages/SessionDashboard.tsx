/**
 * SessionDashboard – "Screening Results": the session-level Component 1 output shown after "Analyse Now".
 *
 *  • Pooled ASR confidence (Eq. 3 over every token of every recording) + overall speech score + screening level
 *  • Score breakdown (ASR accuracy, fluency, pronunciation, articulation)
 *  • Per-task results with heat-coloured transcripts, linking to the per-recording explainable dashboard
 *  • Word-confidence distribution, lowest-confidence words, sound-level findings, acoustic summary
 *  • The JSON hand-off for Components 2 & 3
 */
import { useEffect, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import MethodEquations from "../components/MethodEquations";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Braces,
  Download,
  FileText,
  Gauge,
  Image as ImageIcon,
  ListChecks,
  MessageSquareText,
  MessagesSquare,
  Mic,
  ShieldCheck,
  Sigma,
  Sparkles,
  Volume2,
} from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { Bar, Card, COLORS, ErrorBox, ScoreRing, scoreColor, scoreWord, SeverityGauge, Spinner, pct } from "../components/ui";
import { TASK_LABEL, type PhonemeFinding, type SessionSummary, type SessionTaskEntry, type TaskType } from "../types";

const TASK_ICON: Record<TaskType, ReactNode> = {
  reading: <Mic size={16} />,
  picture: <ImageIcon size={16} />,
  scenario: <MessageSquareText size={16} />,
  questions: <MessagesSquare size={16} />,
};

function downloadJson(name: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

function MetricCard({ label, value, caption, suffix = "" }: { label: string; value: number; caption: string; suffix?: string }) {
  const c = scoreColor(value);
  return (
    <div className="card p-4">
      <div className="flex items-baseline justify-between">
        <div className="text-sm font-semibold text-ink-soft">{label}</div>
        <div className="text-xs font-semibold" style={{ color: c }}>{scoreWord(value)}</div>
      </div>
      <div className="mt-1 text-[28px] font-extrabold" style={{ color: COLORS.ink }}>{value.toFixed(1)}{suffix}</div>
      <Bar value={value} className="h-2" />
      <div className="mt-2 text-[11px] leading-snug muted">{caption}</div>
    </div>
  );
}

function FindingRow({ f }: { f: PhonemeFinding }) {
  const color = f.status === "ok" ? COLORS.ok : f.status === "warning" ? COLORS.warn : COLORS.bad;
  return (
    <div className="grid grid-cols-[88px_1fr_44px_18px] items-center gap-3 py-1.5"
      title={f.flagged_words.length ? `Low-confidence words: ${f.flagged_words.join(", ")}` : `${f.word_count} words`}>
      <span className="font-mono text-sm text-ink">{f.sound}</span>
      <Bar value={f.accuracy_percent} color={color} />
      <span className="text-right font-mono text-xs">{f.accuracy_percent.toFixed(0)}%</span>
      {f.status === "ok" ? <ShieldCheck size={16} color={color} /> : <AlertTriangle size={16} color={color} />}
    </div>
  );
}

function ConfidenceDistribution({ d, threshold }: { d: SessionSummary["confidence_distribution"]; threshold: number }) {
  const total = Math.max(1, d.high + d.medium + d.low);
  const parts = [
    { key: "high", label: "High (≥ 90 %)", n: d.high, color: COLORS.ok },
    { key: "medium", label: `Medium (${(threshold * 100).toFixed(0)}–90 %)`, n: d.medium, color: COLORS.warn },
    { key: "low", label: `Low (< ${(threshold * 100).toFixed(0)} %) – dysfluency candidates`, n: d.low, color: COLORS.bad },
  ];
  return (
    <div>
      <div className="flex h-5 w-full overflow-hidden rounded-full bg-[#EEF0F7]">
        {parts.map((p) => p.n > 0 && (
          <div key={p.key} style={{ width: `${(p.n / total) * 100}%`, background: p.color }} title={`${p.label}: ${p.n}`} />
        ))}
      </div>
      <ul className="mt-3 space-y-1.5 text-sm">
        {parts.map((p) => (
          <li key={p.key} className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-sm" style={{ background: p.color }} />
            <span className="flex-1 text-ink-soft">{p.label}</span>
            <span className="font-mono font-semibold">{p.n}</span>
            <span className="w-12 text-right font-mono text-xs muted">{((p.n / total) * 100).toFixed(0)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function TaskConfidenceChart({ tasks }: { tasks: SessionTaskEntry[] }) {
  return (
    <div className="space-y-3">
      {tasks.map((t, i) => (
        <div key={t.analysis_id}>
          <div className="mb-1 flex items-center justify-between gap-2 text-xs">
            <span className="truncate font-semibold text-ink-soft">{taskShortName(t, tasks, i)}</span>
            <span className="font-mono font-semibold">{pct(t.overall_confidence_percent)}</span>
          </div>
          <Bar value={t.overall_confidence_percent} className="h-3" />
        </div>
      ))}
    </div>
  );
}

function taskShortName(t: SessionTaskEntry, all: SessionTaskEntry[], idx: number) {
  if (t.task_type !== "questions") return TASK_LABEL[t.task_type];
  const qIndex = all.slice(0, idx + 1).filter((x) => x.task_type === "questions").length;
  return `Question ${qIndex}`;
}

function TaskResultCard({ t, name }: { t: SessionTaskEntry; name: string }) {
  const c = scoreColor(t.overall_confidence_percent);
  return (
    <div className="card flex flex-col p-5">
      <div className="mb-2 flex items-center gap-2">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-lav-100 text-lav-600">{TASK_ICON[t.task_type]}</span>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-bold">{name}</div>
          <div className="truncate text-xs muted" title={t.title}>{t.title}</div>
        </div>
      </div>
      <div className="my-2 grid grid-cols-3 gap-2 text-center">
        <div className="rounded-xl bg-canvas p-2">
          <div className="text-[10px] font-semibold uppercase tracking-wide muted">ASR conf.</div>
          <div className="font-mono text-lg font-bold" style={{ color: c }}>{t.overall_confidence_percent.toFixed(0)}%</div>
        </div>
        <div className="rounded-xl bg-canvas p-2">
          <div className="text-[10px] font-semibold uppercase tracking-wide muted">Score</div>
          <div className="font-mono text-lg font-bold">{t.overall_speech_score.toFixed(0)}</div>
        </div>
        <div className={`rounded-xl p-2 ${t.dysfluency_candidate_count ? "bg-bad-soft" : "bg-canvas"}`}>
          <div className="text-[10px] font-semibold uppercase tracking-wide muted">Flags</div>
          <div className={`font-mono text-lg font-bold ${t.dysfluency_candidate_count ? "text-bad" : ""}`}>{t.dysfluency_candidate_count}</div>
        </div>
      </div>
      <p className="line-clamp-3 flex-1 text-sm italic leading-relaxed text-ink-soft">“{t.transcript || "…"}”</p>
      <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-[11px] muted">
        <span>{t.word_count} words</span>
        <span>{t.words_per_minute.toFixed(0)} wpm</span>
        <span>{t.pause_count} pauses</span>
        <span>SNR {t.snr_db.toFixed(0)} dB</span>
        {t.content_coverage_percent !== null && <span>coverage {t.content_coverage_percent.toFixed(0)}%</span>}
      </div>
      <Link to={`/results/${t.analysis_id}`} className="btn-outline mt-4 py-2 text-xs">Word-level details <ArrowRight size={14} /></Link>
    </div>
  );
}

/** Technical session dashboard – rendered for the admin account only (route /admin/patients/:patientId/sessions/:sessionId). */
export default function SessionDashboard() {
  const { sessionId = "", patientId } = useParams();
  const { user } = useAuth();
  const [data, setData] = useState<SessionSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showJson, setShowJson] = useState(false);
  const [patientName, setPatientName] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    setError(null);
    api.sessionSummary(sessionId).then(setData).catch((e: Error) => setError(e.message));
  }, [sessionId]);

  // the admin owns no patients, so the name comes from the admin patient profile
  useEffect(() => {
    if (!patientId || user?.role !== "admin") return;
    api.admin.patient(patientId).then((p) => setPatientName(p.patient.full_name)).catch(() => undefined);
  }, [patientId, user?.role]);

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Spinner />;

  const name = patientName ?? user?.patients.find((p) => p.id === data.patient_id)?.full_name ?? data.patient_id;
  const backTo = patientId ? `/admin/patients/${patientId}` : "/admin/patients";
  const a = data.acoustic_summary;
  const si = data.screening_indicator;

  return (
    <div className="space-y-6">
      {/* header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <Link to={backTo} className="mb-2 inline-flex items-center gap-1 text-xs font-medium text-ink-muted hover:text-ink"><ArrowLeft size={14} /> Patient profile</Link>
          <h1 className="text-[28px] font-extrabold tracking-tight">Screening Results</h1>
          <p className="mt-1 text-sm text-ink-soft">
            Component 1 · ASR Confidence &amp; Speech Feature Output · {name} ({data.patient_id}) · {new Date(data.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex gap-2">
          <Link to={`/admin/pipeline/${data.session_id}`} className="btn-lav"><Sparkles size={16} /> C2 → C3 → C4</Link>
          <button onClick={() => setShowJson((v) => !v)} className="btn-ghost"><Braces size={16} /> {showJson ? "Hide" : "Show"} JSON</button>
          <Link to={`/sessions/${data.session_id}/report`} target="_blank" className="btn-ghost"><FileText size={16} /> Clinical report</Link>
          <button onClick={() => downloadJson(`speakfree-c1-session-${data.session_id}.json`, data)} className="btn-primary"><Download size={16} /> Export</button>
        </div>
      </div>

      {/* headline */}
      <div className="grid gap-5 lg:grid-cols-3">
        <section className="card relative overflow-hidden p-6 lg:col-span-1">
          <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-lav-100" aria-hidden />
          <div className="relative">
            <div className="flex items-center gap-2 text-sm font-bold text-lav-600"><Sparkles size={16} /> ASR Confidence</div>
            <div className="mt-3 flex items-center gap-5">
              <ScoreRing value={data.overall_confidence_percent} suffix="%" size={132} color={COLORS.lav} />
              <div className="space-y-1 text-xs text-ink-soft">
                <div><b className="text-ink">{data.total_token_count}</b> tokens</div>
                <div><b className="text-ink">{data.word_count}</b> words</div>
                <div><b className="text-ink">{data.recording_count}</b> recordings</div>
                <div>mean C<sub>word</sub> <b className="text-ink">{data.mean_word_confidence.toFixed(3)}</b></div>
              </div>
            </div>
            <div className="mt-4 rounded-xl bg-lav-50 p-3 font-mono text-[11px] text-ink-soft">
              C<sub>overall</sub> = (1/N) · Σ exp(logprob<sub>i</sub>) × 100, pooled over all N tokens of the session
            </div>
          </div>
        </section>

        <section className="card flex flex-col items-center justify-center p-6 text-center">
          <div className="text-sm font-bold text-ink-soft">Overall Speech Score</div>
          <div className="my-3"><ScoreRing value={data.overall_speech_score} size={132} sub="/ 100" /></div>
          <div className="text-sm font-bold" style={{ color: scoreColor(data.overall_speech_score) }}>{scoreWord(data.overall_speech_score)}</div>
          <div className="mt-1 text-[11px] muted">0.30·ASR + 0.30·Fluency + 0.25·Pronunciation + 0.15·Articulation · word-weighted across tasks</div>
        </section>

        <section className="card p-6">
          <div className="mb-2 flex items-center gap-2 text-sm font-bold text-ink-soft"><Gauge size={16} /> Screening Level</div>
          <SeverityGauge hint={si.severity_hint} label={si.label} risk={si.risk} />
          <div className={`mt-4 rounded-xl p-3 text-center text-sm ${data.dysfluency_candidate_count ? "bg-bad-soft text-bad" : "bg-ok-soft text-ok"}`}>
            <b>{data.dysfluency_candidate_count}</b> dysfluency candidate{data.dysfluency_candidate_count === 1 ? "" : "s"} · {pct(data.dysfluency_ratio * 100)} of words below C<sub>word</sub> {data.dysfluency_threshold.toFixed(2)}
          </div>
        </section>
      </div>

      {/* score breakdown */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="ASR Score" value={data.asr_accuracy_percent} suffix="%" caption="No reference passage in these tasks, so it is based on ASR confidence" />
        <MetricCard label="Fluency" value={data.fluency_score} caption="Low-confidence words, significant pauses and speaking rate vs. age norms" />
        <MetricCard label="Pronunciation" value={data.pronunciation_score} caption="Mean word confidence (C_word) across all answers" />
        <MetricCard label="Articulation" value={data.articulation_score} caption="Provisional proxy; refined by Component 2's phoneme alignment" />
      </div>

      {/* per task */}
      <div>
        <h2 className="mb-3 flex items-center gap-2 text-lg font-bold"><ListChecks size={19} className="text-navy" /> Results by task</h2>
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {data.tasks.map((t, i) => <TaskResultCard key={t.analysis_id} t={t} name={taskShortName(t, data.tasks, i)} />)}
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <Card title="ASR Confidence by Task" icon={<Sparkles size={16} className="text-lav-500" />}>
          <TaskConfidenceChart tasks={data.tasks} />
        </Card>
        <Card title="Word Confidence Distribution" icon={<Activity size={16} className="text-lav-500" />}>
          <ConfidenceDistribution d={data.confidence_distribution} threshold={data.dysfluency_threshold} />
        </Card>
        <Card title="Lowest-confidence Words" icon={<AlertTriangle size={16} className="text-warn" />}>
          {data.lowest_confidence_words.length ? (
            <ul className="divide-y divide-line text-sm">
              {data.lowest_confidence_words.slice(0, 7).map((w, i) => (
                <li key={i}>
                  <Link to={`/results/${w.analysis_id}`} className="flex items-center gap-3 py-1.5 hover:bg-canvas">
                    <span className={`flex-1 font-semibold ${w.is_dysfluency_candidate ? "text-bad" : "text-warn"}`}>{w.word}</span>
                    <span className="text-[11px] muted">{TASK_LABEL[w.task_type].split(" ")[0]} · {w.start.toFixed(1)}s</span>
                    <span className="w-14 text-right font-mono text-xs">{(w.confidence * 100).toFixed(1)}%</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : <p className="text-sm muted">No words recognised.</p>}
        </Card>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <Card title="Sound-level Findings" icon={<Volume2 size={16} className="text-lav-500" />}>
          {data.phoneme_findings.length
            ? data.phoneme_findings.slice(0, 8).map((f) => <FindingRow key={f.sound} f={f} />)
            : <p className="text-sm muted">Not enough words to estimate.</p>}
          <p className="mt-2 text-[11px] muted">Mean C<sub>word</sub> of words containing each sound (spelling-based, pooled across all tasks). Phoneme-level alignment comes from Component 2.</p>
        </Card>
        <Card title="Acoustic & Prosodic Summary" icon={<Activity size={16} className="text-lav-500" />} className="lg:col-span-2">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {[
              ["Words / min", a.words_per_minute.toFixed(0)],
              ["Articulation rate", `${a.articulation_rate_syll_per_sec.toFixed(2)} syl/s`],
              ["Pitch mean", a.pitch_mean_hz ? `${a.pitch_mean_hz.toFixed(0)} Hz` : "-"],
              ["Energy mean", `${a.energy_mean_db.toFixed(1)} dB`],
              ["SNR (mean / min)", `${a.snr_db.toFixed(0)} / ${a.min_snr_db.toFixed(0)} dB`],
              ["Pauses > 250 ms", `${a.pause_count} (${a.pause_rate_per_min.toFixed(1)}/min)`],
              ["Longest pause", `${a.longest_pause_sec.toFixed(2)} s`],
              ["Speech ratio", pct(a.speech_ratio * 100, 0)],
              ["RMSE mean", a.rmse_mean.toFixed(4)],
              ["ZCR mean", a.zcr_mean.toFixed(4)],
              ["Total audio", `${a.total_duration_sec.toFixed(1)} s`],
              ["Speech time", `${a.total_speech_sec.toFixed(1)} s`],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl border border-line bg-canvas/60 p-3">
                <div className="text-[11px] font-semibold uppercase tracking-wide muted">{label}</div>
                <div className="mt-1 font-mono text-[15px] font-semibold">{value}</div>
              </div>
            ))}
          </div>
          {a.min_snr_db < 10 && (
            <p className="mt-3 flex items-center gap-2 text-xs text-warn"><AlertTriangle size={14} /> At least one recording was noisy (SNR &lt; 10 dB). Its scores may be less reliable.</p>
          )}
        </Card>
      </div>

      <Card title="Method & equations" icon={<Sigma size={16} className="text-lav-500" />}>
        <MethodEquations threshold={data.dysfluency_threshold} />
      </Card>

      <div className="rounded-2xl border border-lav-200 bg-lav-50 p-4 text-xs leading-relaxed text-ink-soft">
        <b className="text-ink">About these results.</b> {si.note} Scores are transparent formulas over Whisper token log-probabilities and
        acoustic features. They support, but do not replace, assessment by a speech-language pathologist.
      </div>

      {showJson && (
        <Card title="Component 1 output – JSON hand-off for Components 2 & 3" icon={<Braces size={16} className="text-lav-500" />}>
          <pre className="max-h-[480px] overflow-auto rounded-xl bg-[#0F1A3D] p-4 font-mono text-xs text-[#DDE3FF] scrollbar-thin">
            {JSON.stringify(data, null, 2)}
          </pre>
        </Card>
      )}
    </div>
  );
}
