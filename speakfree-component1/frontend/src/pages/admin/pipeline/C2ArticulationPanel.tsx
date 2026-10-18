/**
 * Component 2 dashboard – ★ NOVELTY: the articulation score.
 * Shows each equation with this session's numbers substituted in, the per-recording scores,
 * the session pooling (C2-Eq.5) and the fluency events handed to Component 3.
 */
import { AlertTriangle, ListChecks, Repeat, Sigma } from "lucide-react";
import { Bar, Card, COLORS, ScoreRing, scoreColor } from "../../../components/ui";
import { EquationCard, HBars, StatTile } from "../../../components/charts";
import type { C2Articulation, C2Report } from "../../../types/integration";

const LEVEL_TEXT: Record<string, string> = { good: "Good", fair: "Fair", poor: "Poor", very_poor: "Very poor" };
const n = (v: unknown, d = 2) => (typeof v === "number" ? v.toFixed(d) : "–");

function Substitution({ a }: { a: C2Articulation }) {
  const i = a.inputs ?? {};
  if (a.method === "A_word_accuracy") {
    return <>WA = 100 × max(0, 1 − ({i.S} + {i.D} + {i.I}) / {i.N_reference_words}) = <b>{n(a.articulation_score)}</b></>;
  }
  if (i.C_confidence === null || i.C_confidence === undefined) {
    return <>A = 100 × CWR = 100 × {n(i.CWR_clear_word_ratio, 4)} = <b>{n(a.articulation_score)}</b></>;
  }
  return (
    <>C = {n(i.C_confidence, 4)} ({i.M_kept_tokens ?? "?"} tokens) · CWR = ({i.N_kept_words} − {i.L_dysfluency_candidates}) / {i.N_kept_words} = {n(i.CWR_clear_word_ratio, 4)}
      <br />A = 100 × (0.5 × {n(i.C_confidence, 4)} + 0.5 × {n(i.CWR_clear_word_ratio, 4)}) = <b>{n(a.articulation_score)}</b></>
  );
}

export default function C2ArticulationPanel({ c2 }: { c2: C2Report }) {
  const s = c2.session_articulation;
  const ev = c2.fluency_events;
  const scored = c2.recordings.filter((r) => r.articulation.status === "scored");
  const weights = s.weights ?? [];

  return (
    <div className="space-y-5">
      <section className="grid gap-5 lg:grid-cols-[300px_1fr]">
        <Card title="Session articulation score">
          <div className="flex flex-col items-center gap-2 text-center">
            {s.score !== null ? <ScoreRing value={s.score} size={150} stroke={14} sub="/ 100" /> : <p className="muted">Insufficient data</p>}
            {s.level && <div className="text-lg font-bold" style={{ color: scoreColor(s.score ?? 0) }}>{LEVEL_TEXT[s.level] ?? s.level}</div>}
            <div className="text-xs muted">{s.scored_recordings} recordings · {s.total_weighted_words ?? 0} weighted words · reliability {s.reliability}</div>
            {(s.reliability_flags ?? []).length > 0 && (
              <div className="mt-1 flex flex-wrap justify-center gap-1">
                {s.reliability_flags!.map((f) => <span key={f} className="chip bg-warn-soft text-ink"><AlertTriangle size={12} className="text-warn" />{f.replace(/_/g, " ")}</span>)}
              </div>
            )}
          </div>
        </Card>

        {/* ★ NOVELTY (Component 2): the articulation-score equations C2-Eq.2–5, shown with this session's numbers */}
        <Card title="Articulation-score equations" icon={<Sigma size={18} className="text-navy" />}>
          <div className="grid gap-3 md:grid-cols-2">
            <EquationCard id="C2-Eq.2" name="Kept-token confidence" formula="C = (1/M) · Σ P(tⱼ)">
              Fillers {"{um, uh, er, …}"} removed first · pooled C = {n(s.pooled_confidence_C, 4)}
            </EquationCard>
            <EquationCard id="C2-Eq.3" name="Clear-word ratio" formula="CWR = (N − L) / N">
              L = kept words with C_word &lt; 0.60 (C1 Eq.2) · pooled CWR = {n(s.pooled_clear_word_ratio, 4)}
            </EquationCard>
            <EquationCard id="C2-Eq.4" name="Articulation score" formula="A = 100 × (0.5·C + 0.5·CWR)">
              free speech (picture · scenario · questions)
            </EquationCard>
            <EquationCard id="C2-Eq.5" name="Session pooling" formula="A_session = Σ Nᵣ·Aᵣ / Σ Nᵣ">
              = ({scored.map((r, i) => `${weights[i] ?? "?"}×${n(r.articulation.articulation_score, 1)}`).join(" + ")}) / {s.total_weighted_words} = {n(s.score)}
            </EquationCard>
          </div>
          <p className="mt-3 text-xs muted">Reading tasks with a reference text use C2-Eq.1: WA = 100 × max(0, 1 − (S + D + I) / N) (Levenshtein alignment after filler removal).</p>
        </Card>
      </section>

      <Card title="Per-recording calculation" icon={<ListChecks size={18} className="text-navy" />}>
        <div className="space-y-3">
          {c2.recordings.map((r) => {
            const a = r.articulation;
            return (
              <div key={r.analysis_id} className="rounded-xl border border-line p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="text-sm font-bold text-ink">{r.title}</div>
                    <div className="text-xs muted">{r.task_type} · {r.duration_sec.toFixed(1)} s · weight Nᵣ = {weights[scored.indexOf(r)] ?? 0} · fillers removed {a.filler_count}</div>
                  </div>
                  <div className="w-40">
                    <div className="mb-1 text-right font-mono text-sm font-bold">{a.status === "scored" ? n(a.articulation_score) : "not scored"}</div>
                    <Bar value={a.articulation_score ?? 0} />
                  </div>
                </div>
                {a.status === "scored" ? (
                  <div className="mt-2 rounded-lg bg-canvas p-3 font-mono text-xs text-ink-soft"><Substitution a={a} /></div>
                ) : <p className="mt-2 text-xs muted">{a.message}</p>}
                <p className="mt-2 line-clamp-2 text-xs italic text-ink-soft">“{r.transcript}”</p>
              </div>
            );
          })}
        </div>
      </Card>

      <section className="grid gap-5 lg:grid-cols-2">
        <Card title="Fluency events → Component 3" icon={<Repeat size={18} className="text-navy" />}>
          <HBars format={(v) => String(v)} data={[
            { key: "fill", label: "Fillers (um, uh…)", value: ev.filler_count, color: COLORS.lav },
            { key: "wrep", label: "Word repetitions", value: ev.word_repetition_count, color: COLORS.lav },
            { key: "prep", label: "Phrase repetitions", value: ev.phrase_repetition_count, color: COLORS.lav },
            { key: "prol", label: "Prolonged words", value: ev.prolongation_count, color: COLORS.lav },
            { key: "lp", label: "Long pauses (≥ 1 s)", value: ev.long_pause_count, color: COLORS.lav },
          ]} max={Math.max(5, ev.filler_count, ev.word_repetition_count, ev.long_pause_count, ev.prolongation_count)} />
        </Card>
        <div className="grid grid-cols-2 gap-4 content-start">
          <StatTile label="Filler rate" value={`${((ev.filler_rate ?? 0) * 100).toFixed(1)}%`} sub="of all words" />
          <StatTile label="Repetition rate" value={`${((ev.repetition_rate ?? 0) * 100).toFixed(1)}%`} sub="of content words" />
          <StatTile label="Prolongation rate" value={`${((ev.prolongation_rate ?? 0) * 100).toFixed(1)}%`} sub="of content words" />
          <StatTile label="Long pauses / min" value={(ev.long_pauses_per_min ?? 0).toFixed(2)} sub={`longest ${ev.longest_pause_sec.toFixed(2)} s`} />
        </div>
      </section>
    </div>
  );
}
