import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { TrendingDown, Flame, Clock } from "lucide-react";
import { getDashboard } from "./therapyApi";
import { DashboardResponse } from "../types/therapy";

export default function ProgressDashboard({ sessionId }: { sessionId: string }) {
  const [data, setData] = useState<DashboardResponse | null>(null);

  useEffect(() => {
    getDashboard(sessionId).then(setData);
  }, [sessionId]);

  if (!data) return <p className="text-sm text-ink-soft">Loading dashboard...</p>;

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-teal-100 bg-white p-4">
          <Flame className="text-gold-500" size={18} />
          <p className="mt-2 font-display text-xl font-semibold text-ink">
            {data.current_streak_weeks} weeks
          </p>
          <p className="text-xs text-ink-soft">Active streak</p>
        </div>
        <div className="rounded-2xl border border-teal-100 bg-white p-4">
          <Clock className="text-teal-600" size={18} />
          <p className="mt-2 font-display text-xl font-semibold text-ink">
            {data.total_practice_hours}h
          </p>
          <p className="text-xs text-ink-soft">Total practice</p>
        </div>
        <div className="rounded-2xl border border-teal-100 bg-white p-4">
          <TrendingDown className="text-teal-600" size={18} />
          <p className="mt-2 font-display text-xl font-semibold text-ink">
            {data.total_practice_sessions}
          </p>
          <p className="text-xs text-ink-soft">Sessions completed</p>
        </div>
      </div>

      <div className="rounded-2xl border border-teal-100 bg-white p-5">
        <h3 className="text-sm font-semibold text-ink">
          Stuttering frequency (events/min) — lower is better
        </h3>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data.weekly_trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="#DCEBE5" />
            <XAxis dataKey="week" tickFormatter={(w) => `Wk ${w}`} fontSize={12} />
            <YAxis fontSize={12} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="stuttering_events_per_min"
              stroke="#2F6F62"
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="rounded-2xl border border-teal-100 bg-white p-5">
        <h3 className="text-sm font-semibold text-ink">Articulation accuracy (%)</h3>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data.weekly_trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="#DCEBE5" />
            <XAxis dataKey="week" tickFormatter={(w) => `Wk ${w}`} fontSize={12} />
            <YAxis domain={[0, 100]} fontSize={12} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="articulation_accuracy"
              stroke="#D9A441"
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <p className="text-xs text-ink-soft">
        Weekly statistics shown here are privatised with a Laplace
        differential-privacy mechanism before being returned by the server.
      </p>
    </div>
  );
}
