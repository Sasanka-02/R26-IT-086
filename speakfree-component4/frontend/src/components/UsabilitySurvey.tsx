import { FormEvent, useEffect, useState } from "react";
import { ClipboardList, X } from "lucide-react";
import { api, errorMessage } from "../api/client";

interface SurveyStatus {
  items: string[];
  responded: boolean;
  eligible: boolean;
  invite: boolean;
  sessions: number;
  sessions_needed: number;
}

const SCALE = [
  { value: 1, label: "Strongly disagree" },
  { value: 2, label: "Disagree" },
  { value: 3, label: "Neutral" },
  { value: 4, label: "Agree" },
  { value: 5, label: "Strongly agree" },
];

/** Invitation card + System Usability Scale questionnaire. Shows nothing
 *  until the user is eligible (students: after a few exercises). */
export default function UsabilitySurvey({ refreshKey = 0 }: { refreshKey?: number }) {
  const [status, setStatus] = useState<SurveyStatus | null>(null);
  const [open, setOpen] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [answers, setAnswers] = useState<(number | null)[]>(Array(10).fill(null));
  const [comment, setComment] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ score: number; band: string } | null>(null);

  useEffect(() => {
    let active = true;
    api
      .get("/api/v1/survey/status")
      .then((res) => active && setStatus(res.data))
      .catch(() => active && setStatus(null));
    return () => {
      active = false;
    };
  }, [refreshKey]);

  if (result) {
    return (
      <div className="rounded-2xl border border-teal-200 bg-teal-50 p-5 text-sm text-teal-900" role="status">
        <p className="font-semibold">Thank you — your feedback was saved.</p>
        <p className="mt-1">
          Your usability score: {result.score} / 100 ({result.band}). It helps us evaluate and improve SpeakFree.
        </p>
      </div>
    );
  }

  if (!status?.invite || dismissed) return null;

  const complete = answers.every((a) => a !== null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!complete) return;
    setSaving(true);
    setError(null);
    try {
      const res = await api.post("/api/v1/survey", { answers, comment: comment || null });
      setResult(res.data);
    } catch (err) {
      setError(errorMessage(err, "Couldn't save your answers. Please try again."));
    } finally {
      setSaving(false);
    }
  };

  if (!open) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-gold-400/60 bg-gold-400/10 p-5">
        <div className="flex items-start gap-3">
          <ClipboardList size={20} className="mt-0.5 shrink-0 text-gold-600" />
          <div>
            <p className="font-semibold text-ink">Help us improve SpeakFree</p>
            <p className="text-sm text-ink-soft">10 quick statements about how easy the app is to use — about 2 minutes.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setOpen(true)}
            className="rounded-full bg-teal-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-teal-700"
          >
            Give feedback
          </button>
          <button
            aria-label="Not now"
            onClick={() => setDismissed(true)}
            className="rounded-full p-1.5 text-ink-soft hover:bg-white"
          >
            <X size={16} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4 rounded-2xl border border-teal-100 bg-white p-6">
      <div>
        <h2 className="font-display text-lg font-semibold text-ink">How easy is SpeakFree to use?</h2>
        <p className="text-sm text-ink-soft">
          For each statement, choose how much you agree. There are no right or wrong answers.
        </p>
      </div>
      <ol className="space-y-4">
        {status.items.map((item, i) => (
          <li key={item}>
            <fieldset>
              <legend className="text-sm font-medium text-ink">
                {i + 1}. {item}
              </legend>
              <div className="mt-2 grid grid-cols-5 gap-1.5">
                {SCALE.map((option) => (
                  <label
                    key={option.value}
                    className={`flex cursor-pointer flex-col items-center gap-1 rounded-lg border px-1 py-2 text-center text-[11px] leading-tight transition ${
                      answers[i] === option.value
                        ? "border-teal-600 bg-teal-600 text-white"
                        : "border-teal-100 text-ink-soft hover:border-teal-400"
                    }`}
                  >
                    <input
                      type="radio"
                      name={`sus-${i}`}
                      value={option.value}
                      checked={answers[i] === option.value}
                      onChange={() => setAnswers((prev) => prev.map((a, j) => (j === i ? option.value : a)))}
                      className="sr-only"
                    />
                    <span className="text-sm font-semibold">{option.value}</span>
                    {option.label}
                  </label>
                ))}
              </div>
            </fieldset>
          </li>
        ))}
      </ol>
      <div>
        <label className="text-sm font-medium text-ink">Anything else you'd like to tell us? (optional)</label>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          rows={3}
          maxLength={2000}
          className="mt-1 w-full rounded-lg border border-teal-100 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
        />
      </div>
      {error && <p className="text-sm text-red-700">{error}</p>}
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={!complete || saving}
          className="rounded-full bg-teal-600 px-5 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving ? "Saving..." : "Submit feedback"}
        </button>
        <span className="text-xs text-ink-soft">
          {answers.filter((a) => a !== null).length} of 10 answered
        </span>
        <button type="button" onClick={() => setOpen(false)} className="text-sm text-ink-soft hover:underline">
          Cancel
        </button>
      </div>
    </form>
  );
}
