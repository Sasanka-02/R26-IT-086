/**
 * AdminAppointments – the clinic's inbox of appointment requests: confirm with a date-time or decline,
 * with a note the family sees.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CalendarClock, Check, Loader2, X } from "lucide-react";
import { api, type Appointment } from "../../api/client";
import { ErrorBox, Spinner } from "../../components/ui";
import { StatTile } from "../../components/charts";
import { MODE_LABEL, StatusPill, TIME_LABEL } from "../AppointmentsPage";

const FILTERS = ["pending", "confirmed", "declined", "cancelled", "all"] as const;

function DecisionForm({ a, onDone }: { a: Appointment; onDone: () => void }) {
  const [when, setWhen] = useState(`${a.preferred_date}T${a.preferred_time === "morning" ? "09:00" : a.preferred_time === "afternoon" ? "14:00" : "17:30"}`);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function decide(status: "confirmed" | "declined") {
    setBusy(true); setError(null);
    try {
      await api.appointments.decide(a.id, { status, scheduled_at: status === "confirmed" ? new Date(when).toISOString() : undefined, admin_note: note || undefined });
      onDone();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return (
    <div className="mt-3 grid gap-2 rounded-xl bg-canvas p-3 md:grid-cols-[auto_1fr_auto]">
      <input className="input py-2 text-sm" type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} aria-label="Confirmed date and time" />
      <input className="input py-2 text-sm" placeholder="Note for the family (meeting link, room…)" value={note} onChange={(e) => setNote(e.target.value)} />
      <div className="flex gap-2">
        <button className="btn-primary py-2" disabled={busy} onClick={() => void decide("confirmed")}>{busy ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />} Confirm</button>
        <button className="btn-ghost py-2" disabled={busy} onClick={() => void decide("declined")}><X size={14} /> Decline</button>
      </div>
      {error && <div className="md:col-span-3"><ErrorBox message={error} /></div>}
    </div>
  );
}

export default function AdminAppointments() {
  const [all, setAll] = useState<Appointment[] | null>(null);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("pending");
  const [error, setError] = useState<string | null>(null);
  const load = () => api.appointments.all().then(setAll).catch((e: Error) => setError(e.message));
  useEffect(() => { void load(); }, []);

  if (error) return <ErrorBox message={error} />;
  if (!all) return <Spinner />;
  const rows = filter === "all" ? all : all.filter((a) => a.status === filter);
  const count = (s: string) => all.filter((a) => a.status === s).length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-[28px] font-extrabold tracking-tight"><CalendarClock className="text-navy" /> Appointment requests</h1>
        <p className="text-sm text-ink-soft">Families ask for a session with a speech-language pathologist. Confirm a time or decline with a note.</p>
      </div>
      <section className="grid gap-4 sm:grid-cols-4">
        <StatTile label="Waiting" value={count("pending")} />
        <StatTile label="Confirmed" value={count("confirmed")} />
        <StatTile label="Declined" value={count("declined")} />
        <StatTile label="Cancelled by family" value={count("cancelled")} />
      </section>
      <nav className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button key={f} onClick={() => setFilter(f)}
            className={`rounded-xl px-4 py-2 text-sm font-semibold capitalize ${filter === f ? "bg-navy text-white shadow-nav" : "bg-white text-ink-soft hover:bg-lav-50"}`}>{f}</button>
        ))}
      </nav>
      {rows.length === 0 ? <div className="card p-8 text-center text-sm muted">No {filter === "all" ? "" : filter} requests.</div> : (
        <ul className="space-y-3">
          {rows.map((a) => (
            <li key={a.id} className="card p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <Link to={`/admin/patients/${a.patient_id}`} className="font-bold text-ink hover:text-brand">{a.patient_name}</Link>
                  <span className="text-sm muted"> · {a.patient_id} · requested by {a.requested_by} ({a.requested_by_role}, {a.requested_by_email})</span>
                  <div className="mt-1 text-sm text-ink">
                    Prefers {new Date(`${a.preferred_date}T00:00:00`).toLocaleDateString(undefined, { dateStyle: "medium" })} · {TIME_LABEL[a.preferred_time]} · {MODE_LABEL[a.mode]}
                  </div>
                </div>
                <StatusPill status={a.status} />
              </div>
              <p className="mt-2 text-sm text-ink-soft">“{a.reason}”</p>
              {a.scheduled_at && <p className="mt-2 text-sm font-semibold text-ok">Scheduled {new Date(a.scheduled_at).toLocaleString()}</p>}
              {a.admin_note && <p className="mt-1 text-sm muted">Note: {a.admin_note}</p>}
              {a.status === "pending" && <DecisionForm a={a} onDone={() => void load()} />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
