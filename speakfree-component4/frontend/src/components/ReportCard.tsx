import { ArrowDown, ArrowRight, ArrowUp, CalendarDays, Flag, LifeBuoy, Minus, TrendingUp, UserCog } from "lucide-react";
import { LevelEvent, ReportCard as ReportCardData, ReportStatus } from "../types/therapy";

// Traffic light: colour + icon + word, so the status never relies on colour alone.
const LIGHT: Record<ReportStatus, { dot: string; ring: string; text: string; icon: typeof TrendingUp }> = {
  improving: { dot: "bg-teal-600", ring: "border-teal-600/40 bg-teal-600/10", text: "text-teal-600", icon: TrendingUp },
  steady: { dot: "bg-gold-400", ring: "border-gold-400/40 bg-gold-400/10", text: "text-gold-400", icon: Minus },
  needs_support: { dot: "bg-red-600", ring: "border-red-600/40 bg-red-600/10", text: "text-red-700", icon: LifeBuoy },
};

const ORDER: ReportStatus[] = ["improving", "steady", "needs_support"];

/** The first thing on the progress page: one sentence, a traffic light,
 *  this week, and the next step. Readable without any chart. */
export function ReportCard({ card, name }: { card: ReportCardData; name?: string }) {
  const tone = LIGHT[card.status];
  const Icon = tone.icon;
  return (
    <section className="rounded-2xl border border-snow/5 bg-white p-5 sm:p-6" aria-label="Progress report">
      <div className="flex flex-wrap items-start gap-4">
        <div className="flex flex-col gap-1.5 rounded-full bg-shell/70 p-2" aria-hidden="true">
          {ORDER.map((s) => (
            <span key={s} className={`h-4 w-4 rounded-full ${s === card.status ? LIGHT[s].dot : "bg-snow/10"}`} />
          ))}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-ink-soft">
            {name ? `${name}'s progress report` : "Your progress report"}
          </p>
          <span className={`mt-1.5 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-semibold ${tone.ring} ${tone.text}`}>
            <Icon size={15} />
            {card.label}
          </span>
          <p className="mt-3 font-display text-xl font-semibold leading-snug text-ink">{card.headline}</p>
        </div>
      </div>

      <dl className="mt-5 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl bg-shell/60 px-4 py-3">
          <dt className="flex items-center gap-1.5 text-xs font-semibold text-ink-soft">
            <CalendarDays size={14} /> This week
          </dt>
          <dd className="mt-1 text-sm text-ink">{card.this_week}</dd>
        </div>
        <div className="rounded-xl bg-shell/60 px-4 py-3">
          <dt className="flex items-center gap-1.5 text-xs font-semibold text-ink-soft">
            <ArrowRight size={14} /> Next step
          </dt>
          <dd className="mt-1 text-sm text-ink">{card.next_step.replace(/^Next: /, "")}</dd>
        </div>
      </dl>

      {card.reasons.length > 0 && (
        <div className="mt-4 text-sm">
          <p className="text-xs font-semibold text-ink-soft">Why “{card.label.toLowerCase()}”</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-ink">
            {card.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

const EVENT_ICON = { up: ArrowUp, down: ArrowDown, mastered: Flag, therapist: UserCog };

function shortDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

/** "Beginner → Intermediate on 3 Oct after 1 strong Beginner reading", newest first. */
export function LevelTimeline({ history }: { history: LevelEvent[] }) {
  if (history.length === 0) {
    return (
      <p className="text-sm text-ink-soft">
        No level changes yet. One strong attempt at the current level moves you up.
      </p>
    );
  }
  return (
    <ol className="space-y-3">
      {[...history].reverse().map((e) => {
        const Icon = EVENT_ICON[e.direction];
        return (
          <li key={`${e.at}-${e.to}`} className="flex gap-3 text-sm">
            <span
              className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
                e.direction === "down" ? "bg-gold-400/15 text-gold-400" : "bg-teal-600/15 text-teal-600"
              }`}
            >
              <Icon size={14} />
            </span>
            <span>
              <span className="font-medium text-ink">
                {e.from ? `${e.from} → ${e.to}` : e.to} on {shortDate(e.at)}
              </span>
              <span className="block text-xs text-ink-soft">
                {e.reason.charAt(0).toUpperCase() + e.reason.slice(1)}
              </span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
