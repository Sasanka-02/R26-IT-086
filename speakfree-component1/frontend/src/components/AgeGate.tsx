/**
 * AgeGate – one-time "How old are you?" screen for accounts created before age was collected.
 * Shown instead of the page content until the active patient has an age; saved with
 * PUT /api/v1/auth/me/age, then the plan, tasks and look follow the new age bracket.
 */
import { useState, type FormEvent } from "react";
import { Cake, CheckCircle2, Loader2, XCircle } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { ADULT_AGE, ageError, bracketForAge, MAX_AGE, MIN_AGE } from "../utils/age";
import type { Patient } from "../types";
import { ErrorBox } from "./ui";

export default function AgeGate({ patient }: { patient: Patient }) {
  const { user, refresh } = useAuth();
  const [value, setValue] = useState("");
  const [guardianConsent, setGuardianConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const self = patient.is_self || user?.role === "patient";
  const age = value.trim() === "" ? null : Number(value);
  const problem = age === null ? null : ageError(age);
  const bracket = age !== null && !problem ? bracketForAge(age) : null;
  const needsGuardian = bracket !== null && age !== null && age < ADULT_AGE;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const msg = ageError(age);
    if (msg) return setError(msg);
    if (needsGuardian && !guardianConsent) return setError("A parent or guardian must agree to this account for anyone under 18.");
    setBusy(true);
    try {
      await api.setMyAge(age!, needsGuardian && guardianConsent, patient.id);
      await refresh();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      <form onSubmit={submit} className="card animate-step space-y-5 p-8 text-center">
        <span className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-sun-soft text-sun"><Cake size={32} /></span>
        <div>
          <h1 className="text-2xl font-extrabold">{self ? "How old are you?" : `How old is ${patient.full_name.split(" ")[0]}?`}</h1>
          <p className="mt-1 text-sm text-ink-soft">
            We plan practice by age, so reading passages, pictures and conversations suit {self ? "you" : "them"}. You only need to tell us once.
          </p>
        </div>
        <ErrorBox message={error} />
        <input className="input mx-auto max-w-[160px] text-center text-3xl font-extrabold" type="number" inputMode="numeric" autoFocus
          min={MIN_AGE} max={MAX_AGE} step={1} value={value} placeholder="Age" aria-label="Age in years"
          onChange={(e) => { setValue(e.target.value); setError(null); }} required />
        {age !== null && (
          <div className={`flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm ${bracket ? "bg-ok-soft text-ok" : "bg-bad-soft text-bad"}`} role="status">
            {bracket ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
            {bracket ? <span>Level {bracket.id} · {bracket.label}</span> : <span>{problem}</span>}
          </div>
        )}
        {needsGuardian && (
          <label className="flex cursor-pointer items-start gap-3 rounded-xl border-2 border-warn/40 bg-warn-soft p-4 text-left">
            <input type="checkbox" className="mt-1 h-5 w-5 accent-[#1E3A8A]" checked={guardianConsent} onChange={(e) => setGuardianConsent(e.target.checked)} required />
            <span className="text-sm text-ink"><b>A parent or guardian has agreed to this account</b>
              <span className="block text-xs text-ink-soft">Required for anyone under {ADULT_AGE}.</span></span>
          </label>
        )}
        <button className="btn-primary w-full py-3 text-base" disabled={busy || !bracket || (needsGuardian && !guardianConsent)}>
          {busy && <Loader2 className="animate-spin" size={18} />} Save my age
        </button>
      </form>
    </div>
  );
}
