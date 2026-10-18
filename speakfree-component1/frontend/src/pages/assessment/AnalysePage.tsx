/**
 * Step 4 – Analyse.
 * "Analyse Now" sends each recording to POST /api/v1/analyze (one at a time, with live progress),
 * then calls POST /api/v1/sessions/{id}/finalize to build the session-level Component 1 output,
 * and opens the results dashboard.
 */
import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowLeft, CheckCircle2, Circle, Loader2, Mic, RotateCcw, Sparkles } from "lucide-react";
import { api, localAudio } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useAssessment } from "../../context/AssessmentContext";
import { fmtTime } from "../../components/Recorder";
import { ErrorBox, Spinner } from "../../components/ui";
import { AssessmentStepper } from "./TaskPages";

type ItemStatus = "waiting" | "analysing" | "done" | "error";

// Plain language for patients (technical detail lives in the admin dashboards).
const STAGES = [
  "Cleaning up background noise",
  "Finding where you spoke and paused",
  "Listening to your words",
  "Checking how clearly each word came through",
  "Measuring your speed, pauses and voice",
];

export default function AnalysePage() {
  const { activePatient } = useAuth();
  const { taskSet, taskError, session, required, allRecorded, markAnalysed, resetSession } = useAssessment();
  const navigate = useNavigate();
  const location = useLocation();
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<Record<string, ItemStatus>>({});
  const [itemErrors, setItemErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [phase, setPhase] = useState<"idle" | "recordings" | "finalizing">("idle");
  const [stage, setStage] = useState(0);
  const [etaSec, setEtaSec] = useState<number | null>(null); // time left, from the recordings analysed so far
  const autostarted = useRef(false);

  // cycle the pipeline stage label while a recording is being analysed (purely informative)
  useEffect(() => {
    if (phase !== "recordings") return;
    const t = window.setInterval(() => setStage((s) => (s + 1) % STAGES.length), 2200);
    return () => window.clearInterval(t);
  }, [phase]);

  async function analyseAll() {
    if (!activePatient || !taskSet || !session || running) return;
    setRunning(true);
    setError(null);
    setItemErrors({});
    setPhase("recordings");
    const sessionId = session.sessionId;
    let failed = 0;
    let left = required.filter((r) => session.recordings[r.key] && !session.recordings[r.key].analysisId).length;
    const took: number[] = [];
    setEtaSec(null);

    for (const item of required) {
      const rec = session.recordings[item.key];
      if (!rec) continue;
      if (rec.analysisId) {
        setStatus((s) => ({ ...s, [item.key]: "done" }));
        continue;
      }
      setStatus((s) => ({ ...s, [item.key]: "analysing" }));
      setStage(0);
      const t0 = performance.now();
      try {
        const res = await api.analyze({
          audio: rec.blob, filename: rec.filename, sessionId, patientId: activePatient.id,
          ageBracket: taskSet.age_bracket.id, taskType: rec.taskType, taskId: rec.taskId,
        });
        localAudio.set(res.analysis_id, rec.blob);
        markAnalysed(item.key, res.analysis_id);
        setStatus((s) => ({ ...s, [item.key]: "done" }));
        took.push((performance.now() - t0) / 1000);
        left -= 1;
        // the first recording includes loading the speech model, so later ones are timed when available
        const typical = took.length > 1 ? took.slice(1).reduce((a, b) => a + b, 0) / (took.length - 1) : took[0];
        setEtaSec(Math.round(typical * left));
      } catch (e) {
        failed += 1;
        setStatus((s) => ({ ...s, [item.key]: "error" }));
        setItemErrors((m) => ({ ...m, [item.key]: (e as Error).message }));
      }
    }

    if (failed) {
      setPhase("idle");
      setRunning(false);
      setError(`${failed} recording${failed === 1 ? "" : "s"} could not be analysed. Re-record ${failed === 1 ? "it" : "them"} (or retry), then press Analyse Now again.`);
      return;
    }

    setPhase("finalizing");
    try {
      await api.finalizeSession(sessionId, activePatient.id);
      navigate(`/sessions/${sessionId}`, { replace: true });
      resetSession();
    } catch (e) {
      setError((e as Error).message);
      setPhase("idle");
      setRunning(false);
    }
  }

  // "Analyse Now" on the overview page navigates here with autostart
  useEffect(() => {
    const auto = (location.state as { autostart?: boolean } | null)?.autostart;
    if (auto && allRecorded && !autostarted.current && session) {
      autostarted.current = true;
      void analyseAll();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allRecorded, session?.sessionId]);

  if (!activePatient) return <div className="card p-8 text-center muted">No patient selected.</div>;
  if (taskError) return <ErrorBox message={taskError} />;
  if (!taskSet || !session) return <Spinner />;

  const done = required.filter((r) => status[r.key] === "done" || session.recordings[r.key]?.analysisId).length;
  const progress = required.length ? (done / required.length) * 100 : 0;
  const recordedCount = required.filter((r) => session.recordings[r.key]).length;

  return (
    <div className="space-y-6">
      <div>
        <Link to="/assessment" className="mb-2 inline-flex items-center gap-1 text-xs font-medium text-ink-muted hover:text-ink"><ArrowLeft size={14} /> All tasks</Link>
        <h1 className="text-[28px] font-extrabold tracking-tight">Assessment Tasks</h1>
      </div>
      <AssessmentStepper />

      <section className="card p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-bold">Review &amp; Analyse</h2>
            <p className="text-sm text-ink-soft">
              {running
                ? "Listening to your recordings. Please keep this page open – you can relax while we work."
                : allRecorded
                  ? "Every task is recorded. Press Analyse Now and we'll prepare your results."
                  : `${recordedCount} of ${required.length} recordings captured. Record the remaining tasks before analysing.`}
            </p>
          </div>
          <button className="btn-primary px-6 py-3 text-[15px]" disabled={!allRecorded || running} onClick={() => void analyseAll()}>
            {running ? <Loader2 className="animate-spin" size={17} /> : error ? <RotateCcw size={17} /> : <Sparkles size={17} />}
            {running ? "Analysing…" : error ? "Retry Analysis" : "Analyse Now"}
          </button>
        </div>

        {(running || done > 0) && (
          <div className="mt-5">
            <div className="mb-1.5 flex justify-between text-xs font-medium text-ink-soft">
              <span>{phase === "finalizing" ? "Putting your results together…" : phase === "recordings" ? STAGES[stage] : "Progress"}</span>
              <span>
                {done} / {required.length} analysed
                {phase === "recordings" && (etaSec === null
                  ? " · the first one takes a little longer"
                  : ` · about ${etaSec < 60 ? `${Math.max(5, etaSec)} seconds` : `${Math.ceil(etaSec / 60)} minute${etaSec > 60 ? "s" : ""}`} left`)}
              </span>
            </div>
            <div className="h-2.5 rounded-full bg-lav-100">
              <div className="h-2.5 rounded-full bg-gradient-to-r from-navy to-lav-500 transition-all duration-500" style={{ width: `${phase === "finalizing" ? 100 : progress}%` }} />
            </div>
          </div>
        )}

        {error && <div className="mt-4"><ErrorBox message={error} /></div>}

        <ul className="mt-5 divide-y divide-line rounded-xl border border-line">
          {required.map((item) => {
            const rec = session.recordings[item.key];
            const st: ItemStatus = status[item.key] ?? (rec?.analysisId ? "done" : "waiting");
            const to = item.taskType === "questions" ? "/assessment/questions" : `/assessment/${item.taskType}`;
            return (
              <li key={item.key} className="flex flex-wrap items-center gap-3 px-4 py-3">
                {st === "done" ? <CheckCircle2 size={20} className="text-ok" />
                  : st === "analysing" ? <Loader2 size={20} className="animate-spin text-brand" />
                  : st === "error" ? <AlertTriangle size={20} className="text-bad" />
                  : rec ? <Mic size={20} className="text-lav-500" /> : <Circle size={20} className="text-line" />}
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-semibold">{item.label}</div>
                  <div className="text-xs muted">
                    {!rec ? "Not recorded yet"
                      : st === "analysing" ? "Analysing…"
                      : st === "done" ? "Analysed"
                      : st === "error" ? itemErrors[item.key]
                      : `Recorded · ${rec.durationSec ? fmtTime(rec.durationSec) : "uploaded file"}`}
                  </div>
                </div>
                {(!rec || st === "error") && !running && <Link to={to} className="btn-ghost px-3 py-1.5 text-xs">{rec ? "Re-record" : "Record"}</Link>}
              </li>
            );
          })}
        </ul>
        <p className="mt-4 text-xs muted">
          The first analysis may take longer while the speech model starts. Each recording is deleted from the server right after it is analysed.
        </p>
      </section>
    </div>
  );
}
