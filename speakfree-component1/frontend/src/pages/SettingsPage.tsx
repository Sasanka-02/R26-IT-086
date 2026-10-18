/**
 * SettingsPage – account profile, password, patients on this account and privacy information.
 */
import { useState, type FormEvent } from "react";
import { CheckCircle2, KeyRound, Loader2, LogOut, ShieldCheck, UserRound, Users } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { Card, ErrorBox } from "../components/ui";

const ROLE_LABEL: Record<string, string> = {
  patient: "Patient (self)", guardian: "Parent / guardian", clinician: "Clinician", admin: "Administrator",
};

function Saved({ text }: { text: string | null }) {
  if (!text) return null;
  return <p role="status" className="flex items-center gap-1.5 text-sm font-semibold text-ok"><CheckCircle2 size={16} /> {text}</p>;
}

export default function SettingsPage() {
  const { user, refresh, logout } = useAuth();
  const [name, setName] = useState(user?.full_name ?? "");
  const [nameMsg, setNameMsg] = useState<string | null>(null);
  const [nameErr, setNameErr] = useState<string | null>(null);
  const [busyName, setBusyName] = useState(false);
  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });
  const [pwMsg, setPwMsg] = useState<string | null>(null);
  const [pwErr, setPwErr] = useState<string | null>(null);
  const [busyPw, setBusyPw] = useState(false);
  if (!user) return null;
  const isAdmin = user.role === "admin";

  async function saveName(e: FormEvent) {
    e.preventDefault();
    setNameMsg(null); setNameErr(null); setBusyName(true);
    try {
      await api.updateMe(name.trim());
      await refresh();
      setNameMsg("Name updated");
    } catch (err) { setNameErr((err as Error).message); } finally { setBusyName(false); }
  }

  async function savePassword(e: FormEvent) {
    e.preventDefault();
    setPwMsg(null); setPwErr(null);
    if (pw.next.length < 8) return setPwErr("The new password needs at least 8 characters.");
    if (pw.next !== pw.confirm) return setPwErr("The new passwords do not match.");
    setBusyPw(true);
    try {
      await api.changePassword(pw.current, pw.next);
      setPw({ current: "", next: "", confirm: "" });
      setPwMsg("Password changed");
    } catch (err) { setPwErr((err as Error).message); } finally { setBusyPw(false); }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-extrabold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-ink-soft">Manage your account, password and privacy.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Profile" icon={<UserRound size={18} className="text-navy" />}>
          <dl className="mb-4 grid grid-cols-2 gap-3 text-sm">
            <div><dt className="text-xs muted">E-mail</dt><dd className="truncate font-semibold">{user.email}</dd></div>
            <div><dt className="text-xs muted">Account type</dt><dd className="font-semibold">{ROLE_LABEL[user.role]}</dd></div>
          </dl>
          {isAdmin ? (
            <p className="rounded-xl bg-lav-50 p-3 text-sm text-ink-soft">The administrator account is configured on the server (backend/config.py).</p>
          ) : (
            <form onSubmit={saveName} className="space-y-3">
              <label className="block"><span className="label">Full name</span>
                <input className="input" value={name} onChange={(e) => setName(e.target.value)} minLength={2} maxLength={120} required />
              </label>
              <ErrorBox message={nameErr} />
              <div className="flex items-center gap-3">
                <button className="btn-primary" disabled={busyName || name.trim() === user.full_name}>{busyName && <Loader2 size={15} className="animate-spin" />} Save</button>
                <Saved text={nameMsg} />
              </div>
            </form>
          )}
        </Card>

        <Card title="Password" icon={<KeyRound size={18} className="text-navy" />}>
          {isAdmin ? (
            <p className="rounded-xl bg-lav-50 p-3 text-sm text-ink-soft">Change the administrator password in backend/config.py and restart the server.</p>
          ) : (
            <form onSubmit={savePassword} className="space-y-3">
              <label className="block"><span className="label">Current password</span>
                <input className="input" type="password" autoComplete="current-password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} required />
              </label>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block"><span className="label">New password</span>
                  <input className="input" type="password" autoComplete="new-password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} required />
                </label>
                <label className="block"><span className="label">Confirm new password</span>
                  <input className="input" type="password" autoComplete="new-password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} required />
                </label>
              </div>
              <ErrorBox message={pwErr} />
              <div className="flex items-center gap-3">
                <button className="btn-primary" disabled={busyPw}>{busyPw && <Loader2 size={15} className="animate-spin" />} Change password</button>
                <Saved text={pwMsg} />
              </div>
            </form>
          )}
        </Card>

        {!isAdmin && (
          <Card title="Patients on this account" icon={<Users size={18} className="text-navy" />}>
            {user.patients.length === 0 ? <p className="text-sm muted">No patients yet – use “Add patient” in the top bar.</p> : (
              <ul className="divide-y divide-line">
                {user.patients.map((p) => (
                  <li key={p.id} className="flex items-center justify-between py-2.5 text-sm">
                    <span><b className="text-ink">{p.full_name}</b> <span className="muted">· {p.id}</span></span>
                    <span className="muted">Age {p.age ?? "not set"}{p.age_bracket ? ` · ${p.age_bracket.label}` : ""}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        )}

        <Card title="Privacy" icon={<ShieldCheck size={18} className="text-navy" />}>
          <ul className="space-y-2 text-sm text-ink-soft">
            <li>• Screening recordings are deleted from the server right after analysis. Only scores and transcripts are kept.</li>
            <li>• Therapy exercises run in your browser – only practice numbers (time, pauses, speed) and your rating are saved.</li>
            <li>• Your results are linked to a pseudonymous patient ID. Only the SpeakFree clinical team can review results across patients.</li>
          </ul>
          <button className="btn-ghost mt-4" onClick={logout}><LogOut size={15} /> Sign out</button>
        </Card>
      </div>
    </div>
  );
}
