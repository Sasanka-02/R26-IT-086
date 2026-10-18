/**
 * System Usability Scale (SUS) – offered after a few exercises (and to therapists on the evidence page).
 * 10 statements on a 1–5 agreement scale; the backend computes the 0–100 score.
 */
import { useEffect, useState } from "react";
import { ClipboardCheck, Loader2, X } from "lucide-react";
import { api } from "../../api/client";
import { ErrorBox } from "../ui";
import type { SurveyStatus } from "../../types/integration";

const SCALE = ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"];
const HIDE_KEY = "speakfree.survey.later";

export default function UsabilitySurvey({ force = false }: { force?: boolean }) {
  const [status, setStatus] = useState<SurveyStatus | null>(null);
  const [open, setOpen] = useState(false);
  const [answers, setAnswers] = useState<(number | null)[]>(Array(10).fill(null));
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ score: number; band: string } | null>(null);
  const [later, setLater] = useState(() => { try { return sessionStorage.getItem(HIDE_KEY) === "1"; } catch { return false; } });

  useEffect(() => { api.survey.status().then(setStatus).catch(() => undefined); }, []);
  if (!status) return null;
  if (!force && (!status.invite || later) && !result) return null;

  async function submit() {
    if (answers.some((a) => a === null)) return setError("Please answer all 10 statements.");
    setBusy(true);
    setError(null);
    try {
      setResult(await api.survey.submit(answers as number[], comment || undefined));
      setOpen(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return <div className="rounded-2xl border border-ok/30 bg-ok-soft p-4 text-sm text-ink"><b>Thank you!</b> Your usability score: {result.score} ({result.band}).</div>;
  }
  if (!open) {
    return (
      <div className="flex flex-col gap-3 rounded-2xl border border-lav-200 bg-lav-50 p-4 sm:flex-row sm:items-center">
        <ClipboardCheck className="shrink-0 text-lav-600" />
        <p className="flex-1 text-sm text-ink">
          {status.responded ? `You rated SpeakFree ${status.score} (${status.band}). You can answer again.` : <><b>Help us improve SpeakFree.</b> Ten quick statements – about two minutes.</>}
        </p>
        <div className="flex gap-2">
          <button className="btn-primary" onClick={() => setOpen(true)}>{status.responded ? "Answer again" : "Take the survey"}</button>
          {!force && <button className="btn-ghost" onClick={() => { setLater(true); try { sessionStorage.setItem(HIDE_KEY, "1"); } catch { /* ignore */ } }}>Later</button>}
        </div>
      </div>
    );
  }
  return (
    <section className="card p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="flex items-center gap-2 font-bold"><ClipboardCheck size={18} className="text-navy" /> Usability survey (SUS)</h2>
        <button onClick={() => setOpen(false)} className="text-ink-muted" aria-label="Close"><X size={18} /></button>
      </div>
      <ol className="space-y-3">
        {status.items.map((item, i) => (
          <li key={item} className="rounded-xl bg-canvas p-3">
            <p className="text-sm font-medium text-ink">{i + 1}. {item}</p>
            <div className="mt-2 grid grid-cols-5 gap-1.5" role="radiogroup" aria-label={item}>
              {SCALE.map((label, v) => (
                <button key={label} type="button" role="radio" aria-checked={answers[i] === v + 1}
                  onClick={() => setAnswers((a) => a.map((x, j) => (j === i ? v + 1 : x)))}
                  className={`rounded-lg border px-1 py-1.5 text-[11px] font-semibold transition ${answers[i] === v + 1 ? "border-navy bg-navy text-white" : "border-line bg-white text-ink-soft hover:border-navy"}`}>
                  {v + 1}<span className="hidden sm:block">{label}</span>
                </button>
              ))}
            </div>
          </li>
        ))}
      </ol>
      <label className="mt-3 block"><span className="label">Anything else? (optional)</span>
        <textarea className="input" rows={2} maxLength={1000} value={comment} onChange={(e) => setComment(e.target.value)} />
      </label>
      <div className="mt-3"><ErrorBox message={error} /></div>
      <button className="btn-primary mt-3" disabled={busy} onClick={() => void submit()}>{busy && <Loader2 className="animate-spin" size={16} />} Submit</button>
    </section>
  );
}
