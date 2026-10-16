import { FormEvent, useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { getUserExercises, submitScreening } from "../therapy/therapyApi";
import { errorMessage } from "../api/client";
import { GoalProgress, ReadingLevel, SeverityLevel, TherapyExercise } from "../types/therapy";
import { GoalMetric, TherapistSettings } from "../types/therapist";
import { addGoal, addNote, removeGoal, setAssignedExercises, setLevelOverride } from "./therapistApi";
import { formatDate, Panel } from "./ui";

const GOAL_OPTIONS: { metric: GoalMetric; label: string; suggested: string; min: number; max: number }[] = [
  { metric: "average_score", label: "Average score (last 7 days) at least", suggested: "70", min: 0, max: 100 },
  { metric: "sessions_per_week", label: "Exercises in the last 7 days at least", suggested: "4", min: 1, max: 50 },
  { metric: "long_pauses_per_reading", label: "Long pauses per reading at most", suggested: "1", min: 0, max: 20 },
];

const LEVEL_OPTIONS: { value: ReadingLevel | ""; label: string }[] = [
  { value: "", label: "Automatic (adaptive engine)" },
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced (final stage)" },
];

interface Props {
  email: string;
  settings: TherapistSettings;
  goals: GoalProgress[];
  onChanged: () => void;
}

/** The therapist steers the adaptive system: assignments, level, goals and notes. */
export default function StudentControls({ email, settings, goals, onChanged }: Props) {
  const [exercises, setExercises] = useState<TherapyExercise[]>([]);
  const [assigned, setAssigned] = useState<string[]>(settings.assigned.map((a) => a.exercise_id));
  const [level, setLevel] = useState<ReadingLevel | "">(settings.level_override?.level ?? "");
  const [goalMetric, setGoalMetric] = useState<GoalMetric>("average_score");
  const [goalTarget, setGoalTarget] = useState(GOAL_OPTIONS[0].suggested);
  const [goalError, setGoalError] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [notePrivate, setNotePrivate] = useState(false);
  const [severity, setSeverity] = useState<SeverityLevel>(settings.screening?.severity ?? "moderate");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    getUserExercises(email).then((d) => setExercises(d.exercises)).catch(() => setExercises([]));
  }, [email]);

  const run = async (action: () => Promise<unknown>, success: string) => {
    setBusy(true);
    setMessage(null);
    try {
      await action();
      setMessage({ ok: true, text: success });
      onChanged();
    } catch (err) {
      setMessage({ ok: false, text: errorMessage(err, "That didn't save. Please try again.") });
    } finally {
      setBusy(false);
    }
  };

  const toggle = (id: string) =>
    setAssigned((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const chooseGoalMetric = (metric: GoalMetric) => {
    setGoalMetric(metric);
    setGoalTarget(GOAL_OPTIONS.find((o) => o.metric === metric)!.suggested);
    setGoalError(null);
  };

  const submitGoal = (e: FormEvent) => {
    e.preventDefault();
    const option = GOAL_OPTIONS.find((o) => o.metric === goalMetric)!;
    const target = Number(goalTarget);
    if (goalTarget.trim() === "" || Number.isNaN(target)) {
      setGoalError("Enter a target number for this goal.");
      return;
    }
    if (target < option.min || target > option.max) {
      setGoalError(`The target must be between ${option.min} and ${option.max}.`);
      return;
    }
    setGoalError(null);
    run(() => addGoal(email, goalMetric, target), "Goal added.");
  };

  const submitNote = (e: FormEvent) => {
    e.preventDefault();
    if (!note.trim()) return;
    run(
      () => addNote(email, note, !notePrivate),
      notePrivate ? "Private note saved." : "Note saved — the student will see it on their dashboard."
    ).then(() => {
      setNote("");
      setNotePrivate(false);
    });
  };

  return (
    <Panel
      title="Therapist controls"
      subtitle="Your choices feed straight into the student's adaptive plan and assistant."
    >
      {message && (
        <p
          role="status"
          className={`mb-4 rounded-lg px-3 py-2 text-sm ${
            message.ok ? "bg-teal-50 text-teal-800" : "bg-red-50 text-red-700"
          }`}
        >
          {message.text}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">Assign exercises</h3>
          <p className="text-xs text-ink-soft">Assigned exercises appear first in the student's plan.</p>
          <ul className="mt-2 max-h-56 space-y-1 overflow-y-auto pr-1">
            {exercises.map((ex) => (
              <li key={ex.id}>
                <label className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1 text-sm hover:bg-teal-50/60">
                  <input
                    type="checkbox"
                    checked={assigned.includes(ex.id)}
                    onChange={() => toggle(ex.id)}
                    className="accent-teal-600"
                  />
                  {ex.title}
                </label>
              </li>
            ))}
          </ul>
          <button
            disabled={busy}
            onClick={() => run(() => setAssignedExercises(email, assigned), "Assignments saved.")}
            className="mt-2 rounded-full bg-teal-600 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            Save assignments
          </button>
        </div>

        <div className="space-y-5">
          <div>
            <h3 className="text-sm font-semibold text-ink">Reading level</h3>
            <p className="text-xs text-ink-soft">
              Override the adaptive level. The engine continues from your choice.
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              <select
                value={level}
                onChange={(e) => setLevel(e.target.value as ReadingLevel | "")}
                className="rounded-lg border border-teal-100 bg-white px-3 py-1.5 text-sm"
              >
                {LEVEL_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              <button
                disabled={busy}
                onClick={() => run(() => setLevelOverride(email, level || null), "Reading level updated.")}
                className="rounded-full bg-teal-600 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              >
                Apply
              </button>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-ink">Screening result</h3>
            <p className="text-xs text-ink-soft">
              {settings.screening
                ? `Current: ${settings.screening.severity} (${settings.screening.source}, ${formatDate(settings.screening.at)}).`
                : "Normally sent by the screening component."}{" "}
              Sets the starting level (severe/moderate → Beginner, mild → Intermediate) until the first reading, and
              steers the plan towards suitable exercises.
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value as SeverityLevel)}
                className="rounded-lg border border-teal-100 bg-white px-3 py-1.5 text-sm"
              >
                {(["mild", "moderate", "severe", "unknown"] as const).map((s) => (
                  <option key={s} value={s}>
                    {s.charAt(0).toUpperCase() + s.slice(1)}
                  </option>
                ))}
              </select>
              <button
                disabled={busy}
                onClick={() =>
                  run(() => submitScreening(email, severity, "Entered by therapist"), "Screening result saved.")
                }
                className="rounded-full bg-teal-600 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              >
                Save
              </button>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-ink">Goals</h3>
            <ul className="mt-2 space-y-1">
              {goals.map((g) => (
                <li key={g.id} className="flex items-center justify-between gap-2 rounded-lg bg-paper px-3 py-1.5 text-sm">
                  <span className={g.met ? "text-teal-800" : "text-ink"}>
                    {g.met ? "✓" : "○"} {g.text} <span className="text-ink-soft">(now {g.current ?? "—"})</span>
                  </span>
                  <button
                    aria-label="Remove goal"
                    onClick={() => run(() => removeGoal(email, g.id), "Goal removed.")}
                    className="text-ink-soft hover:text-red-700"
                  >
                    <Trash2 size={14} />
                  </button>
                </li>
              ))}
              {goals.length === 0 && <li className="text-xs text-ink-soft">No goals yet.</li>}
            </ul>
            <form onSubmit={submitGoal} className="mt-2 flex flex-wrap gap-2">
              <select
                value={goalMetric}
                onChange={(e) => chooseGoalMetric(e.target.value as GoalMetric)}
                className="rounded-lg border border-teal-100 bg-white px-2 py-1.5 text-sm"
              >
                {GOAL_OPTIONS.map((o) => (
                  <option key={o.metric} value={o.metric}>
                    {o.label}
                  </option>
                ))}
              </select>
              <input
                type="number"
                step="any"
                value={goalTarget}
                onChange={(e) => {
                  setGoalTarget(e.target.value);
                  setGoalError(null);
                }}
                aria-label="Goal target"
                className="w-20 rounded-lg border border-teal-100 px-2 py-1.5 text-sm"
              />
              <button
                type="submit"
                disabled={busy}
                className="rounded-full bg-teal-600 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              >
                Add goal
              </button>
            </form>
            {goalError && (
              <p className="mt-1 text-xs text-red-700" role="alert">
                {goalError}
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-semibold text-ink">Clinical notes</h3>
        <p className="text-xs text-ink-soft">
          Notes are shown to the student on their dashboard with a notification, unless you mark them private.
        </p>
        <form onSubmit={submitNote} className="mt-2 flex flex-wrap gap-2">
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. Blocks mostly on plosives (p, b, t). Practise soft onsets."
            className="min-w-[14rem] flex-1 rounded-lg border border-teal-100 px-3 py-1.5 text-sm"
          />
          <button disabled={busy} className="rounded-full bg-teal-600 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50">
            {notePrivate ? "Save private note" : "Save & notify student"}
          </button>
          <label className="flex w-full items-center gap-2 text-xs text-ink-soft">
            <input
              type="checkbox"
              checked={notePrivate}
              onChange={(e) => setNotePrivate(e.target.checked)}
              className="accent-teal-600"
            />
            Only for therapists (don't show to the student)
          </label>
        </form>
        <ul className="mt-3 space-y-2">
          {settings.notes.map((n) => (
            <li key={n.id} className="rounded-lg bg-paper px-3 py-2 text-sm">
              <p className="text-ink">{n.text}</p>
              <p className="text-xs text-ink-soft">
                {formatDate(n.at, true)} · {n.by} ·{" "}
                {n.shared ? (
                  <span className="text-teal-700">Shared with student</span>
                ) : (
                  <span>Private (therapists only)</span>
                )}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </Panel>
  );
}
