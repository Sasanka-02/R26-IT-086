import { useCallback, useEffect, useMemo, useState } from "react";
import "./Component3View.css";

const C3_URL = "http://127.0.0.1:8000/api/v1/component3/analyze";

// Fallback sample Component 2 output so the page can be demoed even if the
// user opens it before running a Component 2 analysis.
const SAMPLE_C2_OUTPUT = {
  component3_ready_output: {
    dysarthria_risk_score: 68.4,
    dysarthria_probability: 0.684,
    risk_level: "high",
    fluency_score: 61,
    word_repetition_count: 4,
    phrase_repetition_count: 1,
    filler_count: 3,
    speech_rate_wpm: 98,
    long_pause_count: 3,
    timing_consistency: null,
    duration_variation: null,
    phoneme_count: 0,
    alignment_reliability: null,
    alignment_uncertain: true,
  },
  clinical_note:
    "Sample Component 2 output used for demonstration of Component 3.",
};

function pct(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

function Bar({ label, value, muted }) {
  const hasValue = value !== null && value !== undefined && !Number.isNaN(value);
  const width = hasValue ? Math.max(2, Math.min(100, value * 100)) : 0;
  return (
    <div className={`c3-bar-row ${muted ? "c3-bar-muted" : ""}`}>
      <span className="c3-bar-label">{label}</span>
      <span className="c3-bar-track">
        <span className="c3-bar-fill" style={{ width: `${width}%` }} />
      </span>
      <span className="c3-bar-value">{hasValue ? pct(value) : "n/a"}</span>
    </div>
  );
}

export default function Component3View({ component2Output, sessionId, onBack }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [usedSample, setUsedSample] = useState(false);

  const payloadC2 = useMemo(
    () => component2Output || SAMPLE_C2_OUTPUT,
    [component2Output]
  );

  const runAnalysis = useCallback(async () => {
    setLoading(true);
    setError("");
    setReport(null);
    setUsedSample(!component2Output);

    try {
      const res = await fetch(C3_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId || `sess-${Date.now()}`,
          user_id: "demo-user",
          component2_output: payloadC2,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Component 3 analysis failed."
        );
      }
      setReport(data);
    } catch (err) {
      setError(
        err.message ||
          "Unable to reach the Component 3 endpoint at " + C3_URL
      );
    } finally {
      setLoading(false);
    }
  }, [component2Output, payloadC2, sessionId]);

  useEffect(() => {
    runAnalysis();
  }, [runAnalysis]);

  const riskClass = report
    ? { Low: "low", Medium: "moderate", High: "high" }[report.risk_level] ||
      "unknown"
    : "unknown";

  const fallbackUsed =
    report?.model_status?.any_untrained_fallback_used === true;

  return (
    <div className="c3-page">
      <header className="c3-header">
        <div className="c3-header-inner">
          <button type="button" className="c3-back" onClick={onBack}>
            ← Back to Component 2
          </button>
          <div className="c3-title-block">
            <span className="c3-eyebrow">COMPONENT 3</span>
            <h1>Multi-Disorder Severity Analysis</h1>
            <p>Classification · Severity · Confidence · Unified Risk</p>
          </div>
          <div className="c3-owner">IT21315114 · I.L.S. Tharushan</div>
        </div>
      </header>

      <main className="c3-container">
        {loading && (
          <section className="c3-card c3-status">
            <span className="c3-spinner" />
            Running Component 3 pipeline…
          </section>
        )}

        {error && !loading && (
          <section className="c3-card c3-error">
            <strong>Component 3 request failed</strong>
            <span>{error}</span>
            <button type="button" className="c3-btn" onClick={runAnalysis}>
              Retry
            </button>
          </section>
        )}

        {report && !loading && (
          <>
            {usedSample && (
              <div className="c3-note c3-note-warn">
                No live Component 2 result was available — this analysis used a
                built-in <strong>sample</strong> Component 2 output.
              </div>
            )}
            {fallbackUsed && (
              <div className="c3-note c3-note-warn">
                One or more models are not trained yet — the pipeline used a
                clearly-flagged heuristic fallback. Run{" "}
                <code>python -m Training.component3.train_all</code>.
              </div>
            )}

            {/* SUMMARY */}
            <section className="c3-card c3-summary">
              <div className="c3-summary-head">
                <div>
                  <span className="c3-label">SCREENING RESULT</span>
                  <h2>{titleCase(report.primary_disorder)}</h2>
                  <p className="c3-session">Session · {report.session_id}</p>
                </div>
                <div className={`c3-risk-pill ${riskClass}`}>
                  {report.risk_level.toUpperCase()} RISK
                </div>
              </div>

              <div className="c3-metric-grid">
                <div className="c3-metric primary">
                  <span>Severity Level</span>
                  <strong>{report.severity_level}</strong>
                  <small>{report.severity_label}</small>
                </div>
                <div className="c3-metric">
                  <span>Detected Disorder</span>
                  <strong>{titleCase(report.primary_disorder)}</strong>
                </div>
                <div className="c3-metric">
                  <span>Confidence</span>
                  <strong>{pct(report.confidence_score)}</strong>
                  <small>{report.confidence_band}</small>
                </div>
                <div className="c3-metric">
                  <span>Professional Review</span>
                  <strong>
                    {report.professional_review_recommended ? "Recommended" : "Not flagged"}
                  </strong>
                </div>
              </div>
            </section>

            {/* DISORDER BREAKDOWN */}
            <section className="c3-card">
              <span className="c3-label">DISORDER BREAKDOWN</span>
              <h3>Multi-disorder probabilities</h3>
              <div className="c3-bars">
                {Object.entries(report.disorder_breakdown).map(([k, v]) => (
                  <Bar key={k} label={titleCase(k)} value={v} />
                ))}
              </div>
            </section>

            {/* SEVERITY BREAKDOWN */}
            <section className="c3-card">
              <span className="c3-label">SEVERITY DISTRIBUTION</span>
              <h3>Level 1 (Normal) → Level 4 (Severe)</h3>
              <div className="c3-bars">
                {Object.entries(report.severity_breakdown).map(([k, v]) => (
                  <Bar key={k} label={`Level ${k}`} value={v} />
                ))}
              </div>
            </section>

            {/* STUTTERING EVENTS */}
            <section className="c3-card">
              <span className="c3-label">STUTTERING EVENTS · MULTI-LABEL</span>
              <h3>Repetition · Prolongation · Block</h3>
              <div className="c3-bars">
                {Object.entries(report.stuttering_events).map(([k, v]) => (
                  <Bar
                    key={k}
                    label={titleCase(k)}
                    value={v}
                    muted={v === null || v === undefined}
                  />
                ))}
              </div>
              {report.stuttering_positive_events?.length > 0 && (
                <p className="c3-inline">
                  Positive (&ge; 0.5):{" "}
                  <strong>
                    {report.stuttering_positive_events.map(titleCase).join(", ")}
                  </strong>
                </p>
              )}
            </section>

            {/* ARTICULATION INDICATORS (from Component 2) */}
            <section className="c3-card">
              <span className="c3-label">ARTICULATION INDICATORS · FROM COMPONENT 2</span>
              <h3>Alignment &amp; articulation analytics used as input</h3>
              <div className="c3-kv-grid">
                {Object.entries(report.articulation_metrics)
                  .filter(([k]) => !["source"].includes(k))
                  .map(([k, v]) => (
                    <div className="c3-kv" key={k}>
                      <span>{titleCase(k)}</span>
                      <strong>{formatVal(v)}</strong>
                    </div>
                  ))}
              </div>
            </section>

            {/* UNCERTAINTY */}
            <section className="c3-card">
              <span className="c3-label">CONFIDENCE &amp; UNCERTAINTY</span>
              <h3>Calibrated probability &amp; ensemble disagreement</h3>
              <div className="c3-kv-grid">
                <div className="c3-kv">
                  <span>Confidence score</span>
                  <strong>{pct(report.uncertainty.confidence_score)}</strong>
                </div>
                <div className="c3-kv">
                  <span>Confidence band</span>
                  <strong>{report.uncertainty.confidence_band}</strong>
                </div>
                <div className="c3-kv">
                  <span>Normalised entropy</span>
                  <strong>{report.uncertainty.normalised_entropy}</strong>
                </div>
                <div className="c3-kv">
                  <span>Epistemic std (RF trees)</span>
                  <strong>{report.uncertainty.epistemic_std}</strong>
                </div>
                <div className="c3-kv">
                  <span>Temperature</span>
                  <strong>{report.uncertainty.temperature}</strong>
                </div>
              </div>
              <p className="c3-fine">{report.uncertainty.method}</p>
            </section>

            {/* UNIFIED SCORE */}
            <section className="c3-card c3-unified">
              <span className="c3-label green">UNIFIED SEVERITY SCORE</span>
              <h3>{report.unified_score.scoring_method}</h3>
              <div className="c3-metric-grid">
                <div className="c3-metric primary">
                  <span>Unified Severity</span>
                  <strong>{report.unified_score.severity_level}</strong>
                  <small>{report.unified_score.severity_label}</small>
                </div>
                <div className="c3-metric">
                  <span>Risk Level</span>
                  <strong>{report.unified_score.risk_level}</strong>
                </div>
                <div className="c3-metric">
                  <span>Confidence</span>
                  <strong>{pct(report.unified_score.confidence_score)}</strong>
                </div>
              </div>
              <ol className="c3-explain">
                {report.unified_score.scoring_explanation.map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ol>
            </section>

            {/* RECOMMENDATIONS */}
            <section className="c3-card">
              <span className="c3-label">CLINICAL SCREENING SUMMARY</span>
              <h3>Recommendations</h3>
              <ul className="c3-recs">
                {report.recommendations.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </section>

            {/* MODEL / DISCLAIMER */}
            <section className="c3-card c3-meta">
              <div className="c3-kv-grid">
                <div className="c3-kv">
                  <span>Model version</span>
                  <strong>{report.model_version}</strong>
                </div>
                <div className="c3-kv">
                  <span>Disorder classifier</span>
                  <strong>{report.model_status.disorder_classifier}</strong>
                </div>
                <div className="c3-kv">
                  <span>Severity estimator</span>
                  <strong>{report.model_status.severity_estimator}</strong>
                </div>
                <div className="c3-kv">
                  <span>Stuttering model</span>
                  <strong>{report.model_status.stuttering_multilabel}</strong>
                </div>
              </div>
              <p className="c3-disclaimer">{report.disclaimer}</p>
              <button type="button" className="c3-btn ghost" onClick={runAnalysis}>
                Re-run analysis
              </button>
            </section>
          </>
        )}
      </main>

      <footer className="c3-footer">
        SpeakFree · Component 3 · Multi-Disorder Severity Classification &amp;
        Risk Prediction
      </footer>
    </div>
  );
}

function titleCase(s) {
  if (!s) return s;
  return String(s)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatVal(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (typeof v === "number") return Number.isInteger(v) ? v : v.toFixed(2);
  return String(v);
}
