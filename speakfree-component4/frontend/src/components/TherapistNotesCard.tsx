import { useState } from "react";
import { BellRing, CheckCheck, MessageSquareText } from "lucide-react";
import { useTherapistNotes } from "../therapy/useTherapistNotes";

const SHOW_READ = 3;

function when(iso: string) {
  return new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

/** Notes the therapist shared — shown at the top of the student's dashboard,
 *  with new ones highlighted until the student marks them as read. */
export default function TherapistNotesCard() {
  const { notes, unread, markRead } = useTherapistNotes();
  const [showAll, setShowAll] = useState(false);
  if (notes.length === 0) return null;

  const fresh = notes.filter((n) => n.unread);
  const older = notes.filter((n) => !n.unread);
  const visibleOlder = showAll ? older : older.slice(0, Math.max(0, SHOW_READ - fresh.length));

  return (
    <section
      id="notes"
      aria-label="Notes from your therapist"
      className={`scroll-mt-24 rounded-2xl border p-5 ${
        unread ? "border-gold-400/60 bg-gold-400/10" : "border-snow/5 bg-white"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          {unread ? (
            <BellRing size={18} className="text-gold-400" />
          ) : (
            <MessageSquareText size={18} className="text-teal-600" />
          )}
          <h2 className="text-base font-semibold text-ink">
            {unread
              ? `You have ${unread} new note${unread === 1 ? "" : "s"} from your therapist`
              : "Notes from your therapist"}
          </h2>
        </div>
        {unread > 0 && (
          <button
            onClick={markRead}
            className="flex items-center gap-1.5 rounded-full bg-teal-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-teal-700"
          >
            <CheckCheck size={15} />
            Mark as read
          </button>
        )}
      </div>

      <ul className="mt-4 space-y-2">
        {[...fresh, ...visibleOlder].map((n) => (
          <li
            key={n.id}
            className={`rounded-xl px-4 py-3 ${n.unread ? "border border-gold-400/50 bg-white" : "bg-shell/60"}`}
          >
            <div className="flex flex-wrap items-center gap-2 text-xs text-ink-soft">
              {n.unread && (
                <span className="rounded-full bg-gold-400 px-2 py-0.5 text-[11px] font-semibold text-[#1f2937]">New</span>
              )}
              <span className="font-medium text-ink">{n.by_name}</span>
              <span>· {when(n.at)}</span>
            </div>
            <p className="mt-1 whitespace-pre-line text-sm text-ink">{n.text}</p>
          </li>
        ))}
      </ul>

      {older.length > visibleOlder.length && (
        <button onClick={() => setShowAll(true)} className="mt-3 text-sm font-medium text-teal-600 hover:underline">
          Show all {notes.length} notes
        </button>
      )}
    </section>
  );
}
