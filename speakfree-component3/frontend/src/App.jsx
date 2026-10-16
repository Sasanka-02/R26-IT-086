import { useState } from "react";
import "./App.css";
import Component3View from "./Component3View";

const API_URL =
  "http://127.0.0.1:8000/api/v1/component2/analyze";

function App() {
  const [file, setFile] = useState(null);
  const [referenceText, setReferenceText] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Component 3 navigation (severity & risk analysis view)
  const [view, setView] = useState("component2");
  const [sessionId, setSessionId] = useState("");

  const handleFileChange = (event) => {
    const selectedFile =
      event.target.files?.[0] || null;

    setFile(selectedFile);
    setResult(null);
    setError("");
  };

  const handleAnalyze = async () => {
    if (!file) {
      setError("Please select an audio file first.");
      return;
    }

    setLoading(true);
    setResult(null);
    setError("");

    try {
      const formData = new FormData();

      formData.append("file", file);
      formData.append(
        "reference_text",
        referenceText.trim()
      );

      const response = await fetch(
        API_URL,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Speech analysis failed."
        );
      }

      setResult(data);
      setSessionId("sess-" + Date.now());
    } catch (err) {
      console.error(err);

      setError(
        err.message ||
          "Unable to connect to the SpeakFree backend."
      );
    } finally {
      setLoading(false);
    }
  };

  const output =
    result?.component2_output || null;

  const ml =
    output?.ml_prediction || null;

  const asr =
    output?.asr_analysis || null;

  const stuttering =
    output?.stuttering_analysis || null;

  const alignment =
    output?.alignment || null;

  const timing =
    output?.timing_analysis || null;

  const articulation =
    output?.articulation_analysis || null;

  const phonemeAnalysis =
    output?.phoneme_analysis || null;

  const component3 =
    output?.component3_ready_output || null;

  const phonemes =
    phonemeAnalysis?.phonemes || [];

  const irregularities =
    articulation?.irregularities
      ?.irregular_phonemes || [];

  const findings =
    articulation?.findings || [];

  const hasAlignment =
    alignment?.alignment_available === true;

  const riskLevel =
    ml?.risk_level || "unknown";

  const riskScore =
    ml?.dysarthria_risk_score ?? null;

  const fluencyScore =
    stuttering?.fluency?.fluency_score ?? null;

  const analysisMode =
    output?.analysis_mode ===
    "reference_text_alignment"
      ? "Reference-text alignment"
      : "Spontaneous / ASR-assisted";

  // -------------------------------------------------------------------
  // Component 3 view (Multi-Disorder Severity & Risk Analysis)
  // -------------------------------------------------------------------
  if (view === "component3") {
    return (
      <Component3View
        component2Output={output}
        sessionId={sessionId}
        onBack={() => setView("component2")}
      />
    );
  }

  return (
    <div className="app">

      {/* =====================================================
          HEADER
      ===================================================== */}

      <header className="header">

        <div className="header-inner">

          <div className="brand-block">

            <div className="brand-mark">
              SF
            </div>

            <div>
              <h1>SpeakFree</h1>

              <p>
                Component 2 · Alignment &amp;
                Articulation Analytics
              </p>
            </div>

          </div>

          <div className="header-status">
            <span className="header-dot" />
            Research Prototype
          </div>

        </div>

      </header>


      {/* =====================================================
          MAIN
      ===================================================== */}

      <main className="container">

        {/* ===================================================
            HERO
        =================================================== */}

        <section className="hero-card">

          <div className="hero-content">

            <div className="eyebrow">
              SPEECH ANALYSIS MODULE
            </div>

            <h2>
              Speech Articulation &amp; Fluency Analysis
            </h2>

            <p>
              Analyze acoustic characteristics,
              dysarthria risk, speech fluency,
              phoneme timing, and articulation
              indicators from a speech recording.
            </p>

          </div>

          <div className="hero-pipeline">

            <div className="pipeline-step active">
              <span>01</span>
              Acoustic
            </div>

            <div className="pipeline-line" />

            <div className="pipeline-step">
              <span>02</span>
              Fluency
            </div>

            <div className="pipeline-line" />

            <div className="pipeline-step">
              <span>03</span>
              Alignment
            </div>

            <div className="pipeline-line" />

            <div className="pipeline-step">
              <span>04</span>
              Articulation
            </div>

          </div>

        </section>


        {/* ===================================================
            INPUT
        =================================================== */}

        <section className="card input-card">

          <div className="card-heading">

            <div>

              <span className="section-label">
                ANALYSIS INPUT
              </span>

              <h2>
                Upload Speech Recording
              </h2>

              <p>
                Supported formats: WAV, MP3 and M4A.
              </p>

            </div>

            <div className="step-badge">
              Step 1
            </div>

          </div>


          {/* Audio input */}

          <div className="form-group">

            <label htmlFor="audio">
              Speech audio
            </label>

            <input
              id="audio"
              type="file"
              accept=".wav,.mp3,.m4a,audio/wav,audio/mpeg,audio/mp4"
              onChange={handleFileChange}
            />

          </div>


          {/* Reference text */}

          <div className="form-group">

            <label htmlFor="reference">

              Reference text

              <span className="optional">
                {" "}
                (optional)
              </span>

            </label>

            <textarea
              id="reference"
              rows="3"
              value={referenceText}
              onChange={(event) =>
                setReferenceText(
                  event.target.value
                )
              }
              placeholder="Example: stick"
            />

            <div className="field-hint">
              <strong>
                Known-text analysis:
              </strong>{" "}
              Enter the expected word or sentence
              to enable phoneme-level MFA alignment
              and timing analysis.
            </div>

          </div>


          {/* Selected file */}

          {file && (
            <div className="selected-file">

              <div className="file-icon">
                ♪
              </div>

              <div className="file-details">

                <span>
                  Selected audio
                </span>

                <strong>
                  {file.name}
                </strong>

              </div>

            </div>
          )}


          {/* Analysis mode */}

          <div className="mode-info">

            <div className="mode-icon">
              i
            </div>

            <div>

              <strong>
                Analysis mode
              </strong>

              <p>

                {referenceText.trim()
                  ? "Reference-text mode: MFA phoneme alignment will be performed."
                  : "Spontaneous mode: acoustic, dysarthria, and fluency indicators will be analyzed. Phoneme alignment requires a reliable reference text."}

              </p>

            </div>

          </div>


          {/* Analyze button */}

          <button
            type="button"
            className="analyze-button"
            onClick={handleAnalyze}
            disabled={!file || loading}
          >

            {loading ? (
              <>
                <span className="spinner" />
                Analyzing speech...
              </>
            ) : (
              <>
                Analyze Speech
                <span className="button-arrow">
                  →
                </span>
              </>
            )}

          </button>


          {/* Error */}

          {error && (
            <div className="error-box">

              <strong>
                Analysis failed
              </strong>

              <span>
                {error}
              </span>

            </div>
          )}

        </section>


        {/* ===================================================
            RESULTS
        =================================================== */}

        {output && (
          <div className="results-area">

            {/* =================================================
                SUMMARY
            ================================================= */}

            <section className="summary-card">

              <div className="summary-top">

                <div>

                  <span className="section-label light">
                    ANALYSIS COMPLETE
                  </span>

                  <h2>
                    Component 2 Results
                  </h2>

                  <p>
                    {analysisMode}
                  </p>

                </div>

                <div
                  className={`risk-pill ${riskLevel}`}
                >
                  {riskLevel.toUpperCase()}
                </div>

              </div>


              <div className="summary-metrics">

                <div className="summary-metric primary">

                  <span>
                    Dysarthria Risk
                  </span>

                  <strong>
                    {riskScore !== null
                      ? `${riskScore}%`
                      : "N/A"}
                  </strong>

                  <small>
                    Supervised model output
                  </small>

                </div>


                <div className="summary-metric">

                  <span>
                    Fluency Score
                  </span>

                  <strong>
                    {fluencyScore !== null
                      ? `${fluencyScore}/100`
                      : "N/A"}
                  </strong>

                </div>


                <div className="summary-metric">

                  <span>
                    Alignment
                  </span>

                  <strong>
                    {hasAlignment
                      ? "Available"
                      : "Unavailable"}
                  </strong>

                </div>


                <div className="summary-metric">

                  <span>
                    Phonemes
                  </span>

                  <strong>
                    {component3?.phoneme_count ??
                      0}
                  </strong>

                </div>

              </div>

            </section>


            {/* =================================================
                DYSARTHRIA
            ================================================= */}

            <section className="card">

              <div className="card-heading">

                <div>

                  <span className="section-label">
                    DYSARTHRIA ANALYSIS
                  </span>

                  <h2>
                    Dysarthria Risk
                  </h2>

                  <p>
                    Classification output from the
                    trained acoustic-feature model.
                  </p>

                </div>

                <span
                  className={`risk-badge ${riskLevel}`}
                >
                  {riskLevel.toUpperCase()}
                </span>

              </div>


              <div className="metric-grid">

                <div className="metric">

                  <span>
                    Dysarthria Probability
                  </span>

                  <strong>
                    {ml
                      ? `${(
                          ml.dysarthria_probability *
                          100
                        ).toFixed(1)}%`
                      : "N/A"}
                  </strong>

                </div>


                <div className="metric">

                  <span>
                    Healthy Probability
                  </span>

                  <strong>
                    {ml
                      ? `${(
                          ml.healthy_probability *
                          100
                        ).toFixed(1)}%`
                      : "N/A"}
                  </strong>

                </div>


                <div className="metric">

                  <span>
                    Risk Score
                  </span>

                  <strong>
                    {riskScore !== null
                      ? riskScore
                      : "N/A"}
                  </strong>

                </div>


                <div className="metric">

                  <span>
                    Predicted Class
                  </span>

                  <strong>
                    {ml?.predicted_class ||
                      "N/A"}
                  </strong>

                </div>

              </div>

            </section>


            {/* =================================================
                STUTTERING / FLUENCY
            ================================================= */}

            {stuttering && (
              <section className="card fluency-card">

                <div className="card-heading">

                  <div>

                    <span className="section-label">
                      FLUENCY ANALYSIS
                    </span>

                    <h2>
                      Stuttering &amp; Fluency Indicators
                    </h2>

                    <p>
                      Observable speech-fluency
                      characteristics extracted
                      from ASR text and timing.
                    </p>

                  </div>

                  <div className="fluency-score-badge">

                    {fluencyScore !== null
                      ? `${fluencyScore}/100`
                      : "N/A"}

                  </div>

                </div>


                <div className="metric-grid">

                  <div className="metric">

                    <span>
                      Word Repetitions
                    </span>

                    <strong>
                      {
                        stuttering
                          .word_repetitions
                          ?.length ?? 0
                      }
                    </strong>

                  </div>


                  <div className="metric">

                    <span>
                      Phrase Repetitions
                    </span>

                    <strong>
                      {
                        stuttering
                          .phrase_repetitions
                          ?.length ?? 0
                      }
                    </strong>

                  </div>


                  <div className="metric">

                    <span>
                      Fillers / Hesitations
                    </span>

                    <strong>
                      {
                        stuttering
                          .fillers_and_hesitations
                          ?.length ?? 0
                      }
                    </strong>

                  </div>


                  <div className="metric">

                    <span>
                      Speech Rate
                    </span>

                    <strong>
                      {
                        stuttering
                          .speech_rate
                          ?.words_per_minute ??
                        "N/A"
                      }
                      <small className="unit">
                        {" "}
                        WPM
                      </small>
                    </strong>

                  </div>

                </div>


                <div className="timing-summary">

                  <div>

                    <span>
                      Pauses
                    </span>

                    <strong>
                      {
                        stuttering
                          .timing
                          ?.pause_count ??
                        0
                      }
                    </strong>

                  </div>


                  <div>

                    <span>
                      Long pauses
                    </span>

                    <strong>
                      {
                        stuttering
                          .timing
                          ?.long_pause_count ??
                        0
                      }
                    </strong>

                  </div>


                  <div>

                    <span>
                      Mean pause duration
                    </span>

                    <strong>
                      {
                        stuttering
                          .timing
                          ?.mean_pause_duration ??
                        "N/A"
                      }{" "}
                      sec
                    </strong>

                  </div>

                </div>


                <div className="interpretation">

                  <div className="interpretation-title">
                    Fluency interpretation
                  </div>

                  <p>
                    {
                      stuttering
                        .fluency
                        ?.interpretation ||
                      "No fluency interpretation available."
                    }
                  </p>

                </div>


                {/* Repetitions */}

                {stuttering.word_repetitions?.length >
                  0 && (

                  <div className="issues">

                    <h3>
                      Word Repetition Indicators
                    </h3>

                    {stuttering.word_repetitions.map(
                      (item, index) => (

                        <div
                          className="issue"
                          key={`word-${index}`}
                        >

                          <span className="issue-marker">
                            ↻
                          </span>

                          <span>
                            Repeated word:{" "}
                            <strong>
                              {item.word}
                            </strong>
                          </span>

                        </div>

                      )
                    )}

                  </div>

                )}


                {/* Phrase repetitions */}

                {stuttering.phrase_repetitions?.length >
                  0 && (

                  <div className="issues">

                    <h3>
                      Phrase Repetition Indicators
                    </h3>

                    {stuttering.phrase_repetitions.map(
                      (item, index) => (

                        <div
                          className="issue"
                          key={`phrase-${index}`}
                        >

                          <span className="issue-marker">
                            ↻
                          </span>

                          <span>
                            Repeated phrase:{" "}
                            <strong>
                              {item.phrase}
                            </strong>
                          </span>

                        </div>

                      )
                    )}

                  </div>

                )}


                {/* Fillers */}

                {stuttering.fillers_and_hesitations?.length >
                  0 && (

                  <div className="issues">

                    <h3>
                      Filler / Hesitation Indicators
                    </h3>

                    {stuttering.fillers_and_hesitations.map(
                      (item, index) => (

                        <div
                          className="issue"
                          key={`filler-${index}`}
                        >

                          <span className="issue-marker">
                            ~
                          </span>

                          <span>
                            Detected:
                            {" "}
                            <strong>
                              {item.word}
                            </strong>
                          </span>

                        </div>

                      )
                    )}

                  </div>

                )}

              </section>
            )}


            {/* =================================================
                ALIGNMENT
            ================================================= */}

            <section className="card">

              <div className="section-title">

                <div>

                  <span className="section-label">
                    PHONETIC ALIGNMENT
                  </span>

                  <h2>
                    Alignment &amp; Timing
                  </h2>

                </div>

                <span
                  className={`status-badge ${
                    hasAlignment
                      ? "available"
                      : "unavailable"
                  }`}
                >
                  {hasAlignment
                    ? "ALIGNMENT AVAILABLE"
                    : "ALIGNMENT UNAVAILABLE"}
                </span>

              </div>


              {!hasAlignment && (
                <div className="info-box">

                  <div className="info-icon">
                    !
                  </div>

                  <div>

                    <strong>
                      Phoneme alignment was not
                      available.
                    </strong>

                    <p>
                      {alignment?.reason ||
                        "A reliable phoneme alignment could not be produced for this recording."}
                    </p>

                    {!referenceText.trim() && (
                      <p>
                        For a known-text or reading
                        task, enter the exact expected
                        word or sentence in the
                        Reference text field.
                      </p>
                    )}

                  </div>

                </div>
              )}


              {hasAlignment && (
                <>

                  <div className="metric-grid">

                    <div className="metric">

                      <span>
                        Alignment Reliability
                      </span>

                      <strong>
                        {alignment.reliability}
                        <small className="unit">
                          /100
                        </small>
                      </strong>

                    </div>


                    <div className="metric">

                      <span>
                        Alignment Quality
                      </span>

                      <strong>
                        {alignment.quality}
                      </strong>

                    </div>


                    <div className="metric">

                      <span>
                        Phonemes Analyzed
                      </span>

                      <strong>
                        {timing?.phoneme_count ??
                          0}
                      </strong>

                    </div>


                    <div className="metric">

                      <span>
                        Timing Consistency
                      </span>

                      <strong>
                        {timing?.timing_consistency_score ??
                          "N/A"}
                        <small className="unit">
                          /100
                        </small>
                      </strong>

                    </div>

                  </div>


                  <div className="timing-summary">

                    <div>

                      <span>
                        Mean phoneme duration
                      </span>

                      <strong>
                        {
                          timing
                            ?.mean_phoneme_duration ??
                          "N/A"
                        }{" "}
                        sec
                      </strong>

                    </div>


                    <div>

                      <span>
                        Duration variation
                      </span>

                      <strong>
                        {
                          timing
                            ?.duration_variation ??
                          "N/A"
                        }
                      </strong>

                    </div>


                    <div>

                      <span>
                        Duration standard deviation
                      </span>

                      <strong>
                        {
                          timing
                            ?.duration_std ??
                          "N/A"
                        }{" "}
                        sec
                      </strong>

                    </div>

                  </div>

                </>
              )}

            </section>


            {/* =================================================
                PHONEME TABLE
            ================================================= */}

            {phonemes.length > 0 && (

              <section className="card">

                <div className="card-heading">

                  <div>

                    <span className="section-label">
                      PHONEME-LEVEL ANALYSIS
                    </span>

                    <h2>
                      Phoneme Timing
                    </h2>

                    <p>
                      Boundaries extracted from
                      Montreal Forced Aligner.
                    </p>

                  </div>

                  <div className="count-badge">
                    {phonemes.length} phonemes
                  </div>

                </div>


                <div className="table-wrapper">

                  <table>

                    <thead>

                      <tr>

                        <th>
                          Phoneme
                        </th>

                        <th>
                          Start
                        </th>

                        <th>
                          End
                        </th>

                        <th>
                          Duration
                        </th>

                      </tr>

                    </thead>


                    <tbody>

                      {phonemes.map(
                        (phoneme, index) => (

                          <tr
                            key={`${phoneme.phoneme}-${index}`}
                          >

                            <td>
                              <span className="phoneme-chip">
                                {phoneme.phoneme}
                              </span>
                            </td>

                            <td>
                              {Number(
                                phoneme.start
                              ).toFixed(3)}{" "}
                              s
                            </td>

                            <td>
                              {Number(
                                phoneme.end
                              ).toFixed(3)}{" "}
                              s
                            </td>

                            <td>

                              <strong>
                                {Number(
                                  phoneme.duration
                                ).toFixed(3)}{" "}
                                s
                              </strong>

                            </td>

                          </tr>

                        )
                      )}

                    </tbody>

                  </table>

                </div>

              </section>

            )}


            {/* =================================================
                ARTICULATION
            ================================================= */}

            {articulation && (

              <section className="card">

                <div className="card-heading">

                  <div>

                    <span className="section-label">
                      ARTICULATION METRICS
                    </span>

                    <h2>
                      Articulation Analytics
                    </h2>

                    <p>
                      Timing and phoneme consistency
                      indicators derived from the
                      aligned speech.
                    </p>

                  </div>

                </div>


                <div className="metric-grid">

                  <div className="metric highlight">

                    <span>
                      Overall Articulation
                    </span>

                    <strong>
                      {
                        articulation
                          .subscores
                          ?.overall_articulation_indicator ??
                        "N/A"
                      }

                      <small className="unit">
                        /100
                      </small>
                    </strong>

                  </div>


                  <div className="metric">

                    <span>
                      Timing Consistency
                    </span>

                    <strong>
                      {
                        articulation
                          .subscores
                          ?.timing_consistency ??
                        "N/A"
                      }

                      <small className="unit">
                        /100
                      </small>
                    </strong>

                  </div>


                  <div className="metric">

                    <span>
                      Phoneme Consistency
                    </span>

                    <strong>
                      {
                        articulation
                          .subscores
                          ?.phoneme_consistency ??
                        "N/A"
                      }

                      <small className="unit">
                        /100
                      </small>
                    </strong>

                  </div>


                  <div className="metric">

                    <span>
                      Acoustic Model Component
                    </span>

                    <strong>
                      {
                        articulation
                          .subscores
                          ?.acoustic_model_component ??
                        "N/A"
                      }

                      <small className="unit">
                        /100
                      </small>
                    </strong>

                  </div>

                </div>


                <div className="interpretation">

                  <div className="interpretation-title">
                    Interpretation
                  </div>

                  <p>
                    {
                      articulation
                        .subscores
                        ?.interpretation ||
                      "No interpretation available."
                    }
                  </p>

                </div>


                {findings.length > 0 && (

                  <div className="issues">

                    <h3>
                      Detected Patterns
                    </h3>

                    {findings.map(
                      (finding, index) => (

                        <div
                          className="issue"
                          key={index}
                        >

                          <span className="issue-marker">
                            •
                          </span>

                          <span>
                            {finding}
                          </span>

                        </div>

                      )
                    )}

                  </div>

                )}


                {irregularities.length > 0 && (

                  <div className="issues">

                    <h3>
                      Timing Irregularities
                    </h3>

                    {irregularities.map(
                      (item, index) => (

                        <div
                          className="issue"
                          key={`${item.phoneme}-${index}`}
                        >

                          <span className="issue-marker warning">
                            !
                          </span>

                          <span>

                            <strong>
                              {item.phoneme}
                            </strong>

                            {" — "}

                            {item.duration}s

                            {" — "}

                            {item.reason}

                          </span>

                        </div>

                      )
                    )}

                  </div>

                )}

              </section>

            )}


            {/* =================================================
                ASR
            ================================================= */}

            <section className="card">

              <div className="card-heading">

                <div>

                  <span className="section-label">
                    ASR OUTPUT
                  </span>

                  <h2>
                    Speech Recognition
                  </h2>

                </div>

              </div>


              <div className="recognized-text">

                <span className="text-label">
                  Recognized speech
                </span>

                <p>
                  {output.recognized_text ||
                    "No transcription available."}
                </p>

              </div>


              <div className="metric-grid">

                <div className="metric">

                  <span>
                    ASR Confidence
                  </span>

                  <strong>
                    {asr?.asr_confidence_score ??
                      "N/A"}
                  </strong>

                </div>


                <div className="metric">

                  <span>
                    Word Count
                  </span>

                  <strong>
                    {asr?.word_count ??
                      "N/A"}
                  </strong>

                </div>


                <div className="metric">

                  <span>
                    No-speech Probability
                  </span>

                  <strong>
                    {asr
                      ? `${(
                          asr.no_speech_probability *
                          100
                        ).toFixed(1)}%`
                      : "N/A"}
                  </strong>

                </div>


                <div className="metric">

                  <span>
                    Analysis Mode
                  </span>

                  <strong className="small-value">
                    {analysisMode}
                  </strong>

                </div>

              </div>

            </section>


            {/* =================================================
                COMPONENT 3
            ================================================= */}

            <section className="component3-card">

              <div className="component3-header">

                <div>

                  <span className="section-label green">
                    DOWNSTREAM HANDOFF
                  </span>

                  <h2>
                    Component 3 Ready
                  </h2>

                  <p>
                    Component 2 outputs are structured
                    for consumption by the downstream
                    severity-analysis module.
                  </p>

                </div>

                <div className="ready-indicator">
                  ✓ READY
                </div>

              </div>


              <div className="component3-grid">

                <div>

                  <span>
                    Dysarthria Risk
                  </span>

                  <strong>
                    {
                      component3
                        ?.dysarthria_risk_score ??
                      "N/A"
                    }
                  </strong>

                </div>


                <div>

                  <span>
                    Fluency Score
                  </span>

                  <strong>
                    {
                      component3
                        ?.fluency_score ??
                      "N/A"
                    }
                  </strong>

                </div>


                <div>

                  <span>
                    Timing Consistency
                  </span>

                  <strong>
                    {
                      component3
                        ?.timing_consistency ??
                      "N/A"
                    }
                  </strong>

                </div>


                <div>

                  <span>
                    Alignment
                  </span>

                  <strong>
                    {
                      component3?.alignment_uncertain
                        ? "Uncertain"
                        : "Available"
                    }
                  </strong>

                </div>

              </div>

              <button
                type="button"
                className="analyze-button component3-cta"
                onClick={() => setView("component3")}
              >
                View Severity Analysis
                <span className="button-arrow">→</span>
              </button>

              <p className="component3-cta-hint">
                Component 3 · Multi-Disorder Severity Classification &amp;
                Risk Prediction (IT21315114)
              </p>

            </section>


            {/* =================================================
                RESEARCH NOTE
            ================================================= */}

            <div className="research-note">

              <div className="research-note-title">
                Research prototype
              </div>

              <p>
                {output.clinical_note ||
                  "This system is intended for research screening and analysis and is not a clinical diagnosis."}
              </p>

            </div>

          </div>
        )}

      </main>


      {/* =====================================================
          FOOTER
      ===================================================== */}

      <footer className="footer">

        SpeakFree · Component 2

        <span>
          Alignment · Articulation · Fluency Analytics
        </span>

      </footer>

    </div>
  );
}

export default App;