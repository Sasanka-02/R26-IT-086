/**
 * ProgressDashboard – the patient's therapy practice in plain language first, charts second:
 * report card → level + timeline → highlights + goals → (details) KPIs, score trend, weekly and
 * daily practice, practice mix, first try vs latest, score by type, badges, recent exercises, table.
 * Patient-safe: built only from the plan (no screening category or level is named).
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { Award, CalendarCheck, CheckCircle2, ChevronDown, Circle, Clock, Download, Flame, Lightbulb, Target, UserCheck } from "lucide-react";
import { Card, ScoreRing } from "../../components/ui";
import { HBars, TrendLine } from "../../components/charts";
import { DailyActivityChart, FirstVsLatestChart, KpiTile, ScorePill, WeeklyColumns } from "../../components/progressCharts";
import { LevelTimeline, ReportCard } from "../../components/therapy/ReportCard";
import BadgeShowcase from "../../components/therapy/Badges";
import type { Goal, TherapyPlan, WordLevelState } from "../../types/integration";
import { TYPE_LABEL } from "./labels";

const RATING = { easy: "Felt easy", ok: "Felt okay", hard: "Felt hard" } as Record<string, string>;

export function WordLadder({ words }: { words: WordLevelState }) {
  return (
    <Card title="Word practice ladder" icon={<span aria-hidden>🌟</span>} right={<span className="text-xs muted">{words.rounds} round{words.rounds === 1 ? "" : "s"}</span>}>
      <ol className="flex flex-wrap gap-1.5" aria-label="Word ladder">
        {Array.from({ length: words.ladder_size }, (_, i) => {
          const step = i + 1;
          const done = step < words.level || (words.mastered && step === words.level);
          const current = step === words.level && !words.mastered;
          const label = step <= words.word_levels ? `${step}` : `P${step - words.word_levels}`;
          return (
            <li key={step} title={step <= words.word_levels ? `Word level ${step}` : `Phrase stage ${step - words.word_levels}`}
              className={`grid h-9 min-w-[2.25rem] place-items-center rounded-full px-2 text-sm font-bold ${current ? "bg-sun text-ink shadow-sm" : done ? "bg-sun-soft text-warn" : "border border-dashed border-line text-ink-muted"}`}>
              {done ? "⭐" : label}
            </li>
          );
        })}
      </ol>
      <p className="mt-3 text-sm text-ink-soft">{words.progress_text}</p>
      <p className="mt-1 text-xs muted">Levels 1–7 are single words (easy sounds → long tricky words); P1–P3 are phrases, sentences and tongue twisters.</p>
    </Card>
  );
}

export function GoalList({ goals }: { goals: Goal[] }) {
  return (
    <ul className="space-y-2">
      {goals.map((g) => (
        <li key={g.id} className="flex items-start gap-2.5 rounded-xl bg-canvas px-4 py-3 text-sm">
          {g.met ? <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-ok" /> : <Circle size={18} className="mt-0.5 shrink-0 text-ink-muted" />}
          <span className="min-w-0">
            <span className="font-semibold text-ink">{g.text}</span>
            {g.source === "therapist" && <span className="chip ml-2 bg-ok-soft px-2 py-0 text-[10px] text-ok"><UserCheck size={10} /> therapist</span>}
            <span className="block text-xs muted">Now: {g.current ?? "no data yet"} · target {g.target}{g.screening_goal ? " at your next screening" : ""} · {g.met ? "Goal met" : "Not met yet"}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}

export default function ProgressDashboard({ plan, name }: { plan: TherapyPlan; name?: string }) {
  const [details, setDetails] = useState(false);
  const { progress: p, dashboard: d, level } = plan;
  const week = d.weekly[0];
  const total = p.by_type.reduce((n, t) => n + t.attempts, 0);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-extrabold">Therapy practice · {plan.focus.patient_name}</h2>
        <div className="flex gap-2">
          <Link to="/therapy-plan" className="btn-ghost py-2">Open my plan</Link>
          <Link to="/therapy/report?print=1" className="btn-outline py-2"><Download size={15} /> Download report (PDF)</Link>
        </div>
      </div>

      <ReportCard card={d.report_card} name={name} />
      {plan.word_level && <WordLadder words={plan.word_level} />}

      <div className="grid gap-5 lg:grid-cols-2">
        <Card title={`Your level · ${level.label}`} icon={<Award size={18} className="text-navy" />}>
          <p className="text-sm text-ink-soft">{level.dashboard_text}</p>
          <div className="mt-4 border-t border-line pt-4">
            <p className="mb-3 text-xs font-bold uppercase tracking-widest text-ink-muted">Level timeline</p>
            <LevelTimeline history={level.history} />
          </div>
        </Card>
        <div className="space-y-5">
          {d.highlights.length > 0 && (
            <Card title="What this means for you" icon={<Lightbulb size={18} className="text-sun" />}>
              <ul className="space-y-2.5">{d.highlights.map((h) => <li key={h} className="flex gap-2.5 text-sm text-ink"><Lightbulb size={15} className="mt-0.5 shrink-0 text-sun" />{h}</li>)}</ul>
            </Card>
          )}
          <Card title="Your goals" icon={<Target size={18} className="text-navy" />}><GoalList goals={plan.goals} /></Card>
        </div>
      </div>

      {!p.has_data ? (
        <Card title="Badges to work towards"><BadgeShowcase badges={d.badges} /></Card>
      ) : (
        <>
          <button onClick={() => setDetails((v) => !v)} aria-expanded={details}
            className="card flex w-full items-center justify-between px-5 py-4 text-left hover:bg-canvas print:hidden">
            <span>
              <span className="font-bold text-ink">Details: charts and numbers</span>
              <span className="block text-xs muted">Score trend, weekly practice, practice mix, first try vs latest, badges and recent exercises</span>
            </span>
            <ChevronDown size={18} className={`shrink-0 transition ${details ? "rotate-180" : ""}`} />
          </button>

          {details && (
            <div className="animate-step space-y-5">
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                <KpiTile icon={CalendarCheck} value={p.total_sessions} label="Exercises completed" caption={week ? `${week.sessions} this week` : undefined} />
                <KpiTile icon={Clock} value={`${p.total_minutes} min`} label="Practice time" caption={week ? `${week.minutes} min this week` : undefined} />
                <KpiTile icon={Flame} value={`${p.streak_days} day${p.streak_days === 1 ? "" : "s"}`} label="Current streak" caption={`best ${d.best_streak} · ${d.active_days} active days`} />
                <KpiTile icon={Award} value={p.average_score ?? "–"} label="Average score" caption={`best ${p.best_score ?? "–"} of 100`} />
              </div>

              <div className="grid gap-5 lg:grid-cols-3">
                <Card title="Score trend" className="lg:col-span-2" right={<span className="chip bg-lav-100 text-lav-600">{p.trend.label}</span>}>
                  <TrendLine points={p.history.map((h) => ({ x: String(h.attempt), y: h.score, label: `${h.title} · ${new Date(h.completed_at).toLocaleDateString()}` }))}
                    threshold={{ value: level.strong_threshold, label: "strong" }} />
                  <p className="mt-2 text-sm text-ink-soft">{p.trend.detail}</p>
                </Card>
                <Card title="Average score">
                  <div className="grid place-items-center"><ScoreRing value={p.average_score ?? 0} size={150} sub="out of 100" /></div>
                </Card>
              </div>

              <div className="grid gap-5 lg:grid-cols-3">
                <Card title="Weekly practice"><WeeklyColumns weekly={d.weekly} /></Card>
                <Card title="Daily activity · 14 days"><DailyActivityChart daily={p.daily} /></Card>
                <Card title="Practice mix">
                  <HBars format={(v) => `${Math.round(v)}%`} max={100}
                    data={[...p.by_type].sort((a, b) => b.attempts - a.attempts).map((t) => ({ key: t.type, label: TYPE_LABEL[t.type] ?? t.label, value: (t.attempts / total) * 100 }))} />
                </Card>
              </div>

              <div className="grid gap-5 lg:grid-cols-2">
                <Card title="First try vs latest"><FirstVsLatestChart rows={d.first_vs_latest} /></Card>
                <Card title="Score by exercise type">
                  <HBars format={(v) => String(Math.round(v))} max={100}
                    data={p.by_type.map((t) => ({ key: t.type, label: `${TYPE_LABEL[t.type] ?? t.label} · ${t.attempts}× · best ${t.best_score}`, value: t.average_score ?? 0 }))} />
                </Card>
              </div>

              <Card title="Badges"><BadgeShowcase badges={d.badges} /></Card>

              <Card title="Recent exercises">
                <ul className="divide-y divide-line">
                  {p.recent.map((r, i) => (
                    <li key={`${r.completed_at}-${i}`} className="flex flex-wrap items-center gap-3 py-3 text-sm">
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold text-ink">{r.title}</p>
                        <p className="text-xs muted">{new Date(r.completed_at).toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })} · {RATING[r.self_rating]}</p>
                      </div>
                      <span className="w-32 text-right text-xs muted">{r.verdict}</span>
                      <ScorePill score={r.score} />
                    </li>
                  ))}
                </ul>
              </Card>

              <details className="card p-5">
                <summary className="cursor-pointer text-sm font-bold text-ink">Week by week (table view)</summary>
                <table className="mt-3 w-full text-left text-sm tabular-nums">
                  <thead className="text-xs muted"><tr className="border-b border-line"><th className="py-2">Week</th><th>Exercises</th><th>Practice time</th><th>Average score</th></tr></thead>
                  <tbody>{d.weekly.map((w) => (
                    <tr key={w.label} className="border-b border-line last:border-0"><td className="py-2">{w.label}</td><td>{w.sessions}</td><td>{w.minutes} min</td><td>{w.average_score ?? "No practice"}</td></tr>
                  ))}</tbody>
                </table>
              </details>
            </div>
          )}
        </>
      )}
    </div>
  );
}
