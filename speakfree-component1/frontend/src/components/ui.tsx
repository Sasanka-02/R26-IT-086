/** Shared presentational pieces used across pages (light SpeakFree theme). */
import type { ReactNode } from "react";
import { Loader2 } from "lucide-react";
import type { Visual } from "../types";

// --------------------------------------------------------------------------- colour helpers
export const COLORS = {
  navy: "#1E3A8A",
  brand: "#1D4ED8",
  lav: "#7C6CF0",
  lavSoft: "#EFEBFF",
  sun: "#F59E0B",
  ok: "#16A34A",
  warn: "#D97706",
  bad: "#DC2626",
  track: "#EEF0F7",
  ink: "#1B2559",
  muted: "#7A8299",
};

export function scoreColor(v: number) {
  if (v >= 85) return COLORS.ok;
  if (v >= 70) return COLORS.brand;
  if (v >= 55) return COLORS.warn;
  return COLORS.bad;
}
export function scoreWord(v: number) {
  if (v >= 85) return "Good";
  if (v >= 70) return "Fair";
  if (v >= 55) return "Needs practice";
  return "Concern";
}
export const SEVERITY_COLORS = [COLORS.ok, COLORS.brand, COLORS.warn, COLORS.bad];
export const pct = (v: number, d = 1) => `${v.toFixed(d)}%`;

// --------------------------------------------------------------------------- brand
export function Logo({ size = "md", subtitle = true }: { size?: "md" | "lg"; subtitle?: boolean }) {
  const tile = size === "lg" ? "h-14 w-14" : "h-11 w-11";
  return (
    <div className="flex items-center gap-3">
      <div className={`${tile} relative grid shrink-0 place-items-center rounded-xl bg-navy shadow-nav`}>
        <svg viewBox="0 0 24 24" className="h-3/5 w-3/5" aria-hidden>
          {[4, 8, 12, 16, 20].map((x, i) => (
            <rect key={x} x={x - 1} y={[8, 5, 3, 5, 8][i]} width="2" height={[8, 14, 18, 14, 8][i]} rx="1" fill={i === 2 ? COLORS.sun : "#ffffff"} />
          ))}
        </svg>
        {/* speech-bubble tail */}
        <span className="absolute -bottom-1.5 left-2.5 h-3 w-3 rotate-45 rounded-sm bg-navy" aria-hidden />
      </div>
      <div className="leading-tight">
        <div className={`${size === "lg" ? "text-3xl" : "text-[22px]"} font-extrabold tracking-tight text-navy`}>
          Speak<span className="text-sun">Free</span>
        </div>
        {subtitle && (
          <div className="max-w-[190px] text-[10.5px] font-medium leading-snug text-ink-soft">AI-Based Speech Disorder Screening and Therapy Assistant</div>
        )}
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------- feedback
export function Spinner({ className = "h-64" }: { className?: string }) {
  return (
    <div className={`grid place-items-center ${className}`}>
      <Loader2 className="animate-spin text-brand" size={32} />
    </div>
  );
}

export function ErrorBox({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div role="alert" className="rounded-xl border border-bad/30 bg-bad-soft px-4 py-3 text-sm text-bad">
      {message}
    </div>
  );
}

export function Card({ title, icon, right, children, className = "" }: {
  title?: ReactNode; icon?: ReactNode; right?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section className={`card p-5 ${className}`}>
      {title && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-[15px] font-bold text-ink">{icon}{title}</h2>
          {right}
        </div>
      )}
      {children}
    </section>
  );
}

// --------------------------------------------------------------------------- score ring
export function ScoreRing({ value, size = 128, stroke = 12, suffix = "", sub, color }: {
  value: number; size?: number; stroke?: number; suffix?: string; sub?: string; color?: string;
}) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const frac = Math.max(0, Math.min(1, value / 100));
  const c = color ?? scoreColor(value);
  return (
    <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} role="img" aria-label={`${value.toFixed(0)}${suffix}`}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={COLORS.track} strokeWidth={stroke} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={c} strokeWidth={stroke} strokeLinecap="round"
        strokeDasharray={`${circ * frac} ${circ}`} transform={`rotate(-90 ${size / 2} ${size / 2})`}
        style={{ transition: "stroke-dasharray 0.8s ease" }} />
      <text x="50%" y={sub ? "48%" : "53%"} textAnchor="middle" dominantBaseline="middle" fontSize={size * 0.24} fontWeight={800} fill={COLORS.ink}>
        {value.toFixed(0)}{suffix}
      </text>
      {sub && <text x="50%" y="68%" textAnchor="middle" fontSize={size * 0.09} fill={COLORS.muted}>{sub}</text>}
    </svg>
  );
}

export function Bar({ value, color, className = "h-2" }: { value: number; color?: string; className?: string }) {
  return (
    <div className={`w-full rounded-full bg-[#EEF0F7] ${className}`}>
      <div className={`rounded-full ${className}`} style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: color ?? scoreColor(value), transition: "width 0.6s ease" }} />
    </div>
  );
}

// --------------------------------------------------------------------------- severity gauge
export function SeverityGauge({ hint, label, risk }: { hint: number; label: string; risk: string }) {
  const angle = -90 + ((hint - 0.5) / 4) * 180;
  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 200 112" className="w-52" role="img" aria-label={`Screening level ${hint} of 4`}>
        {SEVERITY_COLORS.map((c, i) => {
          const a0 = Math.PI + (i / 4) * Math.PI + 0.02;
          const a1 = Math.PI + ((i + 1) / 4) * Math.PI - 0.02;
          const p = (a: number, r: number) => `${100 + r * Math.cos(a)},${100 + r * Math.sin(a)}`;
          return <path key={i} d={`M${p(a0, 80)} A80,80 0 0 1 ${p(a1, 80)}`} stroke={c} strokeWidth={16} fill="none" opacity={i + 1 === hint ? 1 : 0.22} />;
        })}
        <g transform={`rotate(${angle} 100 100)`}>
          <line x1={100} y1={100} x2={100} y2={36} stroke={COLORS.ink} strokeWidth={3} strokeLinecap="round" />
        </g>
        <circle cx={100} cy={100} r={6} fill={COLORS.ink} />
      </svg>
      <div className="mt-1 text-center text-lg font-bold" style={{ color: SEVERITY_COLORS[hint - 1] }}>{label}</div>
      <div className="text-xs muted">Screening level {hint} / 4 · risk: {risk}</div>
    </div>
  );
}

// --------------------------------------------------------------------------- task illustrations
/** Illustrated scene for picture / scenario tasks: an emoji scene on a sky-and-grass backdrop, or a bar chart. */
export function SceneVisual({ visual, imageUrl, alt, tone = "park", className = "h-44" }: {
  visual?: Visual | null; imageUrl?: string | null; alt?: string; tone?: "park" | "indoor"; className?: string;
}) {
  if (imageUrl) {
    // alt text: explicit alt, else the task's caption (picture tasks always carry one), else a generic label
    const altText = alt || (visual?.kind === "emoji" && visual.caption) || "Task picture";
    return <img src={imageUrl} alt={altText} className={`w-full rounded-xl object-cover ${className}`} />;
  }
  if (!visual) return null;
  if (visual.kind === "chart") {
    const max = Math.max(...visual.data.map((d) => d.value));
    return (
      <figure className="rounded-xl border border-line bg-lav-50 p-3">
        <figcaption className="mb-2 text-xs font-semibold text-ink-soft">{visual.title}</figcaption>
        <div className="flex h-36 items-end gap-2">
          {visual.data.map((d) => (
            <div key={d.label} className="flex flex-1 flex-col items-center gap-1">
              <span className="font-mono text-[10px] text-ink-soft">{d.value}</span>
              <div className="w-full rounded-t-md bg-gradient-to-t from-navy to-lav-500" style={{ height: `${(d.value / max) * 100}px` }} />
              <span className="text-[10px] muted">{d.label}</span>
            </div>
          ))}
        </div>
        <div className="mt-1 text-right text-[10px] muted">{visual.unit}</div>
      </figure>
    );
  }
  const backdrop = tone === "park"
    ? "linear-gradient(180deg, #DCEBFF 0%, #EEF5FF 55%, #CFEBC9 55%, #B8DFAE 100%)"
    : "linear-gradient(180deg, #F6E9D9 0%, #FBF3EA 60%, #E9D3B8 60%, #DDC3A3 100%)";
  return (
    <figure className={`relative overflow-hidden rounded-xl border border-line ${className}`} style={{ background: backdrop }}>
      <div className="absolute inset-0 flex flex-wrap content-center items-end justify-center gap-x-4 gap-y-1 px-4 pb-6 text-[44px] leading-none" role="img" aria-label={visual.caption}>
        {visual.emojis.map((e, i) => (
          <span key={i} className="drop-shadow-sm" style={{ transform: `translateY(${(i % 2) * -10}px)` }}>{e}</span>
        ))}
      </div>
      <figcaption className="absolute inset-x-0 bottom-0 bg-white/80 px-3 py-1 text-center text-[11px] font-medium text-ink-soft backdrop-blur">
        {visual.caption}
      </figcaption>
    </figure>
  );
}

export function StepBadge({ n, done = false }: { n: number; done?: boolean }) {
  return (
    <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-full text-sm font-bold text-white ${done ? "bg-ok" : "bg-navy"}`}>
      {done ? "✓" : n}
    </span>
  );
}

/** Screening risk level (1–4) as a coloured chip; "Not screened" when there is no session yet. */
export function RiskBadge({ hint, label }: { hint: number | null; label?: string | null }) {
  if (!hint) return <span className="chip bg-canvas text-ink-muted">Not screened yet</span>;
  const color = SEVERITY_COLORS[hint - 1];
  return (
    <span className="chip" style={{ background: `${color}1A`, color }}>
      <span className="h-2 w-2 rounded-full" style={{ background: color }} aria-hidden />
      Level {hint}{label ? ` · ${label}` : ""}
    </span>
  );
}
