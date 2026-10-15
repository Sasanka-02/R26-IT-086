/**
 * MethodEquations – every formula behind the Component 1 scores, exactly as implemented in
 * backend/asr_service.py (Eq. 1–3), scoring.py (scores, screening level) and session_summary.py (pooling).
 * Shown in the admin session dashboard and the printable clinical report.
 */
import type { ReactNode } from "react";

function Eq({ name, children, note }: { name: string; children: ReactNode; note?: ReactNode }) {
  return (
    <div className="rounded-xl border border-line bg-canvas/60 p-3 break-inside-avoid">
      <div className="text-xs font-bold uppercase tracking-wide text-lav-600">{name}</div>
      <div className="mt-1 font-mono text-[13px] leading-relaxed text-ink">{children}</div>
      {note && <div className="mt-1 text-[11px] leading-snug muted">{note}</div>}
    </div>
  );
}

export default function MethodEquations({ threshold = 0.6 }: { threshold?: number }) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <Eq name="Eq. 1 · Token probability" note="logprob_i = log P(t_i | audio, t_<i), from teacher-forced Whisper decoding">
        P(t<sub>i</sub>) = exp(logprob<sub>i</sub>)
      </Eq>
      <Eq name="Eq. 2 · Word confidence" note={<>k = sub-word (BPE) tokens in the word · dysfluency candidate if C<sub>word</sub> &lt; {threshold.toFixed(2)}</>}>
        C<sub>word</sub> = (1/k) · Σ<sub>i=1..k</sub> exp(logprob<sub>i</sub>)
      </Eq>
      <Eq name="Eq. 3 · Overall ASR confidence" note="N = all recognised tokens of the recording">
        C<sub>overall</sub> = ((1/N) · Σ<sub>i=1..N</sub> exp(logprob<sub>i</sub>)) × 100
      </Eq>
      <Eq name="Session pooling" note="Eq. 3 over every token of the session; scores weighted by each recording's word count w_r">
        C<sub>session</sub> = Σ<sub>r</sub>(C<sub>overall,r</sub> · N<sub>r</sub>) / Σ<sub>r</sub> N<sub>r</sub> · Score<sub>session</sub> = Σ<sub>r</sub>(Score<sub>r</sub> · w<sub>r</sub>) / Σ<sub>r</sub> w<sub>r</sub>
      </Eq>
      <Eq name="ASR score" note="Reading task: word accuracy against the passage. Picture / scenario / questions have no reference, so C_overall is used.">
        ASR = (1 − WER) × 100 &nbsp;|&nbsp; ASR = C<sub>overall</sub>
      </Eq>
      <Eq name="Fluency" note="pause_score: ≤ 4 significant pauses/min = 1, falls to 0 at 20/min, penalised for pauses > 2 s · rate_score: WPM vs. age-bracket norm">
        100 × [0.50·(1 − dysfluency_ratio) + 0.25·pause_score + 0.25·rate_score]
      </Eq>
      <Eq name="Pronunciation" note="Reading: 0.60·mean(C_word) + 0.40·word_accuracy · other tasks: mean(C_word)">
        100 × mean(C<sub>word</sub>)
      </Eq>
      <Eq name="Articulation (provisional)" note="Proxy until Feature 2 provides phoneme-level alignment · articulation-rate score vs. age norm">
        100 × [0.70·pronunciation + 0.30·articulation_rate_score]
      </Eq>
      <Eq name="Overall speech score">
        0.30·ASR + 0.30·Fluency + 0.25·Pronunciation + 0.15·Articulation
      </Eq>
      <Eq name="Screening level (1–4)" note="Preliminary indicator only – final disorder type and severity come from Feature 3 and clinical judgement.">
        ≥ 85 → 1 typical · ≥ 70 → 2 mild · ≥ 55 → 3 moderate · &lt; 55 → 4 significant
      </Eq>
      <Eq name="Sound-level findings" note="Spelling-based: mean C_word of all words containing the sound's letter pattern (e.g. /θ/ = 'th').">
        accuracy(sound) = mean(C<sub>word</sub> of words with that sound) × 100
      </Eq>
      <Eq name="Hallucination guard" note="Applied before Eq. 1–3: non-speech and decoding loops are excluded so they cannot inflate confidence.">
        drop segment if no_speech ≥ 0.75, or compression &gt; 2.4 and &gt; 8 words/s
      </Eq>
    </div>
  );
}
