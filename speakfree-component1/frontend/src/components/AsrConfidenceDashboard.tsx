/**
 * AsrConfidenceDashboard – "Structured Explainable AI Results"
 *
 *  • Score cards: Overall Speech Score, ASR Score (Accuracy %), Articulation Score (+ ASR confidence)
 *  • Waveform + interactive confidence timeline (regions where C_word < 60 % highlighted)
 *  • Screening indicator (severity hint) + sound-level findings (/s/, /r/, /th/ …)
 *  • Heat-map transcript: C_word ≥ 0.90 ink · 0.60–0.90 amber · < 0.60 red + alert
 *      click a word → tooltip with C_word, sub-token breakdown, timestamps, play-segment button
 *  • Acoustic features + raw JSON contract for Components 2/3
 */
import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent, type ReactNode } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Braces,
  Download,
  Gauge,
  Info,
  Pause,
  Play,
  ShieldCheck,
  Volume2,
  X,
} from "lucide-react";
import { api, localAudio } from "../api/client";
import { TASK_LABEL, type AnalyzeResponse, type PhonemeFinding, type WordSegment } from "../types";
import { Bar, COLORS, ErrorBox, ScoreRing, scoreColor, scoreWord, SeverityGauge, Spinner, pct } from "./ui";

const C = { lav: COLORS.lav, ok: COLORS.ok, brand: COLORS.brand, warn: COLORS.warn, bad: COLORS.bad, ink: COLORS.ink };

// =========================================================================== small UI parts
function Card({ title, icon, children, className = "", right }: { title?: string; icon?: ReactNode; children: ReactNode; className?: string; right?: ReactNode }) {
  return (
    <section className={`card p-5 ${className}`}>
      {title && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-[15px] font-bold text-ink">{icon}{title}</h2>
          {right}
        </div>
      )}
      {children}
    </section>
  );
}

function CircularScore({ value, label, caption, suffix = "" }: { value: number; label: string; caption: string; suffix?: string }) {
  return (
    <div className="card flex flex-col items-center p-5 text-center">
      <div className="text-sm font-bold text-ink-soft">{label}</div>
      <div className="my-3"><ScoreRing value={value} size={124} suffix={suffix} sub={suffix ? undefined : "/ 100"} /></div>
      <div className="text-sm font-bold" style={{ color: scoreColor(value) }}>{scoreWord(value)}</div>
      <div className="mt-1 text-xs muted">{caption}</div>
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-line bg-canvas/60 p-3" title={hint}>
      <div className="text-[11px] font-semibold uppercase tracking-wide muted">{label}</div>
      <div className="mt-1 font-mono text-[15px] font-semibold">{value}</div>
    </div>
  );
}

// =========================================================================== waveform + confidence timeline
function WaveformTimeline({ data, currentTime, onSeek, threshold }: {
  data: AnalyzeResponse; currentTime: number; onSeek: (t: number) => void; threshold: number;
}) {
  const W = 1000;
  const H = 120;
  const CH = 90; // confidence lane height
  const duration = Math.max(data.preprocessing.original_duration_sec, 0.01);
  const x = (t: number) => (t / duration) * W;

  const wavePath = useMemo(() => {
    const peaks = data.waveform_peaks;
    if (!peaks.length) return "";
    const step = W / peaks.length;
    let d = "";
    peaks.forEach((p, i) => {
      const h = Math.max(1, p * (H / 2 - 4));
      const px = (i + 0.5) * step;
      d += `M${px.toFixed(1)},${(H / 2 - h).toFixed(1)}L${px.toFixed(1)},${(H / 2 + h).toFixed(1)}`;
    });
    return d;
  }, [data.waveform_peaks]);

  const confPath = useMemo(() => {
    // step line: each word holds its C_word across its duration
    return data.word_segments
      .map((w, i) => {
        const y = CH - w.confidence * (CH - 6) - 3;
        return `${i === 0 ? "M" : "L"}${x(w.start).toFixed(1)},${y.toFixed(1)}L${x(w.end).toFixed(1)},${y.toFixed(1)}`;
      })
      .join("");
  }, [data.word_segments, duration]);

  const thresholdY = CH - threshold * (CH - 6) - 3;

  function click(e: MouseEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    onSeek(((e.clientX - rect.left) / rect.width) * duration);
  }

  return (
    <div className="space-y-2">
      {/* waveform */}
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="h-28 w-full cursor-pointer rounded-xl bg-[#F4F5FB]" onClick={click} role="img" aria-label="Audio waveform">
        {data.low_confidence_regions.map((r, i) => (
          <rect key={i} x={x(r.start)} y={0} width={Math.max(2, x(r.end) - x(r.start))} height={H} fill={C.bad} opacity={0.12} />
        ))}
        {data.pauses.map((p, i) => (
          <rect key={`p${i}`} x={x(p.start)} y={H - 6} width={Math.max(2, x(p.end) - x(p.start))} height={6} fill={C.warn} opacity={0.7} />
        ))}
        <path d={wavePath} stroke={C.lav} strokeWidth={1.2} vectorEffect="non-scaling-stroke" opacity={0.9} />
        <line x1={x(currentTime)} x2={x(currentTime)} y1={0} y2={H} stroke={C.ink} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
      </svg>
      {/* confidence timeline */}
      <svg viewBox={`0 0 ${W} ${CH}`} preserveAspectRatio="none" className="h-24 w-full cursor-pointer rounded-xl bg-[#F4F5FB]" onClick={click} role="img" aria-label="Word confidence timeline">
        <rect x={0} y={thresholdY} width={W} height={CH - thresholdY} fill={C.bad} opacity={0.07} />
        <line x1={0} x2={W} y1={thresholdY} y2={thresholdY} stroke={C.bad} strokeDasharray="6 6" strokeWidth={1} vectorEffect="non-scaling-stroke" />
        <path d={confPath} fill="none" stroke={C.brand} strokeWidth={2} vectorEffect="non-scaling-stroke" />
        {data.word_segments.filter((w) => w.is_dysfluency_candidate).map((w) => (
          <rect key={w.index} x={x(w.start)} y={CH - w.confidence * (CH - 6) - 5} width={Math.max(3, x(w.end) - x(w.start))} height={4} fill={C.bad} />
        ))}
        <line x1={x(currentTime)} x2={x(currentTime)} y1={0} y2={CH} stroke={C.ink} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] muted">
        <span className="flex items-center gap-1"><span className="h-0.5 w-4 bg-brand" /> Word confidence (C<sub>word</sub>)</span>
        <span className="flex items-center gap-1"><span className="h-0 w-4 border-t border-dashed border-bad" /> {(threshold * 100).toFixed(0)} % dysfluency threshold</span>
        <span className="flex items-center gap-1"><span className="h-2 w-3 bg-bad/20" /> Low-confidence region</span>
        <span className="flex items-center gap-1"><span className="h-1.5 w-3 bg-warn/70" /> Pause &gt; 250 ms</span>
        <span className="ml-auto font-mono">0s - {duration.toFixed(1)}s</span>
      </div>
    </div>
  );
}

// =========================================================================== findings
function FindingRow({ f }: { f: PhonemeFinding }) {
  const color = f.status === "ok" ? C.ok : f.status === "warning" ? C.warn : C.bad;
  return (
    <div className="grid grid-cols-[88px_1fr_44px_18px] items-center gap-3 py-1.5" title={f.flagged_words.length ? `Low-confidence words: ${f.flagged_words.join(", ")}` : `${f.word_count} words`}>
      <span className="font-mono text-sm">{f.sound}</span>
      <Bar value={f.accuracy_percent} color={color} />
      <span className="text-right font-mono text-xs">{f.accuracy_percent.toFixed(0)}%</span>
      {f.status === "ok" ? <ShieldCheck size={16} color={color} /> : <AlertTriangle size={16} color={color} />}
    </div>
  );
}

// =========================================================================== heat-map transcript
function wordClass(w: WordSegment) {
  if (w.level === "high") return "text-ink decoration-brand/50";
  if (w.level === "medium") return "bg-warn-soft text-warn decoration-warn/60";
  return "bg-bad-soft font-bold text-bad decoration-bad/70";
}

function WordTooltip({ w, onClose, onPlay, canPlay, threshold }: {
  w: WordSegment; onClose: () => void; onPlay: () => void; canPlay: boolean; threshold: number;
}) {
  const color = w.level === "high" ? C.ok : w.level === "medium" ? C.warn : C.bad;
  return (
    <div className="card absolute left-1/2 top-full z-30 mt-2 w-72 -translate-x-1/2 p-4 text-left text-sm font-normal text-ink-soft shadow-lift" role="dialog">
      <div className="mb-2 flex items-start justify-between">
        <div>
          <div className="text-base font-bold text-ink">“{w.word}”</div>
          <div className="font-mono text-xs muted">{w.start.toFixed(2)}s → {w.end.toFixed(2)}s ({(w.duration * 1000).toFixed(0)} ms)</div>
        </div>
        <button onClick={onClose} className="text-ink-muted hover:text-ink" aria-label="Close"><X size={16} /></button>
      </div>
      <div className="mb-3 rounded-lg bg-canvas p-2">
        <div className="text-[11px] muted">Linear word confidence C<sub>word</sub> = (1/k)·Σ exp(logprob)</div>
        <div className="font-mono text-2xl font-bold" style={{ color }}>
          {w.confidence.toFixed(4)} <span className="text-sm">({w.confidence_percent.toFixed(1)}%)</span>
        </div>
        {w.is_dysfluency_candidate && (
          <div className="mt-1 flex items-center gap-1 text-xs text-bad"><AlertTriangle size={12} /> Dysfluency candidate (C<sub>word</sub> &lt; {threshold.toFixed(2)})</div>
        )}
      </div>
      <div className="text-[11px] font-semibold uppercase tracking-wide muted">Sub-token breakdown (k = {w.tokens.length})</div>
      <table className="mt-1 w-full font-mono text-xs">
        <thead><tr className="muted"><th className="text-left font-normal">token</th><th className="text-right font-normal">logprob</th><th className="text-right font-normal">P = e^lp</th></tr></thead>
        <tbody>
          {w.tokens.map((t, i) => (
            <tr key={i}>
              <td className="whitespace-pre text-ink">{JSON.stringify(t.token)}</td>
              <td className="text-right">{t.logprob.toFixed(3)}</td>
              <td className="text-right" style={{ color: t.probability < threshold ? C.bad : undefined }}>{t.probability.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <button onClick={onPlay} disabled={!canPlay} className="btn-primary mt-3 w-full py-1.5 text-xs" title={canPlay ? "" : "Recording only available in the browser that recorded it"}>
        <Volume2 size={14} /> Play this segment
      </button>
    </div>
  );
}

// =========================================================================== main dashboard
export default function AsrConfidenceDashboard() {
  const { analysisId = "" } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [showJson, setShowJson] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);
  const stopAtRef = useRef<number | null>(null);
  const rafRef = useRef(0);
  const audioUrl = localAudio.get(analysisId);

  useEffect(() => {
    setData(null);
    setError(null);
    api.result(analysisId).then(setData).catch((e: Error) => setError(e.message));
  }, [analysisId]);

  // smooth playhead while playing + stop at segment end
  const tick = useCallback(() => {
    const a = audioRef.current;
    if (!a) return;
    setCurrentTime(a.currentTime);
    if (stopAtRef.current !== null && a.currentTime >= stopAtRef.current) {
      a.pause();
      stopAtRef.current = null;
    }
    if (!a.paused) rafRef.current = requestAnimationFrame(tick);
  }, []);
  useEffect(() => () => cancelAnimationFrame(rafRef.current), []);

  const seek = (t: number) => {
    setCurrentTime(t);
    if (audioRef.current) audioRef.current.currentTime = t;
  };
  const playSegment = (start: number, end: number) => {
    const a = audioRef.current;
    if (!a) return;
    a.currentTime = Math.max(0, start - 0.05);
    stopAtRef.current = end + 0.05;
    a.play().catch(() => undefined);
  };
  const togglePlay = () => {
    const a = audioRef.current;
    if (!a) return;
    stopAtRef.current = null;
    if (a.paused) a.play().catch(() => undefined);
    else a.pause();
  };

  const downloadJson = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `speakfree-c1-${data.analysis_id}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Spinner />;

  const f = data.acoustic_features;
  const threshold = data.dysfluency_threshold;
  const taskName = TASK_LABEL[data.task_type];

  return (
    <div className="space-y-6">
      {/* header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <button onClick={() => navigate(-1)} className="mb-2 inline-flex items-center gap-1 text-xs font-medium text-ink-muted hover:text-ink"><ArrowLeft size={14} /> Back</button>
          <h1 className="text-[28px] font-extrabold tracking-tight">Word-level Explainable Results</h1>
          <p className="mt-1 text-sm text-ink-soft">
            {taskName} · {new Date(data.created_at).toLocaleString()} · Patient {data.patient_id} · Bracket {data.age_bracket}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowJson((v) => !v)} className="btn-ghost text-sm"><Braces size={16} /> JSON contract</button>
          <button onClick={downloadJson} className="btn-primary text-sm"><Download size={16} /> Export</button>
        </div>
      </div>

      {/* score cards */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <CircularScore value={data.overall_speech_score} label="Overall Speech Score" caption="Weighted: ASR · fluency · pronunciation · articulation" />
        <CircularScore value={data.asr_accuracy_percent} suffix="%" label="ASR Score" caption={data.asr_score_basis === "word_accuracy_vs_reference" ? `Word accuracy vs passage (WER ${(data.wer!.wer * 100).toFixed(1)}%)` : "No reference text – based on ASR confidence"} />
        <CircularScore value={data.articulation_score} label="Articulation Score" caption="Provisional – refined by Component 2 (phoneme alignment)" />
        <div className="card flex flex-col justify-between gap-3 p-5">
          <div className="text-sm font-bold text-lav-600">ASR Confidence (biomarker)</div>
          <div>
            <div className="font-mono text-4xl font-extrabold" style={{ color: scoreColor(data.overall_confidence_percent) }}>{pct(data.overall_confidence_percent)}</div>
            <div className="mt-1 text-[11px] muted">C<sub>overall</sub> = (1/N)·Σ exp(logprob<sub>i</sub>) × 100 · N = {data.model.token_count} tokens</div>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg bg-canvas p-2"><div className="muted">Fluency</div><div className="font-mono text-base font-semibold">{data.fluency_score.toFixed(1)}</div></div>
            <div className="rounded-lg bg-canvas p-2"><div className="muted">Pronunciation</div><div className="font-mono text-base font-semibold">{data.pronunciation_score.toFixed(1)}</div></div>
            <div className={`col-span-2 rounded-lg p-2 ${data.dysfluency_candidate_count ? "bg-bad-soft text-bad" : "bg-ok-soft text-ok"}`}>
              <b>{data.dysfluency_candidate_count}</b> dysfluency candidate{data.dysfluency_candidate_count === 1 ? "" : "s"} ({pct(data.dysfluency_ratio * 100)} of words)
            </div>
          </div>
        </div>
      </div>

      {/* waveform & timeline */}
      <Card title="Waveform & Confidence Timeline" icon={<Activity size={16} className="text-lav-500" />}
        right={
          <div className="flex items-center gap-2">
            {audioUrl ? (
              <button onClick={togglePlay} className="btn-ghost px-3 py-1.5 text-xs">{playing ? <Pause size={14} /> : <Play size={14} />} {playing ? "Pause" : "Play"}</button>
            ) : (
              <span className="text-[11px] muted">Playback available only in the browser that recorded it (audio is never stored on the server)</span>
            )}
          </div>
        }>
        {audioUrl && (
          <audio ref={audioRef} src={audioUrl} preload="auto" className="hidden"
            onPlay={() => { setPlaying(true); rafRef.current = requestAnimationFrame(tick); }}
            onPause={() => { setPlaying(false); setCurrentTime(audioRef.current?.currentTime ?? 0); }}
            onEnded={() => setPlaying(false)} />
        )}
        <WaveformTimeline data={data} currentTime={currentTime} onSeek={seek} threshold={threshold} />
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* heat-map transcript */}
        <Card className="lg:col-span-2" title="Interactive Heat-map Transcript" icon={<Info size={16} className="text-lav-500" />}
          right={
            <div className="flex flex-wrap gap-3 text-[11px]">
              <span className="text-ink">● ≥ 90 %</span>
              <span className="text-warn">● {(threshold * 100).toFixed(0)}–90 %</span>
              <span className="font-bold text-bad">▲ &lt; {(threshold * 100).toFixed(0)} %</span>
            </div>
          }>
          <p className="text-lg leading-[2.4rem]">
            {data.word_segments.map((w) => {
              const active = w.start <= currentTime && currentTime < w.end;
              return (
                <span key={w.index} className="relative inline-block">
                  <button
                    onClick={() => setSelected(selected === w.index ? null : w.index)}
                    title={`C_word ${w.confidence_percent.toFixed(1)}% · ${w.start.toFixed(2)}–${w.end.toFixed(2)}s`}
                    className={`mx-[3px] rounded px-0.5 underline-offset-4 hover:underline ${wordClass(w)} ${active ? "ring-2 ring-lav-400" : ""} ${selected === w.index ? "ring-2 ring-brand" : ""}`}
                  >
                    {w.is_dysfluency_candidate && <AlertTriangle size={13} className="mr-0.5 inline -translate-y-0.5" aria-label="dysfluency candidate" />}
                    {w.word}
                  </button>
                  {selected === w.index && (
                    <WordTooltip w={w} threshold={threshold} canPlay={!!audioUrl}
                      onClose={() => setSelected(null)} onPlay={() => playSegment(w.start, w.end)} />
                  )}
                </span>
              );
            })}
          </p>
          {data.reference_text && (
            <details className="mt-4 rounded-xl bg-canvas p-3 text-sm">
              <summary className="cursor-pointer muted">Reference passage & word errors</summary>
              <p className="mt-2 text-ink-soft">{data.reference_text}</p>
              {data.wer && (
                <p className="mt-2 font-mono text-xs muted">
                  WER {(data.wer.wer * 100).toFixed(1)}% · substitutions {data.wer.substitutions} · deletions {data.wer.deletions} · insertions {data.wer.insertions}
                </p>
              )}
            </details>
          )}
          {data.content_coverage_percent !== null && (
            <p className="mt-3 text-sm muted">Picture content coverage: <b className="text-ink">{data.content_coverage_percent.toFixed(0)}%</b> of expected elements mentioned.</p>
          )}
        </Card>

        {/* severity + phoneme findings */}
        <div className="space-y-6">
          <Card title="Screening Level" icon={<Gauge size={16} className="text-lav-500" />}>
            <SeverityGauge hint={data.screening_indicator.severity_hint} label={data.screening_indicator.label} risk={data.screening_indicator.risk} />
            <p className="mt-3 text-[11px] muted">{data.screening_indicator.note}</p>
          </Card>
          <Card title="Sound-level Findings" icon={<Volume2 size={16} className="text-lav-500" />}>
            {data.phoneme_findings.length ? (
              <div>{data.phoneme_findings.slice(0, 7).map((p) => <FindingRow key={p.sound} f={p} />)}</div>
            ) : (
              <p className="text-sm muted">Not enough words to estimate.</p>
            )}
            <p className="mt-2 text-[11px] muted">Mean C<sub>word</sub> of words containing each sound (spelling-based). Phoneme-level alignment comes from Component 2.</p>
          </Card>
        </div>
      </div>

      {/* acoustic features */}
      <Card title="Acoustic & Prosodic Features" icon={<Activity size={16} className="text-lav-500" />}>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <Stat label="Words / min" value={f.words_per_minute.toFixed(0)} hint="Words ÷ analysed minutes (incl. pauses)" />
          <Stat label="Artic. rate" value={`${f.articulation_rate_syll_per_sec.toFixed(2)} syl/s`} hint="Syllables ÷ speech time (pauses excluded)" />
          <Stat label="Energy mean" value={`${f.energy_mean_db.toFixed(1)} dB`} />
          <Stat label="RMSE" value={f.rmse_mean.toFixed(4)} hint={`std ${f.rmse_std.toFixed(4)}`} />
          <Stat label="ZCR" value={f.zcr_mean.toFixed(4)} hint={`std ${f.zcr_std.toFixed(4)}`} />
          <Stat label="SNR" value={`${f.snr_db.toFixed(1)} dB`} hint="Recording quality: > 20 dB good, < 10 dB noisy" />
          <Stat label="Pauses > 250 ms" value={String(f.pause_count)} hint={`${f.pause_rate_per_min.toFixed(1)} per minute`} />
          <Stat label="Longest pause" value={`${f.longest_pause_sec.toFixed(2)} s`} />
          <Stat label="Speech ratio" value={pct(f.speech_ratio * 100, 0)} />
          <Stat label="Pitch mean" value={f.pitch_mean_hz ? `${f.pitch_mean_hz.toFixed(0)} Hz` : "-"} hint={`std ${f.pitch_std_hz.toFixed(0)} Hz`} />
          <Stat label="Duration" value={`${f.duration_sec.toFixed(1)} s`} />
          <Stat label="Processing" value={`${(data.processing_time_ms / 1000).toFixed(1)} s`} hint={`${data.model.asr} on ${data.model.device}`} />
        </div>
        {f.snr_db < 10 && (
          <p className="mt-3 flex items-center gap-2 text-xs text-warn"><AlertTriangle size={14} /> Background noise is high (SNR &lt; 10 dB). Results may be less reliable – consider re-recording in a quieter place.</p>
        )}
      </Card>

      {showJson && (
        <Card title="Inter-component JSON payload (Components 2 & 3)" icon={<Braces size={16} className="text-lav-500" />}>
          <pre className="max-h-[480px] overflow-auto scrollbar-thin rounded-xl bg-[#0F1A3D] p-4 font-mono text-xs text-[#DDE3FF]">
            {JSON.stringify({ ...data, waveform_peaks: `[${data.waveform_peaks.length} values]` }, null, 2)}
          </pre>
        </Card>
      )}
    </div>
  );
}
