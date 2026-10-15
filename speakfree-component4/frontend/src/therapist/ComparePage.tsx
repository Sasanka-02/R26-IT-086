import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Bot, Gauge, ListChecks } from "lucide-react";
import { CompareColumn, CompareResponse, StudentRow } from "../types/therapist";
import { compareStudents, getStudents } from "./therapistApi";
import { Panel } from "./ui";
import AppShell from "../components/AppShell";
import { LevelTimeline, ReportCard } from "../components/ReportCard";

function Column({ s }: { s: CompareColumn }) {
  return (
    <div className="min-w-0 space-y-4">
      <ReportCard card={s.report_card} name={s.name.split(" ")[0]} />

      <Panel title="Reading level" subtitle={`${s.level.label} · ${s.level.progress_text}`}>
        <LevelTimeline history={s.level.history} />
      </Panel>

      <Panel title="This week's plan" subtitle="Generated from this student's own attempts">
        <ul className="mb-3 space-y-1 text-sm text-ink-soft">
          {s.plan.why.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
        <ol className="space-y-2">
          {s.plan.exercises.map((ex, i) => (
            <li key={ex.id} className="rounded-xl bg-paper px-3 py-2 text-sm">
              <span className="flex items-center gap-1.5 font-medium text-ink">
                <ListChecks size={14} className="text-teal-600" />
                {i + 1}. {ex.title}
              </span>
              <span className="block text-xs text-ink-soft">{ex.explanation}</span>
            </li>
          ))}
        </ol>
      </Panel>

      <Panel title="Personal reading speed" subtitle="The highlight speed adapts: strong attempts +10%, difficult ones −10%">
        <table className="w-full text-left text-sm tabular-nums">
          <tbody>
            {s.reading_speeds.map((r) => (
              <tr key={r.title} className="border-b border-teal-50 last:border-0">
                <td className="py-1.5 pr-3 text-ink">{r.title}</td>
                <td className="py-1.5 text-right text-ink">
                  <Gauge size={13} className="mr-1 inline text-teal-600" />
                  <strong>{r.personal_wpm}</strong>
                  <span className="text-xs text-ink-soft"> wpm (base {r.base_wpm})</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <Panel title="Assistant answer" subtitle={`Same question, ${s.name.split(" ")[0]}'s data`}>
        <p className="flex gap-2 text-sm text-ink">
          <Bot size={16} className="mt-0.5 shrink-0 text-teal-600" />
          <span className="whitespace-pre-line">{s.assistant.reply}</span>
        </p>
        <p className="mt-2 text-xs text-ink-soft">
          Intent: {s.assistant.intent ?? "—"} · confidence {Math.round(s.assistant.confidence * 100)}% ·{" "}
          {s.assistant.source}
        </p>
      </Panel>
    </div>
  );
}

/** Two students side by side: shows that levels, plans, reading speeds and
 *  assistant answers all come from each student's own history. */
export default function ComparePage() {
  const [params, setParams] = useSearchParams();
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [data, setData] = useState<CompareResponse | null>(null);
  const [error, setError] = useState(false);
  const a = params.get("a") ?? "";
  const b = params.get("b") ?? "";

  useEffect(() => {
    getStudents()
      .then((rows) => {
        setStudents(rows);
        if (!a || !b) {
          const active = rows.filter((r) => r.total_sessions > 0).sort((x, y) => x.average_score! - y.average_score!);
          if (active.length >= 2) setParams({ a: active[0].email, b: active[active.length - 1].email }, { replace: true });
        }
      })
      .catch(() => setError(true));
    // Only on first load: default to the lowest- and highest-scoring active students.
  }, []);

  useEffect(() => {
    if (!a || !b) return;
    let active = true;
    setError(false);
    compareStudents(a, b)
      .then((d) => active && setData(d))
      .catch(() => active && setError(true));
    return () => {
      active = false;
    };
  }, [a, b]);

  const select = (key: "a" | "b", value: string) => setParams({ a, b, [key]: value });

  return (
    <AppShell>
      <main className="mx-auto max-w-6xl space-y-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold-600">Personalisation</p>
          <h1 className="mt-1 font-display text-3xl font-semibold text-ink">Compare two students</h1>
          <p className="mt-1 max-w-3xl text-sm text-ink-soft">
            Everything below is computed from each student's own practice history: the same engine gives different
            levels, plans, reading speeds and assistant answers.
          </p>
        </div>

        <div className="no-print grid gap-3 sm:grid-cols-2">
          {(["a", "b"] as const).map((key) => (
            <label key={key} className="text-sm text-ink-soft">
              Student {key.toUpperCase()}
              <select
                value={key === "a" ? a : b}
                onChange={(e) => select(key, e.target.value)}
                className="mt-1 block w-full rounded-xl border border-teal-100 bg-white px-3 py-2 text-sm text-ink"
              >
                <option value="">Choose a student</option>
                {students.map((s) => (
                  <option key={s.email} value={s.email}>
                    {s.name} · {s.total_sessions} exercises · {s.level_label}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>

        {error && (
          <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-ink" role="alert">
            We couldn't load the comparison.
          </p>
        )}
        {(!a || !b) && !error && <p className="text-sm text-ink-soft">Choose two students to compare.</p>}
        {data && a && b && (
          <>
            <p className="text-sm text-ink-soft">
              Question asked to the assistant for both: <strong className="text-ink">“{data.question}”</strong>
            </p>
            <div className="grid gap-5 lg:grid-cols-2">
              <Column s={data.students[0]} />
              <Column s={data.students[1]} />
            </div>
          </>
        )}
      </main>
    </AppShell>
  );
}
