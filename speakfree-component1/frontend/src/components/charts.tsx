/**
 * Small, dependency-free chart primitives for the admin dashboards (inline SVG / HTML).
 * Conventions: thin marks with rounded data-ends, recessive grid, direct labels in text ink
 * (never in the series colour), hover tooltips, and a fixed categorical order.
 *
 * Disorder palette (validated for colour-vision deficiency, light surface):
 *   normal #1D4ED8 · stuttering #F59E0B · dysarthria #7C6CF0 · articulation #0E9F8E
 * Amber is < 3:1 on white, so every bar carries a visible text label.
 */
import { useState, type ReactNode } from "react";
import { COLORS, SEVERITY_COLORS } from "./ui";

export const DISORDER_ORDER = ["normal", "stuttering", "dysarthria", "articulation"] as const;
export const DISORDER_COLOR: Record<string, string> = {
  normal: "#1D4ED8",
  stuttering: "#F59E0B",
  dysarthria: "#7C6CF0",
  articulation: "#0E9F8E",
};
export const DISORDER_LABEL: Record<string, string> = {
  normal: "Typical (normal)",
  stuttering: "Stuttering",
  dysarthria: "Dysarthria",
  articulation: "Articulation",
};
export const FOCUS_LABEL: Record<string, string> = {
  fluency: "Fluency therapy",
  motor_speech: "Motor-speech therapy",
  speech_sounds: "Articulation therapy",
  maintenance: "Maintenance",
};
export const SEVERITY_NAME = ["", "Normal", "Mild", "Moderate", "Severe"];
export const severityColor = (level: number) => SEVERITY_COLORS[Math.max(1, Math.min(4, level)) - 1];

// --------------------------------------------------------------------------- stat tile
export function StatTile({ label, value, sub, icon }: { label: string; value: ReactNode; sub?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between text-sm font-semibold text-ink-soft">{label}{icon && <span className="text-navy">{icon}</span>}</div>
      <div className="mt-1 text-[28px] font-extrabold leading-tight text-ink">{value}</div>
      {sub && <div className="text-xs muted">{sub}</div>}
    </div>
  );
}

// --------------------------------------------------------------------------- horizontal bars
export interface BarDatum { key: string; label: string; value: number; color?: string; note?: string; highlight?: boolean }

/** Labelled horizontal bars (probabilities, counts). `max` defaults to the largest value (or 1 for probabilities). */
export function HBars({ data, max, format = (v) => v.toFixed(2), empty = "No data" }: {
  data: BarDatum[]; max?: number; format?: (v: number) => string; empty?: string;
}) {
  if (!data.length) return <p className="text-sm muted">{empty}</p>;
  const top = max ?? Math.max(...data.map((d) => d.value), 1e-9);
  return (
    <ul className="space-y-2.5">
      {data.map((d) => (
        <li key={d.key} title={`${d.label}: ${format(d.value)}${d.note ? ` – ${d.note}` : ""}`}>
          <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
            <span className={`flex items-center gap-2 ${d.highlight ? "font-bold text-ink" : "text-ink-soft"}`}>
              <span className="h-2.5 w-2.5 rounded-sm" style={{ background: d.color ?? COLORS.navy }} aria-hidden />
              {d.label}
            </span>
            <span className="font-mono text-xs font-semibold text-ink">{format(d.value)}</span>
          </div>
          <div className="h-2.5 w-full rounded-full bg-[#EEF0F7]">
            <div className="h-2.5 rounded-full transition-[width] duration-500"
              style={{ width: `${Math.max(1.5, Math.min(100, (d.value / top) * 100))}%`, background: d.color ?? COLORS.navy }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

/** One stacked 100 % bar (distribution) with a 2px surface gap between segments and a legend. */
export function StackedBar({ data }: { data: BarDatum[] }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (!total) return <p className="text-sm muted">No data yet</p>;
  return (
    <div>
      <div className="flex h-4 w-full gap-[2px] overflow-hidden rounded-full">
        {data.filter((d) => d.value > 0).map((d) => (
          <div key={d.key} title={`${d.label}: ${d.value} (${((d.value / total) * 100).toFixed(0)}%)`}
            style={{ width: `${(d.value / total) * 100}%`, background: d.color }} />
        ))}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-ink-soft">
        {data.map((d) => (
          <li key={d.key} className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: d.color }} aria-hidden />
            {d.label} <b className="text-ink">{d.value}</b>
          </li>
        ))}
      </ul>
    </div>
  );
}

// --------------------------------------------------------------------------- score trend line
export function TrendLine({ points, height = 170, threshold }: {
  points: { x: string; y: number; label?: string }[]; height?: number; threshold?: { value: number; label: string };
}) {
  const [hover, setHover] = useState<number | null>(null);
  if (points.length === 0) return <p className="text-sm muted">No attempts yet.</p>;
  const W = 640, H = height, L = 34, R = 12, T = 12, B = 22;
  const xs = (i: number) => L + (points.length === 1 ? (W - L - R) / 2 : (i / (points.length - 1)) * (W - L - R));
  const ys = (v: number) => T + (1 - v / 100) * (H - T - B);
  const path = points.map((p, i) => `${i ? "L" : "M"}${xs(i).toFixed(1)},${ys(p.y).toFixed(1)}`).join(" ");
  const h = hover !== null ? points[hover] : null;
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Score trend"
        onMouseLeave={() => setHover(null)}
        onMouseMove={(e) => {
          const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
          const x = ((e.clientX - r.left) / r.width) * W;
          const i = points.length === 1 ? 0 : Math.round(((x - L) / (W - L - R)) * (points.length - 1));
          setHover(Math.max(0, Math.min(points.length - 1, i)));
        }}>
        {[0, 25, 50, 75, 100].map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={ys(v)} y2={ys(v)} stroke="#EEF0F7" />
            <text x={L - 6} y={ys(v) + 3} textAnchor="end" fontSize={10} fill={COLORS.muted}>{v}</text>
          </g>
        ))}
        {threshold && (
          <g>
            <line x1={L} x2={W - R} y1={ys(threshold.value)} y2={ys(threshold.value)} stroke={COLORS.ok} strokeDasharray="4 4" />
            <text x={L + 4} y={ys(threshold.value) - 4} textAnchor="start" fontSize={10} fill={COLORS.muted}>{threshold.label}</text>
          </g>
        )}
        <path d={path} fill="none" stroke={COLORS.navy} strokeWidth={2} strokeLinejoin="round" />
        {points.map((p, i) => (
          <circle key={i} cx={xs(i)} cy={ys(p.y)} r={hover === i ? 5 : 3.5} fill={COLORS.navy} stroke="#fff" strokeWidth={2} />
        ))}
        {hover !== null && <line x1={xs(hover)} x2={xs(hover)} y1={T} y2={H - B} stroke={COLORS.muted} strokeDasharray="2 3" />}
      </svg>
      {h && (
        <div className="pointer-events-none absolute top-0 rounded-lg border border-line bg-white px-3 py-2 text-xs shadow-lift"
          style={{ left: `${Math.min(70, (xs(hover!) / W) * 100)}%` }}>
          <div className="font-bold text-ink">{h.y} points</div>
          <div className="muted">{h.label ?? h.x}</div>
        </div>
      )}
    </div>
  );
}

// --------------------------------------------------------------------------- confusion matrix
/** Sequential single-hue (lavender) heat cells; the diagonal is outlined. */
export function ConfusionMatrix({ matrix, labels }: { matrix: number[][]; labels: (string | number)[] }) {
  const max = Math.max(...matrix.flat(), 1);
  const shade = (v: number) => {
    const t = v / max;
    return `rgba(101, 83, 214, ${0.06 + 0.84 * t})`;
  };
  return (
    <div className="overflow-x-auto">
      <table className="text-xs">
        <thead>
          <tr>
            <th className="px-2 py-1 text-left font-semibold muted">true ↓ / pred →</th>
            {labels.map((l) => <th key={String(l)} className="px-2 py-1 font-semibold text-ink-soft">{l}</th>)}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={i}>
              <th className="px-2 py-1 text-left font-semibold text-ink-soft">{labels[i]}</th>
              {row.map((v, j) => (
                <td key={j} title={`true ${labels[i]} → predicted ${labels[j]}: ${v}`}
                  className={`h-9 min-w-[52px] rounded text-center font-mono font-semibold ${i === j ? "ring-2 ring-inset ring-navy" : ""}`}
                  style={{ background: shade(v), color: v / max > 0.55 ? "#fff" : COLORS.ink }}>
                  {v}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --------------------------------------------------------------------------- misc
/** Highlighted equation card used for the component novelties. */
export function EquationCard({ id, name, formula, children, novelty = true }: {
  id: string; name: string; formula: string; children?: ReactNode; novelty?: boolean;
}) {
  return (
    <div className={`rounded-xl border p-4 ${novelty ? "border-lav-200 bg-lav-50" : "border-line bg-white"}`}>
      <div className="flex items-center justify-between gap-2 text-xs font-bold uppercase tracking-wide text-lav-600">
        <span>{id} · {name}</span>
        {novelty && <span className="chip bg-sun-soft px-2 py-0.5 text-[10px] text-[#92400E]">★ Novelty</span>}
      </div>
      <div className="mt-2 font-mono text-[15px] font-semibold text-ink">{formula}</div>
      {children && <div className="mt-2 font-mono text-xs text-ink-soft">{children}</div>}
    </div>
  );
}

export function SeverityChip({ level, label }: { level: number | null; label?: string }) {
  if (!level) return <span className="chip bg-canvas text-ink-muted">–</span>;
  const c = severityColor(level);
  return (
    <span className="chip" style={{ background: `${c}1A`, color: COLORS.ink }}>
      <span className="h-2 w-2 rounded-full" style={{ background: c }} aria-hidden />
      L{level} · {label ?? SEVERITY_NAME[level]}
    </span>
  );
}

export function DisorderChip({ disorder }: { disorder: string | null }) {
  if (!disorder) return <span className="chip bg-canvas text-ink-muted">–</span>;
  return (
    <span className="chip bg-canvas text-ink">
      <span className="h-2 w-2 rounded-full" style={{ background: DISORDER_COLOR[disorder] }} aria-hidden />
      {DISORDER_LABEL[disorder] ?? disorder}
    </span>
  );
}

export function StatusChip({ status }: { status: string }) {
  const map: Record<string, [string, string]> = {
    completed: [COLORS.ok, "Completed"], partial: [COLORS.warn, "Partial"], failed: [COLORS.bad, "Failed"],
  };
  const [c, l] = map[status] ?? [COLORS.muted, status];
  return (
    <span className="chip" style={{ background: `${c}1A`, color: COLORS.ink }}>
      <span className="h-2 w-2 rounded-full" style={{ background: c }} aria-hidden />{l}
    </span>
  );
}
