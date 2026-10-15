import {
  Award,
  BookOpenCheck,
  Compass,
  Crown,
  Flame,
  Footprints,
  Lock,
  LucideIcon,
  Mountain,
  Star,
  Zap,
} from "lucide-react";
import { Badge } from "../types/therapy";

// Each badge gets its own icon and tint; the title is always shown, so colour is never the only cue.
const BADGE_STYLE: Record<string, { icon: LucideIcon; from: string; to: string }> = {
  first_step: { icon: Footprints, from: "#A8DED6", to: "#4FA897" },
  ten_sessions: { icon: Award, from: "#F5B05E", to: "#C9782A" },
  streak_3: { icon: Flame, from: "#F7A072", to: "#D0561F" },
  streak_7: { icon: Zap, from: "#FFD36E", to: "#D79A16" },
  score_90: { icon: Star, from: "#F0C6E6", to: "#C4508F" },
  intermediate: { icon: Mountain, from: "#8EC3F5", to: "#3F87DD" },
  advanced: { icon: Crown, from: "#C9B6F7", to: "#7C5FD6" },
  mastered: { icon: BookOpenCheck, from: "#A8E6B8", to: "#2E9E5B" },
  explorer: { icon: Compass, from: "#9FE3EA", to: "#2B97A6" },
};

const FALLBACK = { icon: Award, from: "#A8DED6", to: "#4FA897" };

function Medal({ badge, size = 56 }: { badge: Badge; size?: number }) {
  const style = BADGE_STYLE[badge.id] ?? FALLBACK;
  const Icon = badge.earned ? style.icon : Lock;
  return (
    <div
      className="relative flex shrink-0 items-center justify-center rounded-2xl"
      style={{
        width: size,
        height: size,
        background: badge.earned
          ? `linear-gradient(145deg, ${style.from}, ${style.to})`
          : "rgba(255,255,255,0.04)",
        boxShadow: badge.earned ? `0 10px 24px -10px ${style.to}` : undefined,
        border: badge.earned ? undefined : "1px dashed rgba(255,255,255,0.12)",
      }}
    >
      <Icon size={size * 0.42} className={badge.earned ? "text-shell" : "text-ink-soft"} strokeWidth={2.2} />
    </div>
  );
}

/** Earned badges first, then locked ones, with a count and progress bar. */
export default function BadgeShowcase({ badges, compact = false }: { badges: Badge[]; compact?: boolean }) {
  const earned = badges.filter((b) => b.earned);
  const locked = badges.filter((b) => !b.earned);
  const ordered = [...earned, ...locked];
  const pct = badges.length ? Math.round((earned.length / badges.length) * 100) : 0;

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <p className="text-sm text-ink">
          <span className="font-display text-xl font-semibold">{earned.length}</span>
          <span className="text-ink-soft"> / {badges.length} earned</span>
        </p>
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-snow/[0.08]">
          <div className="h-full rounded-full bg-gold-400" style={{ width: `${pct}%` }} />
        </div>
      </div>
      <ul
        className={`grid gap-3 ${
          compact ? "grid-cols-3 sm:grid-cols-5 lg:grid-cols-9" : "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
        }`}
      >
        {ordered.map((b) =>
          compact ? (
            <li key={b.id} className="flex flex-col items-center gap-2 text-center" title={b.description}>
              <Medal badge={b} />
              <span className={`text-xs font-medium ${b.earned ? "text-ink" : "text-ink-soft"}`}>{b.title}</span>
            </li>
          ) : (
            <li
              key={b.id}
              className={`flex items-center gap-3 rounded-xl p-3 ${b.earned ? "bg-shell/70" : "bg-shell/40"}`}
            >
              <Medal badge={b} size={48} />
              <div className="min-w-0">
                <p className={`text-sm font-semibold ${b.earned ? "text-ink" : "text-ink-soft"}`}>{b.title}</p>
                <p className="text-xs text-ink-soft">{b.description}</p>
                <p className={`mt-0.5 text-[11px] font-medium ${b.earned ? "text-gold-400" : "text-ink-soft/70"}`}>
                  {b.earned ? "Earned" : "Locked"}
                </p>
              </div>
            </li>
          )
        )}
      </ul>
    </div>
  );
}
