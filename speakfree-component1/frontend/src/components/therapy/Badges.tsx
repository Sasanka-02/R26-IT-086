/** Badges earned by practising – earned first, then locked; the title is always shown (never colour alone). */
import { Award, BookOpenCheck, Compass, Crown, Flame, Footprints, Lock, Mountain, Sparkles, Star, Zap, type LucideIcon } from "lucide-react";
import type { Badge } from "../../types/integration";

const ICON: Record<string, LucideIcon> = {
  first_step: Footprints, ten_sessions: Award, streak_3: Flame, streak_7: Zap, score_90: Star,
  level_up: Mountain, top_level: Crown, explorer: Compass, first_words: Sparkles, word_master: BookOpenCheck,
};

function Medal({ badge, size = 52 }: { badge: Badge; size?: number }) {
  const Icon = badge.earned ? ICON[badge.id] ?? Award : Lock;
  return (
    <div className={`grid shrink-0 place-items-center rounded-2xl ${badge.earned ? "bg-gradient-to-br from-lav-500 to-navy text-white shadow-nav" : "border border-dashed border-line bg-canvas text-ink-muted"}`}
      style={{ width: size, height: size }}>
      <Icon size={size * 0.42} strokeWidth={2.2} />
    </div>
  );
}

export default function BadgeShowcase({ badges, compact = false }: { badges: Badge[]; compact?: boolean }) {
  const earned = badges.filter((b) => b.earned);
  const ordered = [...earned, ...badges.filter((b) => !b.earned)];
  const pct = badges.length ? Math.round((earned.length / badges.length) * 100) : 0;
  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <p className="text-sm text-ink"><span className="text-xl font-extrabold">{earned.length}</span><span className="muted"> / {badges.length} earned</span></p>
        <div className="h-1.5 flex-1 rounded-full bg-[#EEF0F7]"><div className="h-1.5 rounded-full bg-sun" style={{ width: `${pct}%` }} /></div>
      </div>
      <ul className={`grid gap-3 ${compact ? "grid-cols-3 sm:grid-cols-5" : "grid-cols-1 sm:grid-cols-2"}`}>
        {ordered.map((b) => compact ? (
          <li key={b.id} className="flex flex-col items-center gap-2 text-center" title={`${b.description}${b.earned ? "" : " (locked)"}`}>
            <Medal badge={b} />
            <span className={`text-xs font-semibold ${b.earned ? "text-ink" : "text-ink-muted"}`}>{b.title}</span>
          </li>
        ) : (
          <li key={b.id} className={`flex items-center gap-3 rounded-xl p-3 ${b.earned ? "bg-lav-50" : "bg-canvas"}`}>
            <Medal badge={b} size={46} />
            <div className="min-w-0">
              <p className={`text-sm font-bold ${b.earned ? "text-ink" : "text-ink-muted"}`}>{b.title}</p>
              <p className="text-xs muted">{b.description}</p>
              <p className={`mt-0.5 text-[11px] font-semibold ${b.earned ? "text-warn" : "text-ink-muted"}`}>{b.earned ? "Earned" : "Locked"}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** "New badge!" banner shown after an exercise. */
export function NewBadges({ badges }: { badges: Badge[] }) {
  if (!badges.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-sun/40 bg-sun-soft p-3">
      {badges.map((b) => (
        <span key={b.id} className="flex items-center gap-2 text-sm font-semibold text-ink"><Medal badge={b} size={36} /> New badge: {b.title}</span>
      ))}
    </div>
  );
}
