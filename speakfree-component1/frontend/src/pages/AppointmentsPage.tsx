/**
 * AppointmentsPage – patients / guardians request a session with a speech-language pathologist;
 * the admin confirms it (AdminAppointments). Shows the status of every request.
 */
import { useEffect, useState, type FormEvent } from "react";
import { CalendarCheck, CalendarClock, Loader2, MonitorSmartphone, Send, X } from "lucide-react";
import { api, type Appointment } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { COLORS, ErrorBox, Spinner } from "../components/ui";

export const APPT_STATUS: Record<Appointment["status"], { label: string; color: string }> = {
  pending: { label: "Waiting for confirmation", color: COLORS.warn },
  confirmed: { label: "Confirmed", color: COLORS.ok },
  declined: { label: "Not possible", color: COLORS.bad },
  cancelled: { label: "Cancelled", color: COLORS.muted },
};
export const TIME_LABEL = { morning: "Morning (8–12)", afternoon: "Afternoon (12–5)", evening: "Evening (5–8)" };
export const MODE_LABEL = { online: "Online video call", in_person: "In person" };

export function StatusPill({ status }: { status: Appointment["status"] }) {
  const s = APPT_STATUS[status];
  return (
    <span className="chip" style={{ background: `${s.color}1A`, color: COLORS.ink }}>
      <span className="h-2 w-2 rounded-full" style={{ background: s.color }} aria-hidden />{s.label}
    </span>
  );
}

const tomorrow = () => new Date(Date.now() + 86400000).toISOString().slice(0, 10);

export default function AppointmentsPage() {
  const { user, activePatient } = useAuth();
  const [items, setItems] = useState<Appointment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ preferred_date: tomorrow(), preferred_time: "morning" as Appointment["preferred_time"],
    mode: "online" as Appointment["mode"], reason: "" });
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  const load = () => api.appointments.mine().then(setItems).catch((e: Error) => setError(e.message));
  useEffect(() => { void load(); }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!activePatient) return;
    setBusy(true); setError(null); setSent(false);
    try {
      await api.appointments.create({ patient_id: activePatient.id, ...form, reason: form.reason.trim() });
      setForm({ ...form, reason: "" });
      setSent(true);
      await load();
    } catch (err) { setError((err as Error).message); } finally { setBusy(false); }
  }

  async function cancel(id: number) {
    try { await api.appointments.cancel(id); await load(); } catch (err) { setError((err as Error).message); }
  }

  if (!user) return null;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-extrabold tracking-tight">Appointments</h1>
        <p className="mt-1 text-sm text-ink-soft">Talk your results and therapy plan through with a speech-language pathologist.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        <section className="card p-6">
          <h2 className="flex items-center gap-2 text-[15px] font-bold"><CalendarClock size={18} className="text-navy" /> Request a session</h2>
          {!activePatient ? <p className="mt-3 text-sm muted">Add a patient first.</p> : (
            <form onSubmit={submit} className="mt-4 space-y-4">
              <p className="rounded-xl bg-lav-50 p-3 text-sm">For <b>{activePatient.full_name}</b> ({activePatient.id})</p>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block"><span className="label">Preferred date</span>
                  <input className="input" type="date" min={new Date().toISOString().slice(0, 10)} value={form.preferred_date}
                    onChange={(e) => setForm({ ...form, preferred_date: e.target.value })} required />
                </label>
                <label className="block"><span className="label">Time of day</span>
                  <select className="input" value={form.preferred_time} onChange={(e) => setForm({ ...form, preferred_time: e.target.value as Appointment["preferred_time"] })}>
                    {Object.entries(TIME_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
                  </select>
                </label>
              </div>
              <fieldset>
                <legend className="label">How would you like to meet?</legend>
                <div className="grid gap-2 sm:grid-cols-2">
                  {(Object.keys(MODE_LABEL) as Appointment["mode"][]).map((m) => (
                    <label key={m} className={`flex cursor-pointer items-center gap-2 rounded-xl border p-3 text-sm font-semibold ${form.mode === m ? "border-brand bg-brand-soft text-navy" : "border-line"}`}>
                      <input type="radio" name="mode" className="accent-[#1D4ED8]" checked={form.mode === m} onChange={() => setForm({ ...form, mode: m })} />
                      {m === "online" ? <MonitorSmartphone size={16} /> : <CalendarCheck size={16} />} {MODE_LABEL[m]}
                    </label>
                  ))}
                </div>
              </fieldset>
              <label className="block"><span className="label">What would you like to talk about?</span>
                <textarea className="input min-h-[96px]" value={form.reason} minLength={5} maxLength={1000} required
                  placeholder="e.g. I'd like to go through my screening results and my therapy plan."
                  onChange={(e) => setForm({ ...form, reason: e.target.value })} />
              </label>
              <ErrorBox message={error} />
              {sent && <p role="status" className="rounded-xl bg-ok-soft p-3 text-sm font-semibold text-ok">Request sent – we'll confirm a time with you soon.</p>}
              <button className="btn-primary w-full py-3" disabled={busy}>{busy ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />} Send request</button>
            </form>
          )}
        </section>

        <section className="card p-6">
          <h2 className="text-[15px] font-bold">Your requests</h2>
          {!items ? <Spinner className="h-32" /> : items.length === 0 ? (
            <p className="mt-3 text-sm muted">No appointment requests yet.</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {items.map((a) => (
                <li key={a.id} className="rounded-xl border border-line p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <StatusPill status={a.status} />
                    <span className="text-xs muted">requested {new Date(a.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="mt-2 text-sm font-semibold text-ink">
                    {a.status === "confirmed" && a.scheduled_at
                      ? new Date(a.scheduled_at).toLocaleString(undefined, { dateStyle: "full", timeStyle: "short" })
                      : `${new Date(`${a.preferred_date}T00:00:00`).toLocaleDateString(undefined, { dateStyle: "medium" })} · ${TIME_LABEL[a.preferred_time]}`}
                  </div>
                  <div className="text-xs muted">{a.patient_name} · {MODE_LABEL[a.mode]}</div>
                  <p className="mt-2 text-sm text-ink-soft">{a.reason}</p>
                  {a.admin_note && <p className="mt-2 rounded-lg bg-lav-50 p-2 text-sm"><b>Note from the clinic:</b> {a.admin_note}</p>}
                  {(a.status === "pending" || a.status === "confirmed") && (
                    <button className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-bad hover:underline" onClick={() => void cancel(a.id)}><X size={13} /> Cancel request</button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
