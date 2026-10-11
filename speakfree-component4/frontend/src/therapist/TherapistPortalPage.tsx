import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronRight, RefreshCw, Search } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { CaseloadOverview, StudentRow, StudentStatusKey } from "../types/therapist";
import { getCaseloadOverview, getStudents } from "./therapistApi";
import { ColumnChart, HorizontalBars } from "./charts";
import {
  formatDate,
  formatRelative,
  initials,
  Panel,
  PortalHeader,
  StatTile,
  StatusPill,
} from "./ui";

const FILTERS: { key: "all" | StudentStatusKey; label: string }[] = [
  { key: "all", label: "All students" },
  { key: "needs_attention", label: "Needs attention" },
  { key: "inactive", label: "Inactive" },
  { key: "improving", label: "Improving" },
  { key: "on_track", label: "On track" },
  { key: "not_started", label: "Not started" },
];

const ACTIVITY_DAYS = 14;

/** Buckets session timestamps into the viewer's local calendar days. */
function dailyActivity(times: string[]) {
  const days = [];
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  for (let offset = ACTIVITY_DAYS - 1; offset >= 0; offset--) {
    const day = new Date(today);
    day.setDate(today.getDate() - offset);
    const next = new Date(day);
    next.setDate(day.getDate() + 1);
    days.push({
      label: day.toLocaleDateString(undefined, { day: "numeric", month: "short" }),
      exercises: times.filter((t) => {
        const d = new Date(t);
        return d >= day && d < next;
      }).length,
    });
  }
  return days;
}

export default function TherapistPortalPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [overview, setOverview] = useState<CaseloadOverview | null>(null);
  const [students, setStudents] = useState<StudentRow[] | null>(null);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["key"]>("all");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setError(false);
    Promise.all([getCaseloadOverview(), getStudents()])
      .then(([o, s]) => {
        if (!active) return;
        setOverview(o);
        setStudents(s);
      })
      .catch(() => active && setError(true));
    return () => {
      active = false;
    };
  }, [reload]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (students ?? []).filter(
      (s) =>
        (filter === "all" || s.status.key === filter) &&
        (!q || s.name.toLowerCase().includes(q) || s.email.includes(q))
    );
  }, [students, query, filter]);

  const activity = useMemo(
    () => dailyActivity(overview?.recent_session_times ?? []),
    [overview]
  );

  return (
    <div className="min-h-screen bg-paper">
      <PortalHeader />
      <main className="mx-auto max-w-6xl space-y-6 px-6 py-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold-600">
              Caseload overview
            </p>
            <h1 className="mt-1 font-display text-3xl font-semibold text-ink">
              Welcome, {user?.name}
            </h1>
            <p className="mt-1 text-sm text-ink-soft">
              Every registered student, their practice and how their progress is changing.
            </p>
          </div>
          <button
            onClick={() => setReload((n) => n + 1)}
            className="flex items-center gap-1.5 rounded-full border border-teal-200 px-4 py-2 text-sm font-medium text-teal-700 hover:bg-teal-50"
          >
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>

        {error && (
          <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-ink" role="alert">
            We couldn't load the caseload. Check that the therapy service is running, then refresh.
          </p>
        )}

        {!overview && !error && <p className="text-sm text-ink-soft">Loading caseload...</p>}

        {overview && (
          <>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
              <StatTile label="Registered students" value={overview.total_students} />
              <StatTile
                label="Active this week"
                value={overview.active_this_week}
                hint={`of ${overview.total_students} students`}
              />
              <StatTile label="Exercises this week" value={overview.sessions_this_week} />
              <StatTile
                label="Average score"
                value={overview.average_score ?? "—"}
                hint="across all saved exercises"
              />
              <StatTile
                label="Need follow-up"
                value={overview.needs_attention}
                hint="needs attention or inactive"
              />
            </div>

            {overview.alerts.length > 0 && (
              <Panel title="Needs your attention" subtitle="Students the system flagged for follow-up">
                <ul className="space-y-2">
                  {overview.alerts.map((a, i) => (
                    <li key={`${a.email}-${i}`}>
                      <button
                        onClick={() => navigate(`/therapist/students/${encodeURIComponent(a.email)}`)}
                        className="flex w-full flex-wrap items-center justify-between gap-2 rounded-xl bg-paper px-4 py-2.5 text-left text-sm hover:bg-teal-50/60"
                      >
                        <span className="font-medium text-ink">{a.name}</span>
                        <span className="flex items-center gap-2 text-ink-soft">
                          {a.status.detail}
                          <StatusPill status={a.status} />
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </Panel>
            )}

            <div className="grid gap-4 lg:grid-cols-5">
              <div className="lg:col-span-3">
                <Panel
                  title="Practice activity"
                  subtitle={`Exercises saved by all students, last ${ACTIVITY_DAYS} days`}
                >
                  <ColumnChart data={activity} xKey="label" yKey="exercises" unit="exercises" />
                </Panel>
              </div>
              <div className="lg:col-span-2">
                <Panel title="Reading levels" subtitle="How many students are at each level">
                  <HorizontalBars
                    data={overview.level_distribution}
                    labelKey="label"
                    valueKey="students"
                    unit="students"
                  />
                </Panel>
              </div>
            </div>
          </>
        )}

        {students && (
          <Panel
            title="Students"
            subtitle={`${visible.length} of ${students.length} shown — select a student to see their work`}
            action={
              <label className="relative">
                <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-soft" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search name or email"
                  className="w-56 rounded-full border border-teal-100 py-1.5 pl-8 pr-3 text-sm focus:border-teal-500 focus:outline-none"
                />
              </label>
            }
          >
            <div className="flex flex-wrap gap-2">
              {FILTERS.map((f) => (
                <button
                  key={f.key}
                  onClick={() => setFilter(f.key)}
                  className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                    filter === f.key
                      ? "border-teal-600 bg-teal-600 text-white"
                      : "border-teal-100 text-ink-soft hover:border-teal-400"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            {students.length === 0 ? (
              <p className="mt-4 text-sm text-ink-soft">
                No students have registered yet. They'll appear here as soon as they sign up.
              </p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="text-xs text-ink-soft">
                    <tr className="border-b border-teal-100">
                      <th className="py-2 pr-3 font-medium">Student</th>
                      <th className="py-2 pr-3 font-medium">Registered</th>
                      <th className="py-2 pr-3 font-medium">Last active</th>
                      <th className="py-2 pr-3 text-right font-medium">Exercises</th>
                      <th className="py-2 pr-3 text-right font-medium">Avg score</th>
                      <th className="py-2 pr-3 font-medium">Reading level</th>
                      <th className="py-2 pr-3 font-medium">Status</th>
                      <th className="py-2" />
                    </tr>
                  </thead>
                  <tbody className="tabular-nums">
                    {visible.map((s) => (
                      <tr
                        key={s.email}
                        onClick={() => navigate(`/therapist/students/${encodeURIComponent(s.email)}`)}
                        className="cursor-pointer border-b border-teal-50 last:border-0 hover:bg-teal-50/60"
                      >
                        <td className="py-3 pr-3">
                          <div className="flex items-center gap-3">
                            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-teal-100 text-xs font-semibold text-teal-800">
                              {initials(s.name)}
                            </span>
                            <span>
                              <span className="block font-medium text-ink">{s.name}</span>
                              <span className="block text-xs text-ink-soft">{s.email}</span>
                            </span>
                          </div>
                        </td>
                        <td className="py-3 pr-3 text-ink-soft">{formatDate(s.registered_at)}</td>
                        <td className="py-3 pr-3 text-ink-soft">{formatRelative(s.last_active)}</td>
                        <td className="py-3 pr-3 text-right text-ink">{s.total_sessions}</td>
                        <td className="py-3 pr-3 text-right font-semibold text-ink">
                          {s.average_score ?? "—"}
                        </td>
                        <td className="py-3 pr-3 text-ink">{s.level_label}</td>
                        <td className="py-3 pr-3">
                          <StatusPill status={s.status} />
                        </td>
                        <td className="py-3 text-ink-soft">
                          <ChevronRight size={16} />
                        </td>
                      </tr>
                    ))}
                    {visible.length === 0 && (
                      <tr>
                        <td colSpan={8} className="py-6 text-center text-sm text-ink-soft">
                          No students match this filter.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        )}
      </main>
    </div>
  );
}
