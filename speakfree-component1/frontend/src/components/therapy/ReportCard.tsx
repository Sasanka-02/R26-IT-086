/**
 * The first card on the progress page: a traffic light (colour + icon + word, never colour alone),
 * one headline sentence, this week and the next step – readable without any chart.
 */
import { ArrowDown, ArrowRight, ArrowUp, CalendarDays, Flag, LifeBuoy, Minus, Play, TrendingUp, UserCog } from "lucide-react";
import type { Dashboard, LevelEvent, ReportStatus } from "../../types/integration";

const LIGHT: Record<ReportStatus, { dot: string; chip: string; icon: typeof TrendingUp }> = {
  improving: { dot: "bg-ok", chip: "bg-ok-soft text-ok", icon: TrendingUp },
  steady: { dot: "bg-sun", chip: "bg-sun-soft text-warn", icon: Minus },
  needs_support: { dot: "bg-bad", chip: "bg-bad-soft text-bad", icon: LifeBuoy },
};
const ORDER: ReportStatus[] = ["improving", "steady", "needs_support"];

export function ReportCard({ card, name }: { card: Dashboard["report_card"]; name?: string }) {
  const tone = LIGHT[card.status];
  const Icon = tone.icon;
  return (
    <section className="card p-5 sm:p-6" aria-label="Progress report">
      <div className="flex flex-wrap items-start gap-4">
        <div className="flex flex-col gap-1.5 rounded-full bg-canvas p-2" aria-hidden>
          {ORDER.map((s) => <span key={s} className={`h-4 w-4 rounded-full ${s === card.status ? LIGHT[s].dot : "bg-line"}`} />)}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold uppercase tracking-widest text-ink-muted">{name ? `${name}'s progress report` : "Your progress report"}</p>
          <span className={`chip mt-1.5 text-sm ${tone.chip}`}><Icon size={15} /> {card.label}</span>
          <p className="mt-3 text-xl font-bold leading-snug text-ink">{card.headline}</p>
        </div>
      </div>
      <dl className="mt-5 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl bg-canvas px-4 py-3">
          <dt className="flex items-center gap-1.5 text-xs font-bold text-ink-soft"><CalendarDays size={14} /> This week</dt>
          <dd className="mt-1 text-sm text-ink">{card.this_week}</dd>
        </div>
        <div className="rounded-xl bg-lav-50 px-4 py-3">
          <dt className="flex items-center gap-1.5 text-xs font-bold text-ink-soft"><Play size={14} /> Next step</dt>
          <dd className="mt-1 text-sm text-ink">{card.next_step}</dd>
        </div>
      </dl>
      {card.reasons.length > 0 && (
        <div className="mt-4 text-sm">
          <p className="text-xs font-bold text-ink-soft">Why “{card.label.toLowerCase()}”</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-ink">{card.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
        </div>
      )}
    </section>
  );
}

const EVENT_ICON: Record<string, typeof ArrowUp> = { up: ArrowUp, down: ArrowDown, mastered: Flag, therapist: UserCog, start: ArrowRight };

/** "Level 2 → Level 3 on 3 Oct · 2 strong attempts in a row", newest first. */
export function LevelTimeline({ history, empty = "No level changes yet. Two strong attempts in a row move you up." }: {
  history: LevelEvent[]; empty?: string;
}) {
  const moves = history.filter((e) => e.direction !== "start" || history.length === 1);
  if (moves.length === 0) return <p className="text-sm muted">{empty}</p>;
  return (
    <ol className="space-y-3">
      {[...moves].reverse().map((e, i) => {
        const Icon = EVENT_ICON[e.direction] ?? ArrowRight;
        return (
          <li key={`${e.at}-${e.to}-${i}`} className="flex gap-3 text-sm">
            <span className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full ${e.direction === "down" ? "bg-warn-soft text-warn" : "bg-lav-100 text-navy"}`}>
              <Icon size={14} />
            </span>
            <span>
              <span className="font-semibold text-ink">
                {e.from ? `${e.from} → ${e.to}` : e.to}{e.at ? ` on ${new Date(e.at).toLocaleDateString(undefined, { day: "numeric", month: "short" })}` : ""}
              </span>
              <span className="block text-xs muted">{e.reason.charAt(0).toUpperCase() + e.reason.slice(1)}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
