import { ReactNode } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  MoonStar,
  TrendingUp,
} from "lucide-react";
import { StudentStatus, StudentStatusKey } from "../types/therapist";

// Status is always icon + label, never colour alone.
const STATUS_STYLES: Record<StudentStatusKey, { className: string; icon: typeof CheckCircle2 }> = {
  improving: { className: "border-teal-200 bg-teal-50 text-teal-800", icon: TrendingUp },
  on_track: { className: "border-teal-100 bg-paper text-teal-800", icon: CheckCircle2 },
  needs_attention: { className: "border-amber-200 bg-amber-50 text-amber-900", icon: AlertTriangle },
  inactive: { className: "border-teal-100 bg-paper text-ink-soft", icon: MoonStar },
  not_started: { className: "border-dashed border-teal-100 bg-white text-ink-soft", icon: CircleDashed },
};

export function StatusPill({ status }: { status: StudentStatus }) {
  const { className, icon: Icon } = STATUS_STYLES[status.key];
  return (
    <span
      title={status.detail}
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-medium ${className}`}
    >
      <Icon size={12} />
      {status.label}
    </span>
  );
}

export function StatTile({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-2xl border border-teal-100 bg-white p-4">
      <p className="text-xs font-medium text-ink-soft">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-ink">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-ink-soft">{hint}</p>}
    </div>
  );
}

export function Panel({
  title,
  subtitle,
  children,
  action,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-teal-100 bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-ink">{title}</h2>
          {subtitle && <p className="mt-0.5 text-sm text-ink-soft">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function formatDate(iso: string | null, withTime = false) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  });
}

export function formatRelative(iso: string | null) {
  if (!iso) return "Never";
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  return days === 1 ? "Yesterday" : `${days} days ago`;
}
