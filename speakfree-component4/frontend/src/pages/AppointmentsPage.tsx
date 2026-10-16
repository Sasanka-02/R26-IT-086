import { FormEvent, useCallback, useEffect, useState } from "react";
import { CalendarCheck, CalendarPlus, MapPin, Video, X } from "lucide-react";
import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";
import { errorMessage } from "../api/client";
import { Appointment } from "../types/therapy";
import { StudentRow } from "../types/therapist";
import {
  bookAppointment,
  cancelAppointment,
  createAppointmentSlot,
  getStudentAppointments,
  getTherapistAppointments,
} from "../therapy/therapyApi";
import { getStudents } from "../therapist/therapistApi";

function dayLabel(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });
}

function timeLabel(a: Appointment) {
  const start = new Date(a.start);
  const end = new Date(start.getTime() + a.minutes * 60000);
  const t = (d: Date) => d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  return `${t(start)} – ${t(end)}`;
}

function byDay(items: Appointment[]) {
  const groups: { day: string; items: Appointment[] }[] = [];
  for (const a of items) {
    const day = dayLabel(a.start);
    const group = groups.find((g) => g.day === day);
    if (group) group.items.push(a);
    else groups.push({ day, items: [a] });
  }
  return groups;
}

function ModeTag({ mode }: { mode: Appointment["mode"] }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-paper px-2 py-0.5 text-xs text-ink-soft">
      {mode === "online" ? <Video size={12} /> : <MapPin size={12} />}
      {mode === "online" ? "Online" : "At the clinic"}
    </span>
  );
}

function StudentAppointments() {
  const [data, setData] = useState<{ booked: Appointment[]; open: Appointment[] } | null>(null);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  const load = useCallback(() => {
    getStudentAppointments()
      .then(setData)
      .catch(() => setMessage({ ok: false, text: "Couldn't load sessions." }));
  }, []);
  useEffect(load, [load]);

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    setMessage(null);
    try {
      await fn();
      setMessage({ ok: true, text: ok });
    } catch (err) {
      setMessage({ ok: false, text: errorMessage(err, "That didn't work. Please try again.") });
    }
    load();
  };

  return (
    <>
      {message && (
        <p role="status" className={`rounded-lg px-3 py-2 text-sm ${message.ok ? "bg-teal-50 text-teal-800" : "bg-red-50 text-red-700"}`}>
          {message.text}
        </p>
      )}
      <section className="rounded-2xl border border-snow/5 bg-white p-5">
        <h2 className="flex items-center gap-2 text-base font-semibold text-ink">
          <CalendarCheck size={18} className="text-teal-600" /> Your sessions
        </h2>
        {data && data.booked.length === 0 && <p className="mt-2 text-sm text-ink-soft">No sessions booked yet.</p>}
        <ul className="mt-3 space-y-2">
          {data?.booked.map((a) => (
            <li key={a.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-teal-50/60 px-4 py-3 text-sm">
              <span>
                <span className="block font-semibold text-ink">{dayLabel(a.start)}</span>
                <span className="text-ink-soft">
                  {timeLabel(a)} · with {a.therapist_name} · <ModeTag mode={a.mode} />
                </span>
              </span>
              <button
                onClick={() => act(() => cancelAppointment(a.id), "Booking cancelled.")}
                className="flex items-center gap-1 rounded-full border border-red-200 px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-50"
              >
                <X size={13} /> Cancel
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-2xl border border-snow/5 bg-white p-5">
        <h2 className="text-base font-semibold text-ink">Book a session</h2>
        <p className="mt-0.5 text-sm text-ink-soft">Times your therapist has made available, shown in your local time.</p>
        {data && data.open.length === 0 && (
          <p className="mt-3 text-sm text-ink-soft">No open times right now — send your therapist a message.</p>
        )}
        <div className="mt-3 space-y-4">
          {data &&
            byDay(data.open).map((g) => (
              <div key={g.day}>
                <p className="mb-2 text-sm font-semibold text-ink">{g.day}</p>
                <div className="flex flex-wrap gap-2">
                  {g.items.map((a) => (
                    <button
                      key={a.id}
                      onClick={() => act(() => bookAppointment(a.id), `Booked: ${dayLabel(a.start)}, ${timeLabel(a)}.`)}
                      className="rounded-xl border border-teal-100 px-3 py-2 text-left text-sm hover:border-teal-400 hover:bg-teal-50/60"
                    >
                      <span className="block font-medium text-ink">{timeLabel(a)}</span>
                      <span className="text-xs text-ink-soft">
                        {a.therapist_name} · {a.mode === "online" ? "Online" : "Clinic"}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
        </div>
      </section>
    </>
  );
}

function TherapistAppointments() {
  const [sessions, setSessions] = useState<Appointment[] | null>(null);
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [date, setDate] = useState(() => new Date(Date.now() + 86400000).toISOString().slice(0, 10));
  const [time, setTime] = useState("09:00");
  const [minutes, setMinutes] = useState(30);
  const [mode, setMode] = useState<"clinic" | "online">("clinic");
  const [student, setStudent] = useState("");
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  const load = useCallback(() => {
    getTherapistAppointments()
      .then((d) => setSessions(d.sessions))
      .catch(() => setMessage({ ok: false, text: "Couldn't load the calendar." }));
  }, []);
  useEffect(() => {
    load();
    getStudents().then(setStudents).catch(() => {});
  }, [load]);

  const add = async (e: FormEvent) => {
    e.preventDefault();
    setMessage(null);
    try {
      // The browser's local time, sent with its timezone offset.
      const start = new Date(`${date}T${time}`);
      await createAppointmentSlot({ start: start.toISOString(), minutes, mode, student: student || null });
      setMessage({ ok: true, text: student ? "Session booked for the student." : "Open slot added." });
      setStudent("");
    } catch (err) {
      setMessage({ ok: false, text: errorMessage(err, "Couldn't add the session.") });
    }
    load();
  };

  const cancel = async (a: Appointment) => {
    try {
      await cancelAppointment(a.id);
      setMessage({ ok: true, text: a.student ? "Booking cancelled — the slot is open again." : "Open slot removed." });
    } catch (err) {
      setMessage({ ok: false, text: errorMessage(err, "Couldn't cancel.") });
    }
    load();
  };

  return (
    <>
      <form onSubmit={add} className="rounded-2xl border border-snow/5 bg-white p-5">
        <h2 className="flex items-center gap-2 text-base font-semibold text-ink">
          <CalendarPlus size={18} className="text-teal-600" /> Add a session
        </h2>
        <p className="mt-0.5 text-sm text-ink-soft">
          Leave “Book for” empty to publish an open slot students can book; choose a student to book them straight in.
        </p>
        <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-5">
          <label className="text-ink-soft">
            Date
            <input type="date" required value={date} min={new Date().toISOString().slice(0, 10)} onChange={(e) => setDate(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-teal-100 bg-white px-2 py-1.5 text-ink" />
          </label>
          <label className="text-ink-soft">
            Time
            <input type="time" required value={time} onChange={(e) => setTime(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-teal-100 bg-white px-2 py-1.5 text-ink" />
          </label>
          <label className="text-ink-soft">
            Length
            <select value={minutes} onChange={(e) => setMinutes(Number(e.target.value))}
              className="mt-1 block w-full rounded-lg border border-teal-100 bg-white px-2 py-1.5 text-ink">
              {[20, 30, 45, 60].map((m) => <option key={m} value={m}>{m} min</option>)}
            </select>
          </label>
          <label className="text-ink-soft">
            Where
            <select value={mode} onChange={(e) => setMode(e.target.value as "clinic" | "online")}
              className="mt-1 block w-full rounded-lg border border-teal-100 bg-white px-2 py-1.5 text-ink">
              <option value="clinic">At the clinic</option>
              <option value="online">Online</option>
            </select>
          </label>
          <label className="text-ink-soft">
            Book for (optional)
            <select value={student} onChange={(e) => setStudent(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-teal-100 bg-white px-2 py-1.5 text-ink">
              <option value="">Open slot</option>
              {students.map((s) => <option key={s.email} value={s.email}>{s.name}</option>)}
            </select>
          </label>
        </div>
        <button className="mt-4 rounded-full bg-teal-600 px-5 py-2 text-sm font-semibold text-white hover:bg-teal-700">
          Add to calendar
        </button>
      </form>

      {message && (
        <p role="status" className={`rounded-lg px-3 py-2 text-sm ${message.ok ? "bg-teal-50 text-teal-800" : "bg-red-50 text-red-700"}`}>
          {message.text}
        </p>
      )}

      <section className="rounded-2xl border border-snow/5 bg-white p-5">
        <h2 className="text-base font-semibold text-ink">Upcoming sessions</h2>
        {sessions && sessions.length === 0 && <p className="mt-2 text-sm text-ink-soft">Nothing in the calendar yet.</p>}
        <div className="mt-3 space-y-4">
          {sessions &&
            byDay(sessions).map((g) => (
              <div key={g.day}>
                <p className="mb-2 text-sm font-semibold text-ink">{g.day}</p>
                <ul className="space-y-1.5">
                  {g.items.map((a) => (
                    <li key={a.id} className={`flex flex-wrap items-center justify-between gap-2 rounded-xl px-4 py-2.5 text-sm ${a.student ? "bg-teal-50/60" : "bg-paper"}`}>
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="font-medium tabular-nums text-ink">{timeLabel(a)}</span>
                        <span className={a.student ? "font-medium text-teal-700" : "text-ink-soft"}>
                          {a.student ? a.student_name : "Open — not booked"}
                        </span>
                        <ModeTag mode={a.mode} />
                        <span className="text-xs text-ink-soft">{a.therapist_name}</span>
                      </span>
                      <button onClick={() => cancel(a)} className="rounded-full border border-red-200 px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-50">
                        {a.student ? "Cancel booking" : "Remove slot"}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
        </div>
      </section>
    </>
  );
}

export default function AppointmentsPage() {
  const { user } = useAuth();
  const therapist = user?.role === "therapist";
  return (
    <AppShell>
      <main className="mx-auto max-w-4xl space-y-5">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">{therapist ? "Session calendar" : "Appointments"}</h1>
          <p className="mt-1 text-sm text-ink-soft">
            {therapist
              ? "Publish times students can book, or book a session for a student."
              : "Book a session with your therapist, or cancel one you can't make."}
          </p>
        </div>
        {therapist ? <TherapistAppointments /> : <StudentAppointments />}
      </main>
    </AppShell>
  );
}
