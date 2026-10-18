/**
 * What the therapist sends the patient: shared clinical notes (new ones highlighted until read)
 * and homework – assigned exercises with a due date and how many attempts are asked for.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BellRing, BookOpenCheck, CheckCheck, CheckCircle2, MessageSquareText, Play } from "lucide-react";
import { api } from "../../api/client";
import type { HomeworkItem, TherapyNote } from "../../types/integration";

const when = (iso: string) => new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export function TherapistNotesCard({ patientId }: { patientId: string }) {
  const [notes, setNotes] = useState<TherapyNote[]>([]);
  const [unread, setUnread] = useState(0);
  const [showAll, setShowAll] = useState(false);
  useEffect(() => {
    api.therapy.notes(patientId).then((d) => { setNotes(d.notes); setUnread(d.unread); }).catch(() => undefined);
  }, [patientId]);
  if (notes.length === 0) return null;
  const fresh = notes.filter((n) => n.unread);
  const older = notes.filter((n) => !n.unread);
  const shownOlder = showAll ? older : older.slice(0, Math.max(0, 3 - fresh.length));
  const markRead = () => api.therapy.readNotes(patientId).then((d) => { setNotes(d.notes); setUnread(d.unread); }).catch(() => undefined);

  return (
    <section aria-label="Notes from your therapist" className={`rounded-2xl border p-5 ${unread ? "border-sun/50 bg-sun-soft" : "card"}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="flex items-center gap-2 font-bold text-ink">
          {unread ? <BellRing size={18} className="text-warn" /> : <MessageSquareText size={18} className="text-navy" />}
          {unread ? `You have ${unread} new note${unread === 1 ? "" : "s"} from your therapist` : "Notes from your therapist"}
        </h2>
        {unread > 0 && <button onClick={() => void markRead()} className="btn-primary py-1.5"><CheckCheck size={15} /> Mark as read</button>}
      </div>
      <ul className="mt-4 space-y-2">
        {[...fresh, ...shownOlder].map((n) => (
          <li key={n.id} className={`rounded-xl px-4 py-3 ${n.unread ? "border border-sun/50 bg-white" : "bg-canvas"}`}>
            <div className="flex flex-wrap items-center gap-2 text-xs muted">
              {n.unread && <span className="chip bg-sun px-2 py-0.5 text-[11px] text-ink">New</span>}
              <span className="font-semibold text-ink">{n.by_name}</span><span>· {when(n.at)}</span>
            </div>
            <p className="mt-1 whitespace-pre-line text-sm text-ink">{n.text}</p>
          </li>
        ))}
      </ul>
      {older.length > shownOlder.length && (
        <button onClick={() => setShowAll(true)} className="mt-3 text-sm font-semibold text-brand hover:underline">Show all {notes.length} notes</button>
      )}
    </section>
  );
}

function dueText(h: HomeworkItem) {
  if (h.done) return "Done ✓";
  if (h.days_left === null) return "No due date";
  if (h.overdue) return `Overdue by ${-h.days_left} day${h.days_left === -1 ? "" : "s"}`;
  if (h.days_left === 0) return "Due today";
  if (h.days_left === 1) return "Due tomorrow";
  return `Due in ${h.days_left} days`;
}

export function HomeworkCard({ homework }: { homework: { items: HomeworkItem[]; open: number; overdue: number } }) {
  if (homework.items.length === 0) return null;
  return (
    <section className={`card p-5 ${homework.overdue ? "border-bad/40" : ""}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-bold text-ink"><BookOpenCheck size={18} className="text-navy" /> Homework from your therapist</h2>
        <span className="text-xs muted">{homework.open === 0 ? "All done – well done!" : `${homework.open} to do${homework.overdue ? ` · ${homework.overdue} overdue` : ""}`}</span>
      </div>
      <ul className="mt-3 space-y-2">
        {homework.items.map((h) => (
          <li key={h.exercise_id} className={`flex flex-wrap items-center gap-3 rounded-xl px-4 py-3 text-sm ${h.done ? "bg-ok-soft" : "bg-canvas"}`}>
            <div className="min-w-0 flex-1">
              <p className="font-semibold text-ink">{h.title}</p>
              <p className={`text-xs ${h.overdue ? "font-semibold text-bad" : h.done ? "text-ok" : "muted"}`}>
                {dueText(h)}{h.due ? ` · ${new Date(`${h.due}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" })}` : ""}
              </p>
            </div>
            <div className="flex items-center gap-1" aria-label={`${h.done_count} of ${h.times} done`}>
              {Array.from({ length: h.times }, (_, i) => <span key={i} className={`h-2.5 w-2.5 rounded-full ${i < h.done_count ? "bg-ok" : "bg-line"}`} />)}
              <span className="ml-1 text-xs tabular-nums muted">{h.done_count}/{h.times}</span>
            </div>
            {h.done ? <CheckCircle2 size={18} className="text-ok" /> : (
              <Link to={`/therapy/exercise/${h.exercise_id}`} className="btn-primary px-3 py-1.5 text-xs"><Play size={12} /> Start</Link>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
