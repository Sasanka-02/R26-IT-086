/**
 * AdminPatients – patient directory for the admin account.
 * Columns: patient name, last session date, total sessions, latest screening risk level.
 * Controls: search by name / ID / account e-mail, filter by risk level, sort. Row click → patient profile.
 */
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronRight, Search, Users } from "lucide-react";
import { api } from "../../api/client";
import { ErrorBox, RiskBadge, Spinner } from "../../components/ui";
import type { AdminPatientRow } from "../../types";

type RiskFilter = "all" | "1" | "2" | "3" | "4" | "none";
type SortKey = "name" | "recent" | "oldest" | "risk" | "sessions";

const fmtDate = (iso: string | null) => (iso ? new Date(iso).toLocaleString() : "-");

export default function AdminPatients() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<AdminPatientRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [risk, setRisk] = useState<RiskFilter>("all");
  const [sort, setSort] = useState<SortKey>("recent");

  useEffect(() => {
    api.admin.patients().then(setRows).catch((e: Error) => setError(e.message));
  }, []);

  const shown = useMemo(() => {
    if (!rows) return [];
    const q = query.trim().toLowerCase();
    const filtered = rows.filter((r) => {
      if (q && ![r.full_name, r.id, r.owner_email, r.owner_name].some((v) => v.toLowerCase().includes(q))) return false;
      if (risk === "none") return r.latest_severity_hint === null;
      if (risk !== "all") return r.latest_severity_hint === Number(risk);
      return true;
    });
    const time = (r: AdminPatientRow) => (r.last_session_at ? new Date(r.last_session_at).getTime() : 0);
    return [...filtered].sort((a, b) => {
      switch (sort) {
        case "name": return a.full_name.localeCompare(b.full_name);
        case "recent": return time(b) - time(a) || a.full_name.localeCompare(b.full_name);
        case "oldest": return (time(a) || Infinity) - (time(b) || Infinity);
        case "risk": return (b.latest_severity_hint ?? 0) - (a.latest_severity_hint ?? 0) || time(b) - time(a);
        case "sessions": return b.total_sessions - a.total_sessions;
      }
    });
  }, [rows, query, risk, sort]);

  const counts = useMemo(() => {
    const c = { total: rows?.length ?? 0, screened: 0, concern: 0 };
    for (const r of rows ?? []) {
      if (r.total_sessions) c.screened++;
      if ((r.latest_severity_hint ?? 0) >= 3) c.concern++;
    }
    return c;
  }, [rows]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-[28px] font-extrabold tracking-tight"><Users size={26} className="text-navy" /> Patients</h1>
        <p className="mt-1 text-sm text-ink-soft">Every registered patient. Open a patient to see their profile and full screening history.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {[["Registered patients", counts.total], ["Screened at least once", counts.screened], ["Latest result: moderate or significant concern", counts.concern]].map(([label, v]) => (
          <div key={label} className="card p-4">
            <div className="text-xs font-semibold uppercase tracking-wide muted">{label}</div>
            <div className="mt-1 text-2xl font-extrabold text-ink">{rows ? v : "…"}</div>
          </div>
        ))}
      </div>

      <div className="card p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          <label className="relative flex-1">
            <span className="sr-only">Search patients</span>
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted" />
            <input className="input pl-9" placeholder="Search by name, patient ID or account e-mail" value={query} onChange={(e) => setQuery(e.target.value)} />
          </label>
          <label className="flex items-center gap-2 text-sm text-ink-soft">
            Risk
            <select className="input w-auto py-2" value={risk} onChange={(e) => setRisk(e.target.value as RiskFilter)}>
              <option value="all">All</option>
              <option value="4">Level 4 – significant concern</option>
              <option value="3">Level 3 – moderate concern</option>
              <option value="2">Level 2 – mild concern</option>
              <option value="1">Level 1 – typical range</option>
              <option value="none">Not screened yet</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-ink-soft">
            Sort
            <select className="input w-auto py-2" value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
              <option value="recent">Last session – newest</option>
              <option value="oldest">Last session – oldest</option>
              <option value="risk">Risk – highest first</option>
              <option value="sessions">Most sessions</option>
              <option value="name">Name A–Z</option>
            </select>
          </label>
        </div>
      </div>

      <ErrorBox message={error} />
      {!rows && !error ? <Spinner /> : rows && (
        <div className="card overflow-x-auto p-0">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="border-b border-line bg-canvas/60 text-left text-xs uppercase tracking-wide muted">
              <tr>
                <th className="px-5 py-3 font-semibold">Patient name</th>
                <th className="px-5 py-3 font-semibold">Last session</th>
                <th className="px-5 py-3 text-right font-semibold">Total sessions</th>
                <th className="px-5 py-3 font-semibold">Latest screening risk</th>
                <th className="w-8" />
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {shown.map((r) => (
                <tr key={r.id} tabIndex={0} role="link" aria-label={`Open ${r.full_name}`}
                  onClick={() => navigate(`/admin/patients/${r.id}`)}
                  onKeyDown={(e) => { if (e.key === "Enter") navigate(`/admin/patients/${r.id}`); }}
                  className="cursor-pointer transition hover:bg-lav-50 focus:bg-lav-50 focus:outline-none">
                  <td className="px-5 py-3">
                    <div className="font-semibold text-ink">{r.full_name}</div>
                    <div className="text-xs muted">{r.id} · age {r.age ?? "not set"}{r.age_bracket ? ` · bracket ${r.age_bracket.id} (${r.age_bracket.label})` : ""}{r.age_bracket_override ? ` · pinned to level ${r.age_bracket_override}` : ""}</div>
                  </td>
                  <td className="px-5 py-3 text-ink-soft">{fmtDate(r.last_session_at)}</td>
                  <td className="px-5 py-3 text-right font-mono">{r.total_sessions}</td>
                  <td className="px-5 py-3"><RiskBadge hint={r.latest_severity_hint} label={r.latest_label} /></td>
                  <td className="pr-4 text-ink-muted"><ChevronRight size={18} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          {shown.length === 0 && <p className="p-8 text-center text-sm muted">No patients match these filters.</p>}
        </div>
      )}
    </div>
  );
}
