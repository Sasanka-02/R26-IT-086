import { ExtractFeaturesResponse } from "../types";

interface ResultsPanelProps {
  result: ExtractFeaturesResponse;
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-lg font-semibold text-slate-900">{value}</p>
    </div>
  );
}

export default function ResultsPanel({ result }: ResultsPanelProps) {
  return (
    <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div>
        <h3 className="text-sm font-semibold text-slate-500">Transcript</h3>
        <p className="mt-1 rounded-md bg-slate-50 p-3 text-slate-800">
          {result.asr_result.transcript || "(no transcript returned)"}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          label="ASR Confidence"
          value={`${Math.round(result.asr_result.average_confidence * 100)}%`}
        />
        <StatCard
          label="Words / min"
          value={result.fluency_metrics.words_per_minute.toFixed(1)}
        />
        <StatCard
          label="Articulation rate"
          value={result.fluency_metrics.articulation_rate.toFixed(2)}
        />
        <StatCard
          label="Dysfluency density"
          value={result.fluency_metrics.estimated_dysfluency_density.toFixed(2)}
        />
        <StatCard
          label="Duration (s)"
          value={result.audio_metadata.duration_seconds.toFixed(1)}
        />
        <StatCard label="SNR (dB)" value={result.audio_metadata.snr_db.toFixed(1)} />
        <StatCard
          label="Tempo (BPM)"
          value={result.acoustic_features.tempo_bpm.toFixed(1)}
        />
        <StatCard
          label="Processing time"
          value={`${result.processing_time_seconds.toFixed(2)}s`}
        />
      </div>

      {result.asr_result.low_confidence_segments.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-500">
            Low-confidence segments (possible dysfluency markers)
          </h3>
          <ul className="mt-2 space-y-1">
            {result.asr_result.low_confidence_segments.map((seg, idx) => (
              <li
                key={`${seg.word}-${idx}`}
                className="flex justify-between rounded-md bg-amber-50 px-3 py-1.5 text-sm text-amber-800"
              >
                <span>
                  "{seg.word}" ({seg.start.toFixed(1)}s–{seg.end.toFixed(1)}s)
                </span>
                <span className="font-medium">
                  {Math.round(seg.confidence * 100)}%
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
