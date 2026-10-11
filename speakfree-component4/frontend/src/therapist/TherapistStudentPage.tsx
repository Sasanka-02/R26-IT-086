import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Lightbulb, Printer } from "lucide-react";
import { StudentDetail } from "../types/therapist";
import { getStudentDetail, rateAttempt } from "./therapistApi";
import StudentControls from "./StudentControls";
import { ColumnChart, ScoreLineChart } from "./charts";
import {
  formatDate,
  formatRelative,
  initials,
  Panel,
  PortalHeader,
  StatTile,
  StatusPill,
} from "./ui";

const RATING_LABEL = { easy: "Easy", ok: "Okay", hard: "Hard" };
const LEVEL_STEPS = ["Beginner", "Intermediate", "Advanced (final stage)"];

function formatDuration(seconds: number) {
  const total = Math.round(seconds);
  if (total < 60) return `${total}s`;
  return `${Math.floor(total / 60)}m ${total % 60}s`;
}

export default function TherapistStudentPage() {
  const navigate = useNavigate();
  const { email = "" } = useParams();
  const [detail, setDetail] = useState<StudentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [savingRating, setSavingRating] = useState<string | null>(null);

  const rate = async (recordId: string, rating: number) => {
    setSavingRating(recordId);
    try {
      await rateAttempt(email, recordId, rating);
      setReload((n) => n + 1);
    } finally {
      setSavingRating(null);
    }
  };

  useEffect(() => {
    let active = true;
    setError(null);
    getStudentDetail(email)
      .then((d) => active && setDetail(d))
      .catch((err) =>
        active &&
        setError(
          err?.response?.status === 404
            ? "This student could not be found."
            : "We couldn't load this student. Check that the therapy service is running."
        )
      );
    return () => {
      active = false;
    };
  }, [email, reload]);

  const summary = detail?.summary;

  return (
    <div className="min-h-screen bg-paper">
      <PortalHeader />
      <main className="mx-auto max-w-6xl space-y-6 px-6 py-8">
        <div className="no-print flex items-center justify-between">
          <button
            onClick={() => navigate("/therapist")}
            className="flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink"
          >
            <ArrowLeft size={15} />
            All students
          </button>
          {detail && (
            <button
              onClick={() => window.print()}
              className="flex items-center gap-1.5 rounded-full border border-teal-200 px-4 py-1.5 text-sm font-medium text-teal-700 hover:bg-teal-50"
            >
              <Printer size={14} />
              Print / save PDF report
            </button>
          )}
        </div>

        {error && (
          <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-ink" role="alert">
            {error}
          </p>
        )}
        {!detail && !error && <p className="text-sm text-ink-soft">Loading student...</p>}

        {detail && summary && (
          <>
            <section className="flex flex-wrap items-center gap-4 rounded-2xl border border-teal-100 bg-white p-6">
              <span className="flex h-14 w-14 items-center justify-center rounded-full bg-teal-600 font-display text-lg font-semibold text-white">
                {initials(detail.profile.name)}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="font-display text-2xl font-semibold text-ink">{detail.profile.name}</h1>
                  <StatusPill status={detail.row.status} />
                </div>
                <p className="text-sm text-ink-soft">{detail.profile.email}</p>
                <p className="mt-1 text-xs text-ink-soft">
                  Registered {formatDate(detail.profile.registered_at)} · Last login{" "}
                  {formatRelative(detail.profile.last_login)} · Last practice{" "}
                  {formatRelative(detail.row.last_active)}
                </p>
              </div>
              <p className="w-full text-sm text-ink-soft sm:w-auto sm:max-w-xs">
                {detail.row.status.detail}
              </p>
            </section>

            <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
              <StatTile label="Exercises completed" value={summary.total_sessions} />
              <StatTile label="Practice time" value={`${summary.total_minutes} min`} />
              <StatTile
                label="Average score"
                value={summary.average_score ?? "—"}
                hint={summary.best_score !== null ? `best ${summary.best_score}` : undefined}
              />
              <StatTile label="Current streak" value={`${summary.streak_days} d`} />
              <StatTile label="Reading level" value={summary.level.label.replace(" (final stage)", "")} />
            </div>

            <div className="no-print">
              <StudentControls
                email={detail.profile.email}
                settings={detail.settings}
                goals={summary.goals}
                onChanged={() => setReload((n) => n + 1)}
              />
            </div>

            {summary.has_data ? (
              <>
                <div className="grid gap-4 lg:grid-cols-5">
                  <div className="lg:col-span-3">
                    <Panel
                      title="Score per exercise"
                      subtitle={`${summary.trend.label} — ${summary.trend.detail}`}
                    >
                      <ScoreLineChart data={detail.score_history} />
                    </Panel>
                  </div>
                  <div className="lg:col-span-2">
                    <Panel title="Exercises per week" subtitle="Last 8 weeks">
                      <ColumnChart
                        data={detail.weekly_sessions}
                        xKey="label"
                        yKey="sessions"
                        unit="exercises"
                      />
                    </Panel>
                  </div>
                </div>

                <div className="grid gap-4 lg:grid-cols-2">
                  <Panel title="Reading level progress" subtitle={summary.level.progress_text}>
                    <ol className="grid gap-2 sm:grid-cols-3">
                      {LEVEL_STEPS.map((label, i) => {
                        const done =
                          i < summary.level.level_index ||
                          (summary.level.mastered && i === summary.level.level_index);
                        const current = i === summary.level.level_index && !summary.level.mastered;
                        return (
                          <li
                            key={label}
                            className={`rounded-xl border px-3 py-2 text-sm ${
                              current
                                ? "border-teal-600 bg-teal-600 text-white"
                                : done
                                ? "border-teal-200 bg-teal-50 text-teal-800"
                                : "border-dashed border-teal-100 text-ink-soft"
                            }`}
                          >
                            <span className="block font-semibold">{label}</span>
                            <span className="text-xs opacity-80">
                              {done ? "Completed" : current ? "Current" : "Not reached"}
                            </span>
                          </li>
                        );
                      })}
                    </ol>
                  </Panel>
                  <Panel title="Progress notes" subtitle="As shown to the student">
                    <ul className="space-y-2 text-sm text-ink">
                      {summary.highlights.map((line) => (
                        <li key={line} className="flex gap-2">
                          <Lightbulb size={16} className="mt-0.5 shrink-0 text-gold-500" />
                          {line}
                        </li>
                      ))}
                    </ul>
                  </Panel>
                </div>

                <Panel title="By exercise type">
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    {summary.by_type.map((t) => (
                      <div key={t.type} className="rounded-xl bg-paper px-4 py-3 text-sm">
                        <p className="font-semibold text-ink">{t.label}</p>
                        <p className="mt-1 text-ink-soft">
                          {t.sessions}× · avg {t.average_score} · best {t.best_score}
                        </p>
                      </div>
                    ))}
                  </div>
                </Panel>

                <Panel title="All work" subtitle={`${detail.records.length} saved exercises, newest first`}>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[900px] text-left text-sm">
                      <thead className="text-xs text-ink-soft">
                        <tr className="border-b border-teal-100">
                          <th className="py-2 pr-3 font-medium">Date</th>
                          <th className="py-2 pr-3 font-medium">Exercise</th>
                          <th className="py-2 pr-3 text-right font-medium">Time</th>
                          <th className="py-2 pr-3 text-right font-medium">Speaking</th>
                          <th className="py-2 pr-3 text-right font-medium">Long pauses</th>
                          <th className="py-2 pr-3 text-right font-medium" title="Measured words per minute / target">wpm</th>
                          <th className="py-2 pr-3 font-medium">Felt</th>
                          <th className="py-2 pr-3 text-right font-medium">Score</th>
                          <th className="no-print py-2 font-medium" title="Your clinical rating of this attempt (1 = very poor, 5 = very fluent). Used to validate and calibrate the score.">
                            Expert rating
                          </th>
                        </tr>
                      </thead>
                      <tbody className="tabular-nums">
                        {detail.records.map((r) => (
                          <tr key={r.id} className="border-b border-teal-50 last:border-0">
                            <td className="py-2.5 pr-3 text-ink-soft">{formatDate(r.completed_at, true)}</td>
                            <td className="py-2.5 pr-3 text-ink">{r.title}</td>
                            <td className="py-2.5 pr-3 text-right text-ink">{formatDuration(r.duration_seconds)}</td>
                            <td className="py-2.5 pr-3 text-right text-ink">
                              {r.speaking_ratio !== null ? `${Math.round(r.speaking_ratio * 100)}%` : "—"}
                            </td>
                            <td className="py-2.5 pr-3 text-right text-ink">
                              {r.speaking_ratio !== null ? r.long_pauses : "—"}
                            </td>
                            <td className="py-2.5 pr-3 text-right text-ink">
                              {r.measured_wpm ? `${r.measured_wpm}/${r.target_wpm}` : "—"}
                            </td>
                            <td className="py-2.5 pr-3 text-ink">{RATING_LABEL[r.self_rating]}</td>
                            <td className="py-2.5 pr-3 text-right">
                              <span className="font-semibold text-ink">{r.score}</span>{" "}
                              <span className="text-xs text-ink-soft">{r.verdict}</span>
                            </td>
                            <td className="no-print py-2.5">
                              <div className="flex gap-1" role="radiogroup" aria-label="Expert rating">
                                {[1, 2, 3, 4, 5].map((n) => (
                                  <button
                                    key={n}
                                    role="radio"
                                    aria-checked={r.expert?.rating === n}
                                    disabled={savingRating === r.id}
                                    onClick={() => rate(r.id, n)}
                                    className={`h-6 w-6 rounded-full text-xs font-semibold transition ${
                                      r.expert?.rating === n
                                        ? "bg-teal-600 text-white"
                                        : "border border-teal-100 text-ink-soft hover:border-teal-400"
                                    }`}
                                  >
                                    {n}
                                  </button>
                                ))}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Panel>
              </>
            ) : (
              <Panel title="No work yet">
                <p className="text-sm text-ink-soft">
                  {detail.profile.name} has registered but hasn't saved any exercises yet.
                </p>
              </Panel>
            )}
          </>
        )}
      </main>
    </div>
  );
}
