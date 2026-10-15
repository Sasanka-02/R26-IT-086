/**
 * ClinicalReport – printable, therapist-facing report of one screening session (all technical
 * metrics + the method/equations). Rendered without the app shell so "Save as PDF" is clean.
 * Opened from the patient view ("Download Clinical Report", ?print=1 opens the print dialog)
 * and from the admin session dashboard.
 */
import { useEffect, useState, type ReactNode } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { Printer } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import MethodEquations from "../components/MethodEquations";
import { ErrorBox, Logo, Spinner } from "../components/ui";
import { TASK_LABEL, type SessionSummary } from "../types";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="break-inside-avoid-page">
      <h2 className="mb-3 border-b border-line pb-1 text-base font-bold text-navy">{title}</h2>
      {children}
    </section>
  );
}

function Table({ head, rows }: { head: string[]; rows: (string | number)[][] }) {
  return (
    <table className="w-full border-collapse text-[13px]">
      <thead><tr>{head.map((h, i) => <th key={h} className={`border-b border-line bg-canvas px-2 py-1.5 font-semibold text-ink-soft ${i ? "text-right" : "text-left"}`}>{h}</th>)}</tr></thead>
      <tbody>
        {rows.map((r, ri) => (
          <tr key={ri} className="break-inside-avoid">
            {r.map((c, i) => <td key={i} className={`border-b border-line px-2 py-1.5 ${i ? "text-right font-mono" : "text-left"}`}>{c}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

const f1 = (v: number) => v.toFixed(1);

export default function ClinicalReport() {
  const { sessionId = "" } = useParams();
  const [params] = useSearchParams();
  const { user } = useAuth();
  const [data, setData] = useState<SessionSummary | null>(null);
  const [name, setName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.sessionSummary(sessionId).then(setData).catch((e: Error) => setError(e.message));
  }, [sessionId]);

  useEffect(() => {
    if (!data) return;
    const own = user?.patients.find((p) => p.id === data.patient_id);
    if (own) setName(own.full_name);
    else if (user?.role === "admin") api.admin.patient(data.patient_id).then((p) => setName(p.patient.full_name)).catch(() => undefined);
  }, [data, user]);

  // ?print=1 → open the browser's print / "Save as PDF" dialog once the report has rendered
  useEffect(() => {
    if (!data || params.get("print") !== "1") return;
    const t = window.setTimeout(() => window.print(), 600);
    return () => window.clearTimeout(t);
  }, [data, params]);

  if (error) return <div className="mx-auto max-w-3xl p-8"><ErrorBox message={error} /></div>;
  if (!data) return <Spinner className="min-h-screen" />;

  const si = data.screening_indicator;
  const a = data.acoustic_summary;
  const d = data.confidence_distribution;
  const total = Math.max(1, d.high + d.medium + d.low);
  let q = 0;
  const taskName = (t: SessionSummary["tasks"][number]) => (t.task_type === "questions" ? `Question ${++q}` : TASK_LABEL[t.task_type]);
  const named = data.tasks.map((t) => ({ t, name: taskName(t) }));

  return (
    <div className="min-h-screen bg-canvas py-8 print:bg-white print:py-0">
      <div className="mx-auto mb-4 flex max-w-[860px] justify-end gap-2 px-4 print:hidden">
        <button onClick={() => window.print()} className="btn-primary"><Printer size={16} /> Print / Save as PDF</button>
      </div>
      <article className="mx-auto max-w-[860px] space-y-7 bg-white p-8 shadow-card print:max-w-none print:p-0 print:shadow-none sm:rounded-2xl">
        <header className="flex flex-wrap items-start justify-between gap-4 border-b-2 border-navy pb-4">
          <Logo subtitle={false} />
          <div className="text-right">
            <h1 className="text-xl font-extrabold text-ink">Clinical Screening Report</h1>
            <p className="text-xs text-ink-soft">Feature 1 · Speech Screening &amp; Feature Extraction</p>
          </div>
        </header>

        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
          {[
            ["Patient", name ?? "-"],
            ["Patient ID", data.patient_id],
            ["Age bracket", `Bracket ${data.age_bracket}`],
            ["Session date", new Date(data.created_at).toLocaleString()],
            ["Session ID", data.session_id.slice(0, 8)],
            ["Recordings", String(data.recording_count)],
            ["Report generated", new Date().toLocaleString()],
            ["Schema", data.schema_version],
          ].map(([k, v]) => (
            <div key={k}><dt className="text-[11px] font-semibold uppercase tracking-wide muted">{k}</dt><dd className="font-semibold text-ink">{v}</dd></div>
          ))}
        </dl>

        <Section title="Screening summary">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-line p-3"><div className="text-xs muted">Overall speech score</div><div className="text-2xl font-extrabold text-ink">{f1(data.overall_speech_score)} <span className="text-sm font-medium muted">/ 100</span></div></div>
            <div className="rounded-xl border border-line p-3"><div className="text-xs muted">Screening level</div><div className="text-2xl font-extrabold text-ink">{si.severity_hint} / 4</div><div className="text-xs text-ink-soft">{si.label} · risk {si.risk}</div></div>
            <div className="rounded-xl border border-line p-3"><div className="text-xs muted">ASR confidence (C<sub>overall</sub>, pooled)</div><div className="text-2xl font-extrabold text-ink">{f1(data.overall_confidence_percent)}%</div><div className="text-xs text-ink-soft">{data.total_token_count} tokens · {data.word_count} words · mean C<sub>word</sub> {data.mean_word_confidence.toFixed(3)}</div></div>
          </div>
          <p className="mt-3 text-sm text-ink-soft">
            Dysfluency candidates: <b className="text-ink">{data.dysfluency_candidate_count}</b> ({f1(data.dysfluency_ratio * 100)}% of words below C<sub>word</sub> {data.dysfluency_threshold.toFixed(2)}).
          </p>
        </Section>

        <Section title="Core metrics">
          <Table head={["Metric", "Score"]} rows={[
            ["ASR score (accuracy %)", `${f1(data.asr_accuracy_percent)}%`],
            ["Fluency", f1(data.fluency_score)],
            ["Pronunciation", f1(data.pronunciation_score)],
            ["Articulation (provisional)", f1(data.articulation_score)],
          ]} />
        </Section>

        <Section title="Results by task">
          <Table head={["Task", "ASR conf.", "Score", "Flags", "Words", "WPM", "Pauses", "SNR dB"]}
            rows={named.map(({ t, name: n }) => [n, `${f1(t.overall_confidence_percent)}%`, f1(t.overall_speech_score), t.dysfluency_candidate_count, t.word_count, t.words_per_minute.toFixed(0), t.pause_count, t.snr_db.toFixed(0)])} />
          <div className="mt-4 space-y-3">
            {named.map(({ t, name: n }) => (
              <div key={t.analysis_id} className="break-inside-avoid rounded-xl border border-line p-3 text-sm">
                <div className="font-semibold text-ink">{n} <span className="font-normal text-ink-soft">· {t.title}</span></div>
                <p className="mt-1 italic text-ink-soft">“{t.transcript || "-"}”</p>
              </div>
            ))}
          </div>
        </Section>

        <div className="grid gap-7 md:grid-cols-2">
          <Section title="Word confidence distribution">
            <Table head={["Band", "Words", "%"]} rows={[
              ["High (≥ 90 %)", d.high, `${((d.high / total) * 100).toFixed(0)}%`],
              [`Medium (${(data.dysfluency_threshold * 100).toFixed(0)}–90 %)`, d.medium, `${((d.medium / total) * 100).toFixed(0)}%`],
              [`Low (< ${(data.dysfluency_threshold * 100).toFixed(0)} %)`, d.low, `${((d.low / total) * 100).toFixed(0)}%`],
            ]} />
          </Section>
          <Section title="Sound-level findings">
            <Table head={["Sound", "Accuracy", "Words", "Status"]}
              rows={data.phoneme_findings.map((p) => [p.sound, `${p.accuracy_percent.toFixed(0)}%`, p.word_count, p.status])} />
          </Section>
        </div>

        <Section title="Lowest-confidence words">
          <Table head={["Word", "Task", "Time (s)", "Confidence"]}
            rows={data.lowest_confidence_words.map((w) => [w.word, TASK_LABEL[w.task_type], w.start.toFixed(1), `${(w.confidence * 100).toFixed(1)}%`])} />
        </Section>

        <Section title="Acoustic & prosodic summary">
          <Table head={["Measure", "Value"]} rows={[
            ["Words / min", a.words_per_minute.toFixed(0)],
            ["Articulation rate", `${a.articulation_rate_syll_per_sec.toFixed(2)} syl/s`],
            ["Pitch mean", a.pitch_mean_hz ? `${a.pitch_mean_hz.toFixed(0)} Hz` : "-"],
            ["Energy mean", `${a.energy_mean_db.toFixed(1)} dB`],
            ["SNR (mean / min)", `${a.snr_db.toFixed(0)} / ${a.min_snr_db.toFixed(0)} dB`],
            ["Pauses > 250 ms", `${a.pause_count} (${a.pause_rate_per_min.toFixed(1)}/min)`],
            ["Longest pause", `${a.longest_pause_sec.toFixed(2)} s`],
            ["Speech ratio", `${(a.speech_ratio * 100).toFixed(0)}%`],
            ["RMSE mean / ZCR mean", `${a.rmse_mean.toFixed(4)} / ${a.zcr_mean.toFixed(4)}`],
            ["Total audio / speech time", `${a.total_duration_sec.toFixed(1)} s / ${a.total_speech_sec.toFixed(1)} s`],
          ]} />
        </Section>

        <Section title="Method & equations">
          <MethodEquations threshold={data.dysfluency_threshold} />
        </Section>

        <footer className="border-t border-line pt-3 text-xs leading-relaxed text-ink-muted">
          {si.note} This report is a screening aid and does not replace assessment by a qualified speech-language pathologist.
          Raw audio is not retained; all values are derived measurements.
        </footer>
      </article>
    </div>
  );
}
