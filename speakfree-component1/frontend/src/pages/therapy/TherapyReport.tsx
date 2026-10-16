/**
 * TherapyReport – printable therapy progress report (Component 4) for the active patient.
 * Rendered without the app shell so "Save as PDF" is clean; ?print=1 opens the print dialog.
 * Patient-safe like the plan itself: focus name, levels, goals and practice numbers only.
 */
import { useEffect, useState, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { Printer } from "lucide-react";
import { api } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { ErrorBox, Logo, Spinner } from "../../components/ui";
import { TrendLine } from "../../components/charts";
import type { TherapyPlan } from "../../types/integration";
import { TYPE_LABEL } from "./TherapyPlan";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="break-inside-avoid-page">
      <h2 className="mb-3 border-b border-line pb-1 text-base font-bold text-navy">{title}</h2>
      {children}
    </section>
  );
}

export default function TherapyReport() {
  const { activePatient } = useAuth();
  const [params] = useSearchParams();
  const [plan, setPlan] = useState<TherapyPlan | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activePatient) return;
    api.therapy.plan(activePatient.id).then((p) => (p.has_profile ? setPlan(p) : setError("No therapy plan yet.")))
      .catch((e: Error) => setError(e.message));
  }, [activePatient]);
  useEffect(() => {
    if (!plan || params.get("print") !== "1") return;
    const t = window.setTimeout(() => window.print(), 700);
    return () => window.clearTimeout(t);
  }, [plan, params]);

  if (error) return <div className="mx-auto max-w-3xl p-8"><ErrorBox message={error} /></div>;
  if (!plan || !activePatient) return <Spinner className="min-h-screen" />;
  const p = plan.progress;

  return (
    <div className="min-h-screen bg-canvas py-8 print:bg-white print:py-0">
      <div className="mx-auto mb-4 flex max-w-[860px] justify-end px-4 print:hidden">
        <button onClick={() => window.print()} className="btn-primary"><Printer size={16} /> Print / Save as PDF</button>
      </div>
      <article className="mx-auto max-w-[860px] space-y-7 bg-white p-8 shadow-card print:max-w-none print:p-0 print:shadow-none sm:rounded-2xl">
        <header className="flex flex-wrap items-start justify-between gap-4 border-b-2 border-navy pb-4">
          <Logo subtitle={false} />
          <div className="text-right">
            <h1 className="text-xl font-extrabold text-ink">Therapy Progress Report</h1>
            <p className="text-xs text-ink-soft">Adaptive therapy plan (Component 4)</p>
          </div>
        </header>

        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
          {[
            ["Patient", activePatient.full_name], ["Patient ID", activePatient.id], ["Age", String(activePatient.age)],
            ["Generated", new Date().toLocaleString()], ["Plan focus", plan.focus.patient_name], ["Current level", plan.level.label],
            ["Weekly dose", `${plan.dose.sessions_per_week} × ${plan.dose.minutes_per_session} min`], ["Day streak", String(p.streak_days)],
          ].map(([k, v]) => (
            <div key={k}><dt className="text-[11px] font-semibold uppercase tracking-wide muted">{k}</dt><dd className="font-semibold text-ink">{v}</dd></div>
          ))}
        </dl>

        <Section title="Summary">
          <div className="grid gap-3 sm:grid-cols-4">
            {[["Exercises", p.total_sessions], ["Minutes", p.total_minutes], ["Average score", p.average_score ?? "–"], ["Best score", p.best_score ?? "–"]].map(([k, v]) => (
              <div key={k} className="rounded-xl border border-line p-3"><div className="text-xs muted">{k}</div><div className="text-2xl font-extrabold text-ink">{v}</div></div>
            ))}
          </div>
          <p className="mt-3 text-sm text-ink-soft"><b>Trend:</b> {p.trend.label} – {p.trend.detail}</p>
        </Section>

        <Section title="Score history">
          <TrendLine points={p.history.map((h) => ({ x: String(h.attempt), y: h.score, label: h.title }))} threshold={{ value: plan.level.strong_threshold, label: "strong" }} />
        </Section>

        <Section title="Goals">
          <table className="w-full border-collapse text-[13px]">
            <thead><tr>{["Goal", "Now", "Target", "Met"].map((h, i) => <th key={h} className={`border-b border-line bg-canvas px-2 py-1.5 font-semibold text-ink-soft ${i ? "text-right" : "text-left"}`}>{h}</th>)}</tr></thead>
            <tbody>{plan.goals.map((g) => (
              <tr key={g.id}><td className="border-b border-line px-2 py-1.5">{g.text}</td><td className="border-b border-line px-2 py-1.5 text-right font-mono">{g.current ?? "–"}</td>
                <td className="border-b border-line px-2 py-1.5 text-right font-mono">{g.target}</td><td className="border-b border-line px-2 py-1.5 text-right">{g.met ? "✓" : "–"}</td></tr>
            ))}</tbody>
          </table>
        </Section>

        <Section title="Practice by exercise type">
          <table className="w-full border-collapse text-[13px]">
            <thead><tr>{["Exercise type", "Attempts", "Average", "Best"].map((h, i) => <th key={h} className={`border-b border-line bg-canvas px-2 py-1.5 font-semibold text-ink-soft ${i ? "text-right" : "text-left"}`}>{h}</th>)}</tr></thead>
            <tbody>{p.by_type.map((t) => (
              <tr key={t.type}><td className="border-b border-line px-2 py-1.5">{TYPE_LABEL[t.type] ?? t.label}</td><td className="border-b border-line px-2 py-1.5 text-right font-mono">{t.attempts}</td>
                <td className="border-b border-line px-2 py-1.5 text-right font-mono">{t.average_score ?? "–"}</td><td className="border-b border-line px-2 py-1.5 text-right font-mono">{t.best_score}</td></tr>
            ))}</tbody>
          </table>
        </Section>

        <Section title="Level history">
          <ul className="space-y-1 text-sm">{plan.level.history.map((h, i) => (
            <li key={i}><b>{h.from ? `${h.from} → ` : ""}{h.to}</b> <span className="muted">– {h.reason}{h.at ? ` (${new Date(h.at).toLocaleDateString()})` : ""}</span></li>
          ))}</ul>
        </Section>

        <footer className="border-t border-line pt-3 text-[11px] leading-relaxed muted">
          SpeakFree is a screening and practice aid, not a diagnosis. Scores describe practice quality measured in the browser
          (voicing, pauses, speaking rate, goal completion and self-rating); no audio was stored.
        </footer>
      </article>
    </div>
  );
}
