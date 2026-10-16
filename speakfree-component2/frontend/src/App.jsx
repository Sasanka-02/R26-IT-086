import { useState } from "react";
import axios from "axios";
import "./App.css";

const API_BASE = "http://localhost:8000/api/v1";
const DELIVERY_TEXT = {
  sent: "Sent to Component 3.",
  failed: "Could not reach Component 3",
  not_configured: "Not sent: SPEAKFREE_COMPONENT3_URL is not set on the backend.",
  not_sent: "Not sent: no articulation score was produced.",
};

function DisplayValue({ value }) {
  if (value === null || value === undefined || value === "") return "Not available";
  return typeof value === "number" ? String(Number(value.toFixed(4))) : String(value);
}

function errorText(error) {
  const detail = error?.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map((d) => `${d.loc?.slice(1).join(".")}: ${d.msg}`).join("; ");
  return detail || "Request failed. Check that the backend is running and see its terminal for details.";
}

function downloadBlob(content, type, filename) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function Calculation({ score }) {
  const i = score.inputs;
  if (score.method === "A_word_accuracy") {
    return (
      <>
        <p className="equation">
          WA = 100 × max(0, 1 − ({i.S} + {i.D} + {i.I}) ÷ {i.N_reference_words}) = {score.articulation_score}
        </p>
        <div className="data-table">
          <div><span>Reference text</span><strong>{i.reference_text}</strong></div>
          <div><span>Kept words (fillers removed)</span><strong>{i.kept_words.join(" ")}</strong></div>
          <div><span>N: reference words</span><strong>{i.N_reference_words}</strong></div>
          <div><span>Correct words</span><strong>{i.correct_words}</strong></div>
          <div><span>S: substituted words</span><strong>{i.S}</strong></div>
          <div><span>D: deleted (missed) words</span><strong>{i.D}</strong></div>
          <div><span>I: inserted words</span><strong>{i.I}</strong></div>
        </div>
      </>
    );
  }
  return (
    <>
      <p className="equation">
        {i.C_confidence === null
          ? `Score = 100 × CWR = 100 × ${i.CWR_clear_word_ratio} = ${score.articulation_score}`
          : `Score = 100 × (0.5 × ${i.C_confidence} + 0.5 × ${i.CWR_clear_word_ratio}) = ${score.articulation_score}`}
      </p>
      <div className="data-table">
        <div><span>N: kept words (fillers removed)</span><strong>{i.N_kept_words}</strong></div>
        <div><span>M: tokens of kept words</span><strong><DisplayValue value={i.M_kept_tokens} /></strong></div>
        <div><span>C: mean token probability (Component 1 Eq. 3)</span><strong><DisplayValue value={i.C_confidence} /></strong></div>
        <div><span>C taken from</span><strong><DisplayValue value={i.C_source} /></strong></div>
        <div><span>L: dysfluency candidates (C_word &lt; {i.dysfluency_threshold})</span><strong>{i.L_dysfluency_candidates}</strong></div>
        <div><span>CWR = (N − L) ÷ N</span><strong>{i.CWR_clear_word_ratio}</strong></div>
      </div>
    </>
  );
}

export default function App() {
  const [component1, setComponent1] = useState(null);
  const [component1Name, setComponent1Name] = useState("");
  const [result, setResult] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleComponent1File = async (selected) => {
    setResult(null);
    setMessage("");
    setComponent1(null);
    setComponent1Name("");
    if (!selected) return;
    try {
      const parsed = JSON.parse(await selected.text());
      if (!parsed.session_id || !parsed.task_type) {
        setMessage("This JSON is missing session_id or task_type. Is it a Component 1 output file?");
        return;
      }
      setComponent1(parsed);
      setComponent1Name(selected.name);
    } catch {
      setMessage("Could not read the file as JSON.");
    }
  };

  const handleAnalyze = async () => {
    if (!component1) {
      setMessage("Please load a Component 1 output JSON file.");
      return;
    }
    try {
      setLoading(true);
      setResult(null);
      const data = (await axios.post(`${API_BASE}/component2/from-component1`, component1)).data;
      setResult(data);
      const delivery = data.component3_delivery;
      setMessage(data.ready_for_component3
        ? `Articulation score calculated. ${DELIVERY_TEXT[delivery.status]}${delivery.error ? `: ${delivery.error}` : ""}`
        : data.message || "No articulation score could be calculated.");
    } catch (error) {
      setMessage(errorText(error));
    } finally {
      setLoading(false);
    }
  };

  const score = result?.articulation_score;
  const component3 = result?.component3_input;

  return (
    <main className="page">
      <section className="card">
        <div className="eyebrow">SPEAKFREE · COMPONENT 2</div>
        <h1>Articulation Score</h1>
        <p className="intro">
          Reads the JSON produced by Component 1, calculates a 0–100 articulation score from how
          clearly the words were recognised, and sends the result to Component 3.
        </p>

        <section className="panel">
          <h2>Component 1 output</h2>
          <input type="file" accept=".json,application/json"
            onChange={(event) => handleComponent1File(event.target.files?.[0] || null)} />
          {component1 && (
            <div className="selected-file">
              <strong>{component1Name}</strong>
              <span className="muted">
                Session <strong>{component1.session_id}</strong> · task <strong>{component1.task_type}</strong>
              </span>
              {component1.transcript && <blockquote>{component1.transcript}</blockquote>}
            </div>
          )}
        </section>

        <button className="primary-button" disabled={loading} onClick={handleAnalyze}>
          {loading ? "Calculating…" : "Calculate and send to Component 3"}
        </button>
        {message && <p className="message" role="status">{message}</p>}

        {score?.status === "scored" && (
          <section className="results">
            <div className="score-grid">
              <div className="score-card">
                <span>Articulation score</span>
                <strong>{score.articulation_score}<small> / 100 · {score.articulation_level}</small></strong>
                <p>
                  {score.method === "A_word_accuracy"
                    ? "Method A: word accuracy against the reading passage (Maier et al., 2009)."
                    : "Method B: ASR confidence and clear-word ratio."}
                  {" "}Fillers removed: {score.filler_count}.
                </p>
              </div>
              <div className="score-card">
                <span>Reliability</span>
                <strong>{score.reliability}</strong>
                <p>{score.reliability_flags.join(" · ") || "No issues detected."}</p>
              </div>
            </div>

            <h3>Calculation</h3>
            <Calculation score={score} />

            {component3 && (
              <>
                <h3>Sent to Component 3</h3>
                <pre>{JSON.stringify(component3, null, 2)}</pre>
                <button type="button" className="secondary-button"
                  onClick={() => downloadBlob(JSON.stringify(component3, null, 2), "application/json",
                    `component3_input_${component3.session_id || "session"}.json`)}>
                  Download Component 3 JSON
                </button>
              </>
            )}
          </section>
        )}
      </section>
    </main>
  );
}
