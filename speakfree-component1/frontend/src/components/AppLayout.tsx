/**
 * AppLayout – application shell matching the SpeakFree mock-up:
 *   header (menu · logo · patient selector · notifications · avatar) + white sidebar + routed content.
 */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Bell,
  BookOpen,
  Bot,
  Brain,
  Workflow,
  CalendarDays,
  ChevronDown,
  ClipboardList,
  FileText,
  FlaskConical,
  Headphones,
  HeartPulse,
  Home,
  Info,
  Library,
  Loader2,
  LogOut,
  Menu,
  Plus,
  Settings,
  TrendingUp,
  Users,
  X,
} from "lucide-react";
import { api } from "../api/client";
import AgeGate from "./AgeGate";
import { useAuth } from "../context/AuthContext";
import { AssessmentProvider, useAssessment } from "../context/AssessmentContext";
import type { Role } from "../types";
import { calculateAge, MAX_AGE, MIN_AGE, TOO_YOUNG_MESSAGE } from "../utils/age";
import SiteFooter from "./SiteFooter";
import { ErrorBox, Logo } from "./ui";

// roles: who sees the link (omitted = every role except admin)
const NAV: { to: string; label: string; icon: ReactNode; roles?: Role[] }[] = [
  { to: "/admin/pipeline", label: "Analysis Pipeline", icon: <Workflow size={18} />, roles: ["admin"] },
  { to: "/admin/patients", label: "Patients", icon: <Users size={18} />, roles: ["admin"] },
  { to: "/admin/appointments", label: "Appointments", icon: <CalendarDays size={18} />, roles: ["admin"] },
  { to: "/admin/models", label: "Models & Methods", icon: <Brain size={18} />, roles: ["admin"] },
  { to: "/admin/evidence", label: "Evidence & Validation", icon: <FlaskConical size={18} />, roles: ["admin"] },
  { to: "/", label: "Dashboard", icon: <Home size={18} /> },
  { to: "/assessment", label: "Assessment Tasks", icon: <ClipboardList size={18} /> },
  { to: "/progress", label: "My Progress", icon: <TrendingUp size={18} /> },
  { to: "/therapy-plan", label: "Therapy Plan", icon: <HeartPulse size={18} /> },
  { to: "/therapy/recordings", label: "My Recordings", icon: <Headphones size={18} /> },
  { to: "/therapy/assistant", label: "AI Assistant", icon: <Bot size={18} /> },
  { to: "/reports", label: "Reports", icon: <FileText size={18} /> },
  { to: "/resources", label: "Resources", icon: <BookOpen size={18} /> },
  { to: "/appointments", label: "Appointments", icon: <CalendarDays size={18} /> },
  { to: "/task-library", label: "Task Library", icon: <Library size={18} />, roles: ["clinician", "admin"] },
  { to: "/settings", label: "Settings", icon: <Settings size={18} />, roles: ["patient", "guardian", "clinician", "admin"] },
];

function useClickOutside(onOutside: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) onOutside(); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [onOutside]);
  return ref;
}

// =========================================================================== sidebar
function Sidebar({ open, collapsed, onClose }: { open: boolean; collapsed: boolean; onClose: () => void }) {
  const { user } = useAuth();
  const role = user?.role ?? "patient";
  const items = NAV.filter((item) => (item.roles ? item.roles.includes(role) : role !== "admin"));
  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-ink/30 lg:hidden" onClick={onClose} aria-hidden />}
      <aside
        className={`fixed bottom-0 left-0 top-0 z-40 flex w-64 flex-col border-r border-line bg-white px-4 pb-4 pt-4 transition-transform lg:top-[76px] lg:pt-5 ${collapsed ? "lg:-translate-x-full" : "lg:translate-x-0"} ${open ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="mb-6 flex items-center justify-between lg:hidden">
          <Logo subtitle={false} />
          <button className="text-ink-muted" onClick={onClose} aria-label="Close menu"><X size={20} /></button>
        </div>
        <nav className="flex-1 space-y-1">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition ${isActive ? "bg-navy text-white shadow-nav" : "text-ink-soft hover:bg-canvas hover:text-ink"}`
              }
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-4 rounded-2xl bg-lav-50 p-4">
          <div className="flex items-center gap-2 text-sm font-bold text-ink"><Info size={18} className="text-navy" /> Need help?</div>
          <p className="mt-1.5 text-xs leading-relaxed text-ink-soft">Our support team is here to help you.</p>
          <a href="mailto:support@speakfree.lk" className="mt-3 inline-flex rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-navy shadow-sm hover:bg-lav-100">
            Contact Support
          </a>
        </div>
      </aside>
    </>
  );
}

// =========================================================================== header widgets
function AddPatientModal({ onClose }: { onClose: () => void }) {
  const { refresh, setActivePatientId } = useAuth();
  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const age = calculateAge(dob);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (age === null || age < MIN_AGE || age > MAX_AGE) return setError(age !== null && age < MIN_AGE ? TOO_YOUNG_MESSAGE : `Patient must be ${MIN_AGE}–${MAX_AGE} years old.`);
    setBusy(true);
    try {
      const p = await api.createPatient(name.trim(), dob);
      await refresh();
      setActivePatientId(p.id);
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/40 px-4" role="dialog" aria-modal>
      <form onSubmit={submit} className="card w-full max-w-md space-y-4 p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">Add patient</h2>
          <button type="button" onClick={onClose} className="text-ink-muted" aria-label="Close"><X size={18} /></button>
        </div>
        <ErrorBox message={error} />
        <label className="block"><span className="label">Full name</span>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} required minLength={2} />
        </label>
        <label className="block"><span className="label">Date of birth</span>
          <input className="input" type="date" value={dob} max={new Date().toISOString().slice(0, 10)} onChange={(e) => setDob(e.target.value)} required />
        </label>
        {age !== null && <p className="text-sm muted">Calculated age: <b className="text-ink">{age}</b></p>}
        <button className="btn-primary w-full" disabled={busy}>{busy && <Loader2 className="animate-spin" size={16} />} Save patient</button>
      </form>
    </div>
  );
}

function PatientSelector() {
  const { user, activePatient, setActivePatientId } = useAuth();
  const [adding, setAdding] = useState(false);
  if (!user) return null;
  const canAdd = user.role !== "patient";
  return (
    <div className="flex items-center gap-2">
      {user.patients.length > 0 && (
        <label className="relative flex items-center rounded-xl bg-lav-100 pl-4 pr-9 text-sm font-medium text-ink">
          <span className="hidden whitespace-nowrap sm:inline">Patient:&nbsp;</span>
          <select
            className="cursor-pointer appearance-none bg-transparent py-2.5 font-semibold focus:outline-none"
            value={activePatient?.id ?? ""}
            onChange={(e) => setActivePatientId(e.target.value)}
            aria-label="Active patient"
          >
            {user.patients.map((p) => <option key={p.id} value={p.id}>{p.full_name}</option>)}
          </select>
          <ChevronDown size={16} className="pointer-events-none absolute right-3 text-ink-soft" />
        </label>
      )}
      {canAdd && (
        <button className="btn-lav px-3 py-2.5" onClick={() => setAdding(true)} title="Add patient">
          <Plus size={16} /> <span className="hidden md:inline">Add patient</span>
        </button>
      )}
      {adding && <AddPatientModal onClose={() => setAdding(false)} />}
    </div>
  );
}

function Notifications() {
  const { session, completedCount, required } = useAssessment();
  const [open, setOpen] = useState(false);
  const ref = useClickOutside(() => setOpen(false));
  const pending = session ? Object.values(session.recordings).filter((r) => !r.analysisId).length : 0;
  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((v) => !v)} className="relative grid h-10 w-10 place-items-center rounded-full text-ink-soft hover:bg-canvas" aria-label="Notifications">
        <Bell size={21} />
        {pending > 0 && <span className="absolute right-2 top-1.5 h-2.5 w-2.5 rounded-full bg-sun ring-2 ring-white" />}
      </button>
      {open && (
        <div className="card absolute right-0 top-12 z-50 w-72 p-4 text-sm shadow-lift">
          <div className="mb-2 font-bold">Notifications</div>
          {pending > 0 ? (
            <Link to="/assessment" onClick={() => setOpen(false)} className="block rounded-xl bg-sun-soft p-3 text-ink hover:brightness-95">
              <b>{pending} recording{pending === 1 ? "" : "s"}</b> waiting for analysis ({completedCount}/{required.length} tasks recorded).
            </Link>
          ) : (
            <p className="muted">You're all caught up.</p>
          )}
        </div>
      )}
    </div>
  );
}

function AvatarMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useClickOutside(() => setOpen(false));
  if (!user) return null;
  const initials = user.full_name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]!.toUpperCase()).join("");
  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((v) => !v)} className="grid h-11 w-11 place-items-center rounded-full bg-lav-100 text-sm font-bold text-navy hover:bg-lav-200" aria-label="Account menu">
        {initials}
      </button>
      {open && (
        <div className="card absolute right-0 top-12 z-50 mt-1 w-64 p-4 shadow-lift">
          <div className="truncate font-semibold">{user.full_name}</div>
          <div className="truncate text-xs capitalize muted">{user.role} · {user.email}</div>
          <button onClick={logout} className="btn-ghost mt-3 w-full py-2"><LogOut size={15} /> Sign out</button>
        </div>
      )}
    </div>
  );
}

// =========================================================================== shell
function Shell() {
  const { user, activePatient } = useAuth();
  // accounts created before age was collected answer "How old are you?" once (therapists are never asked)
  const needsAge = !!activePatient && activePatient.age === null && (user?.role === "patient" || user?.role === "guardian");
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0); // block body: newer browsers return a Promise here, which must not become the effect cleanup
  }, [pathname]);
  return (
    <div className="min-h-screen">
      <header className="fixed inset-x-0 top-0 z-30 flex h-[76px] items-center justify-between gap-3 border-b border-line bg-white/95 px-4 backdrop-blur sm:px-6">
        <div className="flex items-center gap-4">
          <button className="text-ink lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu"><Menu size={24} /></button>
          <button className="hidden text-ink lg:block" onClick={() => setCollapsed((c) => !c)} aria-label="Toggle menu"><Menu size={24} /></button>
          <div className="hidden sm:block"><Logo /></div>
          <div className="sm:hidden"><Logo subtitle={false} /></div>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          {user?.role === "admin" ? (
            <span className="chip bg-navy text-white">Administrator</span>
          ) : (
            <>
              <PatientSelector />
              <Notifications />
            </>
          )}
          <AvatarMenu />
        </div>
      </header>
      <Sidebar open={open} collapsed={collapsed} onClose={() => setOpen(false)} />

      <div className={`pt-[76px] transition-[padding] ${collapsed ? "" : "lg:pl-64"}`}>
        <main className="mx-auto max-w-[1180px] px-4 py-7 sm:px-8">
          {needsAge ? <AgeGate patient={activePatient!} /> : <Outlet />}
        </main>
        <div className="mx-auto max-w-[1180px] px-4 sm:px-8"><SiteFooter variant="compact" /></div>
      </div>
    </div>
  );
}

export default function AppLayout() {
  return (
    <AssessmentProvider>
      <Shell />
    </AssessmentProvider>
  );
}

export function PlaceholderPage({ title, owner, description }: { title: string; owner: string; description: string }) {
  return (
    <div className="card p-8">
      <h1 className="text-2xl font-extrabold">{title}</h1>
      <p className="mt-2 muted">{description}</p>
      <p className="chip mt-4 bg-lav-100 text-lav-600">Provided by {owner}</p>
    </div>
  );
}
