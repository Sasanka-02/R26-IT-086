import { ReactNode } from "react";
import { LucideIcon } from "lucide-react";

/** Dashboard card: dark surface, title row with optional subtitle and action. */
export function Card({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`min-w-0 rounded-2xl border border-snow/5 bg-white p-5 ${className}`}>
      {(title || action) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-base font-semibold text-ink">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-ink-soft">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

const TONES = {
  mint: "text-teal-600 border-teal-600/30",
  gold: "text-gold-400 border-gold-400/30",
  blue: "text-[#6FA8EC] border-[#6FA8EC]/30",
  pink: "text-[#E59BC6] border-[#E59BC6]/30",
};

/** One headline number with an icon and a short caption (like "Total Sales"). */
export function KpiTile({
  icon: Icon,
  value,
  label,
  caption,
  tone = "mint",
}: {
  icon: LucideIcon;
  value: ReactNode;
  label: string;
  caption?: string;
  tone?: keyof typeof TONES;
}) {
  return (
    <div className="rounded-2xl bg-shell/70 p-4">
      <div className={`flex h-10 w-10 items-center justify-center rounded-xl border ${TONES[tone]}`}>
        <Icon size={19} />
      </div>
      <p className="mt-4 font-display text-2xl font-semibold tabular-nums text-ink">{value}</p>
      <p className="mt-0.5 text-sm text-ink">{label}</p>
      {caption && <p className={`mt-1 text-xs ${TONES[tone].split(" ")[0]}`}>{caption}</p>}
    </div>
  );
}

/** Thin progress bar with a recessive track (0–100). */
export function MeterBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-snow/[0.08]">
      <div
        className="h-full rounded-full"
        style={{ width: `${Math.max(2, Math.min(100, value))}%`, backgroundColor: color }}
      />
    </div>
  );
}

/** Score pill: outlined chip with the number, toned by score band. */
export function ScorePill({ score }: { score: number }) {
  const tone =
    score >= 65
      ? "border-teal-600/50 bg-teal-600/10 text-teal-600"
      : score >= 45
      ? "border-gold-400/50 bg-gold-400/10 text-gold-400"
      : "border-red-600/50 bg-red-600/10 text-red-700";
  return (
    <span className={`inline-flex min-w-[3rem] justify-center rounded-md border px-2 py-0.5 text-xs font-semibold tabular-nums ${tone}`}>
      {score}
    </span>
  );
}

export function EmptyChart({ message }: { message: string }) {
  return (
    <div className="flex h-full min-h-[160px] items-center justify-center rounded-xl border border-dashed border-snow/10 px-6 text-center text-sm text-ink-soft">
      {message}
    </div>
  );
}
