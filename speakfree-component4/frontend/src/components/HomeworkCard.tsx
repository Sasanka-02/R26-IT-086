import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BookOpenCheck, CalendarClock, CheckCircle2, Play } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { usePracticeHistory } from "../context/PracticeHistoryContext";
import { Appointment, HomeworkResponse } from "../types/therapy";
import { getHomework, getStudentAppointments } from "../therapy/therapyApi";

function dueText(days: number | null, done: boolean, overdue: boolean) {
  if (done) return "Done ✓";
  if (days === null) return "No due date";
  if (overdue) return `Overdue by ${-days} day${days === -1 ? "" : "s"}`;
  if (days === 0) return "Due today";
  if (days === 1) return "Due tomorrow";
  return `Due in ${days} days`;
}

/** Student dashboard: homework from the therapist, and the next booked session. */
export default function HomeworkCard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { version } = usePracticeHistory();
  const [homework, setHomework] = useState<HomeworkResponse | null>(null);
  const [next, setNext] = useState<Appointment | null>(null);

  useEffect(() => {
    if (!user) return;
    getHomework(user.email).then(setHomework).catch(() => {});
    getStudentAppointments()
      .then((d) => setNext(d.booked[0] ?? null))
      .catch(() => {});
  }, [user, version]);

  if ((!homework || homework.items.length === 0) && !next) return null;

  return (
    <section className="grid gap-4 lg:grid-cols-3">
      {homework && homework.items.length > 0 && (
        <div className={`rounded-2xl border p-5 lg:col-span-2 ${homework.overdue ? "border-red-600/40" : "border-snow/5"} bg-white`}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 text-base font-semibold text-ink">
              <BookOpenCheck size={18} className="text-teal-600" />
              Homework from your therapist
            </h2>
            <span className="text-xs text-ink-soft">
              {homework.open === 0 ? "All done — well done!" : `${homework.open} to do${homework.overdue ? ` · ${homework.overdue} overdue` : ""}`}
            </span>
          </div>
          <ul className="mt-3 space-y-2">
            {homework.items.map((h) => (
              <li key={h.exercise_id} className={`flex flex-wrap items-center gap-3 rounded-xl px-4 py-3 text-sm ${h.done ? "bg-teal-50/60" : "bg-shell/60"}`}>
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-ink">{h.title}</p>
                  <p className="text-xs text-ink-soft">
                    <span className={h.overdue ? "font-semibold text-red-700" : h.done ? "text-teal-700" : ""}>
                      {dueText(h.days_left, h.done, h.overdue)}
                    </span>
                    {h.due ? ` · ${new Date(h.due).toLocaleDateString(undefined, { day: "numeric", month: "short" })}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-1" aria-label={`${h.done_count} of ${h.times} done`}>
                  {Array.from({ length: h.times }, (_, i) => (
                    <span key={i} className={`h-2.5 w-2.5 rounded-full ${i < h.done_count ? "bg-teal-600" : "bg-snow/15"}`} />
                  ))}
                  <span className="ml-1 text-xs tabular-nums text-ink-soft">
                    {h.done_count}/{h.times}
                  </span>
                </div>
                {h.done ? (
                  <CheckCircle2 size={18} className="text-teal-600" />
                ) : (
                  <button
                    onClick={() => navigate(`/therapy?tab=practice&start=${encodeURIComponent(h.exercise_id)}`)}
                    className="flex items-center gap-1 rounded-full bg-teal-600 px-3 py-1 text-xs font-medium text-white hover:bg-teal-700"
                  >
                    <Play size={12} /> Start
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      {next && (
        <div className="rounded-2xl border border-snow/5 bg-white p-5">
          <h2 className="flex items-center gap-2 text-base font-semibold text-ink">
            <CalendarClock size={18} className="text-teal-600" />
            Next session
          </h2>
          <p className="mt-3 font-display text-lg font-semibold text-ink">
            {new Date(next.start).toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "short" })}
          </p>
          <p className="text-sm text-ink-soft">
            {new Date(next.start).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })} · {next.minutes} min ·{" "}
            {next.mode === "online" ? "Online" : "At the clinic"} · {next.therapist_name}
          </p>
          <button onClick={() => navigate("/appointments")} className="mt-3 text-sm font-medium text-teal-600 hover:underline">
            Manage appointments →
          </button>
        </div>
      )}
    </section>
  );
}
