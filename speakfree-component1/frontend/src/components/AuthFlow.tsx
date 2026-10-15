/**
 * AuthFlow – Login and Sign-up (role, details with DOB → age → bracket, privacy consent).
 *
 * Layout: one centred card on the landing-page background (no side panel).
 * Interactive helpers: show/hide password, Caps Lock warning, live e-mail check, password-strength
 * meter, "passwords match" indicator, live age/bracket preview, clickable stepper, review step.
 *
 * Sign-up is a 3-step wizard:
 *   1. Role      – Patient | Parent/Guardian (registering a minor) | Clinician
 *   2. Details   – name, email, password, Date of Birth (patient or child) -> live age + bracket
 *   3. Consent   – review + privacy consent (raw audio never stored on the server)
 */
import { useState, type FormEvent, type KeyboardEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  Eye,
  EyeOff,
  Loader2,
  Lock,
  Mail,
  ShieldCheck,
  Stethoscope,
  User as UserIcon,
  Users,
  XCircle,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { bracketForAge, calculateAge, MAX_AGE, MIN_AGE } from "../utils/age";
import type { Role } from "../types";
import SiteFooter from "./SiteFooter";
import { ErrorBox, Logo } from "./ui";

const EMAIL_RE = /^\S+@\S+\.\S+$/;

// =========================================================================== shared bits
function AuthShell({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-b from-[#F3F1FF] via-canvas to-canvas">
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-lav-200/40 blur-3xl" aria-hidden />
      <div className="pointer-events-none absolute -bottom-40 -right-24 h-[28rem] w-[28rem] rounded-full bg-brand/10 blur-3xl" aria-hidden />

      <header className="relative mx-auto flex h-[72px] max-w-5xl items-center justify-between px-4 sm:px-6">
        <Link to="/welcome" aria-label="SpeakFree home"><Logo subtitle={false} /></Link>
        <Link to="/welcome" className="inline-flex items-center gap-1 text-sm font-medium text-ink-soft hover:text-ink">
          <ArrowLeft size={15} /> Back to home
        </Link>
      </header>

      <main className="relative flex justify-center px-4 pb-12 pt-4 sm:pt-10">
        <div className={`w-full ${wide ? "max-w-2xl" : "max-w-md"}`}>
          <div className="card p-6 shadow-lift sm:p-8">{children}</div>
          <p className="mt-6 flex items-center justify-center gap-1.5 text-center text-xs text-ink-muted">
            <ShieldCheck size={14} /> Raw audio is deleted from the server right after analysis.
          </p>
        </div>
      </main>
      <div className="relative mx-auto max-w-5xl px-4 sm:px-6"><SiteFooter variant="compact" /></div>
    </div>
  );
}

function Field({ label, icon, hint, children }: { label: string; icon?: ReactNode; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      <div className="relative">
        {icon && <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted">{icon}</span>}
        {children}
      </div>
      {hint && <div className="mt-1.5 text-xs">{hint}</div>}
    </label>
  );
}

/** Input with a trailing tick when `valid` (e.g. a well-formed e-mail). */
function ValidMark({ show }: { show: boolean }) {
  if (!show) return null;
  return <CheckCircle2 size={17} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ok" aria-hidden />;
}

/** Password input with show/hide toggle and a Caps Lock warning. */
function PasswordInput({ value, onChange, autoComplete, placeholder, id }: {
  value: string; onChange: (v: string) => void; autoComplete: string; placeholder?: string; id?: string;
}) {
  const [visible, setVisible] = useState(false);
  const [caps, setCaps] = useState(false);
  const checkCaps = (e: KeyboardEvent<HTMLInputElement>) => setCaps(e.getModifierState?.("CapsLock") ?? false);
  return (
    <>
      <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted"><Lock size={16} /></span>
      <input
        id={id}
        className="input pl-9 pr-11"
        type={visible ? "text" : "password"}
        autoComplete={autoComplete}
        value={value}
        maxLength={64}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        onKeyUp={checkCaps}
        onKeyDown={checkCaps}
        onBlur={() => setCaps(false)}
        required
      />
      <button type="button" onClick={() => setVisible((v) => !v)}
        className="absolute right-2 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-lg text-ink-muted hover:bg-canvas hover:text-ink"
        aria-label={visible ? "Hide password" : "Show password"} aria-pressed={visible}>
        {visible ? <EyeOff size={17} /> : <Eye size={17} />}
      </button>
      {caps && (
        <div className="absolute -bottom-6 left-0 flex items-center gap-1 text-xs font-medium text-warn" role="status">
          <AlertTriangle size={12} /> Caps Lock is on
        </div>
      )}
    </>
  );
}

function passwordStrength(pw: string): { score: number; label: string; color: string } {
  if (!pw) return { score: 0, label: "", color: "" };
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (pw.length < 8) return { score: 1, label: "Too short – at least 8 characters", color: "bg-bad" };
  if (score <= 2) return { score: 2, label: "Fair", color: "bg-warn" };
  if (score === 3) return { score: 3, label: "Good", color: "bg-brand" };
  return { score: 4, label: "Strong", color: "bg-ok" };
}

function StrengthMeter({ password }: { password: string }) {
  const s = passwordStrength(password);
  if (!password) return <span className="text-ink-muted">Use 8+ characters. Mixing letters, numbers and symbols makes it stronger.</span>;
  return (
    <div>
      <div className="flex gap-1" aria-hidden>
        {[1, 2, 3, 4].map((i) => <span key={i} className={`h-1.5 flex-1 rounded-full ${i <= s.score ? s.color : "bg-line"}`} />)}
      </div>
      <span className={`mt-1 block font-medium ${s.score === 1 ? "text-bad" : "text-ink-soft"}`}>{s.label}</span>
    </div>
  );
}

// =========================================================================== login
function LoginForm() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const emailOk = EMAIL_RE.test(email.trim());
  const locked = !!error?.startsWith("Account locked");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email.trim(), password);
      navigate("/", { replace: true });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell>
      <div className="animate-step">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-lav-100 text-navy"><UserIcon size={26} /></div>
          <h1 className="text-2xl font-extrabold text-ink">Welcome back</h1>
          <p className="mt-1 text-sm text-ink-soft">Sign in to continue your speech screening.</p>
        </div>

        <form onSubmit={onSubmit} className="space-y-5" noValidate>
          {locked ? (
            <div role="alert" className="flex gap-3 rounded-xl border border-warn/30 bg-warn-soft px-4 py-3 text-sm text-warn">
              <Lock size={18} className="mt-0.5 shrink-0" />
              <div><b>{error}.</b><br /><span className="text-ink-soft">For your security the account is locked after 5 wrong passwords.</span></div>
            </div>
          ) : (
            <ErrorBox message={error} />
          )}

          <Field label="Email" icon={<Mail size={16} />}>
            <input className="input pl-9 pr-10" type="email" autoComplete="email" required value={email} autoFocus
              onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
            <ValidMark show={emailOk} />
          </Field>

          <div className="pb-2">
            <span className="label">Password</span>
            <div className="relative">
              <PasswordInput value={password} onChange={setPassword} autoComplete="current-password" placeholder="Your password" />
            </div>
          </div>

          <button className="btn-primary w-full py-3 text-[15px]" disabled={busy || !emailOk || !password}>
            {busy ? <Loader2 className="animate-spin" size={18} /> : <ArrowRight size={18} />} Sign in
          </button>
        </form>

        <div className="my-6 flex items-center gap-3 text-xs font-medium uppercase tracking-wider text-ink-muted" aria-hidden>
          <span className="h-px flex-1 bg-line" /> New to SpeakFree? <span className="h-px flex-1 bg-line" />
        </div>
        <Link to="/signup" className="btn-outline w-full py-3">Create a free account</Link>
      </div>
    </AuthShell>
  );
}

// =========================================================================== sign-up
const ROLES: { id: Role; title: string; desc: string; icon: ReactNode }[] = [
  { id: "patient", title: "Patient", desc: "I am 6–20 years old and doing my own screening.", icon: <UserIcon size={22} /> },
  { id: "guardian", title: "Parent / Guardian", desc: "I am registering my child (a minor) for screening.", icon: <Users size={22} /> },
  { id: "clinician", title: "Clinician", desc: "I am a speech-language professional managing patients.", icon: <Stethoscope size={22} /> },
];
const STEPS = ["Account type", "Your details", "Review & consent"] as const;

function AgePreview({ dob }: { dob: string }) {
  const age = calculateAge(dob);
  if (age === null) return null;
  const bracket = bracketForAge(age);
  const ok = age >= MIN_AGE && age <= MAX_AGE && bracket;
  return (
    <div className={`mt-2 flex items-start gap-2 rounded-xl border px-3 py-2 text-sm ${ok ? "border-ok/30 bg-ok-soft text-ok" : "border-bad/30 bg-bad-soft text-bad"}`} role="status">
      {ok ? <CheckCircle2 size={16} className="mt-0.5 shrink-0" /> : <XCircle size={16} className="mt-0.5 shrink-0" />}
      <span>
        {ok
          ? <>Age <b>{age}</b> · Bracket {bracket!.id} ({bracket!.label}) - tasks: {bracket!.focus.toLowerCase()}.</>
          : <>Calculated age {age}. SpeakFree screening supports ages {MIN_AGE}–{MAX_AGE}.</>}
      </span>
    </div>
  );
}

function SignupForm() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [role, setRole] = useState<Role | null>(null);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [dob, setDob] = useState("");
  const [childName, setChildName] = useState("");
  const [childDob, setChildDob] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const today = new Date().toISOString().slice(0, 10);
  const emailOk = EMAIL_RE.test(email.trim());
  const subjectDob = role === "patient" ? dob : role === "guardian" ? childDob : "";
  const subjectAge = calculateAge(subjectDob);
  const subjectBracket = bracketForAge(subjectAge);

  function validateDetails(): string | null {
    if (fullName.trim().length < 2) return "Please enter your full name.";
    if (!emailOk) return "Please enter a valid email address.";
    if (password.length < 8) return "Password must be at least 8 characters.";
    if (password !== confirm) return "Passwords do not match.";
    if (role === "guardian" && childName.trim().length < 2) return "Please enter your child's full name.";
    if (role === "patient" || role === "guardian") {
      if (subjectAge === null) return "Date of birth is required.";
      if (subjectAge < MIN_AGE || subjectAge > MAX_AGE) return `Screening supports ages ${MIN_AGE}–${MAX_AGE} (calculated age: ${subjectAge}).`;
    }
    return null;
  }

  function goTo(n: 1 | 2 | 3) {
    setError(null);
    if (n > 1 && !role) return setError("Please choose an account type.");
    if (n > 2) {
      const msg = validateDetails();
      if (msg) return setError(msg);
    }
    setStep(n);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (step < 3) return goTo((step + 1) as 2 | 3);
    setError(null);
    if (!consent) return setError("You must accept the privacy consent to continue.");
    setBusy(true);
    try {
      await register({
        role: role!,
        full_name: fullName.trim(),
        email: email.trim(),
        password,
        date_of_birth: role === "patient" ? dob : null,
        child_full_name: role === "guardian" ? childName.trim() : null,
        child_date_of_birth: role === "guardian" ? childDob : null,
        consent,
      });
      navigate("/", { replace: true });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function onRoleKey(e: KeyboardEvent<HTMLDivElement>) {
    const keys = ["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp"];
    if (!keys.includes(e.key)) return;
    e.preventDefault();
    const i = Math.max(0, ROLES.findIndex((r) => r.id === role));
    const next = (i + (e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : ROLES.length - 1)) % ROLES.length;
    setRole(ROLES[next].id);
    document.getElementById(`role-${ROLES[next].id}`)?.focus();
  }

  const roleInfo = ROLES.find((r) => r.id === role);

  return (
    <AuthShell wide>
      {/* stepper */}
      <div className="mb-7">
        <ol className="flex items-center gap-2 text-xs font-semibold">
          {STEPS.map((label, i) => {
            const n = (i + 1) as 1 | 2 | 3;
            const state = n < step ? "done" : n === step ? "current" : "todo";
            return (
              <li key={label} className="flex flex-1 items-center gap-2">
                <button type="button" disabled={state === "todo"} onClick={() => goTo(n)}
                  className="flex items-center gap-2 rounded-lg disabled:cursor-default" aria-current={state === "current" ? "step" : undefined}>
                  <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full transition ${state === "done" ? "bg-ok text-white" : state === "current" ? "bg-navy text-white ring-4 ring-lav-100" : "bg-canvas text-ink-muted"}`}>
                    {state === "done" ? <CheckCircle2 size={15} /> : n}
                  </span>
                  <span className={`hidden sm:inline ${state === "todo" ? "text-ink-muted" : "text-ink"} ${state === "done" ? "hover:underline" : ""}`}>{label}</span>
                </button>
                {n < 3 && <span className={`h-0.5 flex-1 rounded-full transition-colors ${n < step ? "bg-ok" : "bg-line"}`} />}
              </li>
            );
          })}
        </ol>
        <p className="mt-2 text-xs text-ink-muted sm:hidden">Step {step} of 3 · {STEPS[step - 1]}</p>
      </div>

      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        <ErrorBox message={error} />

        {step === 1 && (
          <div key="s1" className="animate-step">
            <h1 className="text-2xl font-extrabold text-ink">Who is creating this account?</h1>
            <p className="mt-1 text-sm text-ink-soft">This decides which details we ask for next. Use the arrow keys or click a card.</p>
            <div className="mt-5 grid gap-3 sm:grid-cols-3" role="radiogroup" aria-label="Account type" onKeyDown={onRoleKey}>
              {ROLES.map((r) => {
                const selected = role === r.id;
                return (
                  <div key={r.id} id={`role-${r.id}`} role="radio" aria-checked={selected}
                    tabIndex={selected || (!role && r.id === "patient") ? 0 : -1}
                    onClick={() => { setRole(r.id); setError(null); }}
                    onDoubleClick={() => { setRole(r.id); setStep(2); }}
                    onKeyDown={(e) => { if (e.key === " " || e.key === "Enter") { e.preventDefault(); setRole(r.id); if (e.key === "Enter") setStep(2); } }}
                    className={`relative cursor-pointer rounded-2xl border-2 p-4 text-left outline-none transition hover:-translate-y-0.5 focus-visible:ring-4 focus-visible:ring-brand/20 ${selected ? "border-navy bg-lav-50 shadow-card" : "border-line bg-white hover:border-lav-200 hover:shadow-card"}`}>
                    {selected && <CheckCircle2 size={18} className="absolute right-3 top-3 text-navy" aria-hidden />}
                    <div className={`mb-3 grid h-11 w-11 place-items-center rounded-xl transition ${selected ? "bg-navy text-white" : "bg-lav-100 text-navy"}`}>{r.icon}</div>
                    <div className="font-bold text-ink">{r.title}</div>
                    <div className="mt-1 text-xs leading-relaxed text-ink-soft">{r.desc}</div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {step === 2 && (
          <div key="s2" className="animate-step space-y-4">
            <div>
              <h1 className="text-2xl font-extrabold text-ink">Your details</h1>
              <p className="mt-1 text-sm text-ink-soft">Signing up as <b className="text-ink">{roleInfo?.title}</b>.</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={role === "guardian" ? "Your full name (parent/guardian)" : "Full name"} icon={<UserIcon size={16} />}>
                <input className="input pl-9" value={fullName} autoComplete="name" autoFocus onChange={(e) => setFullName(e.target.value)} required />
              </Field>
              <Field label="Email" icon={<Mail size={16} />}
                hint={email && !emailOk ? <span className="text-bad">That doesn't look like an email address yet.</span> : undefined}>
                <input className="input pl-9 pr-10" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                <ValidMark show={emailOk} />
              </Field>
              <div>
                <span className="label">Password</span>
                <div className="relative"><PasswordInput value={password} onChange={setPassword} autoComplete="new-password" /></div>
                <div className="mt-2 text-xs"><StrengthMeter password={password} /></div>
              </div>
              <div>
                <span className="label">Confirm password</span>
                <div className="relative"><PasswordInput value={confirm} onChange={setConfirm} autoComplete="new-password" /></div>
                {confirm && (
                  <div className={`mt-2 flex items-center gap-1 text-xs font-medium ${confirm === password ? "text-ok" : "text-bad"}`} role="status">
                    {confirm === password ? <><CheckCircle2 size={13} /> Passwords match</> : <><XCircle size={13} /> Passwords don't match yet</>}
                  </div>
                )}
              </div>
            </div>

            {role === "patient" && (
              <div>
                <Field label="Date of birth" icon={<CalendarDays size={16} />}>
                  <input className="input pl-9" type="date" max={today} value={dob} onChange={(e) => setDob(e.target.value)} required />
                </Field>
                <AgePreview dob={dob} />
              </div>
            )}

            {role === "guardian" && (
              <div className="space-y-4 rounded-2xl border border-lav-200 bg-lav-50 p-4">
                <div className="flex items-center gap-2 text-sm font-bold text-ink"><Users size={16} className="text-navy" /> Child being screened</div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Child's full name" icon={<UserIcon size={16} />}>
                    <input className="input pl-9" value={childName} onChange={(e) => setChildName(e.target.value)} required />
                  </Field>
                  <Field label="Child's date of birth" icon={<CalendarDays size={16} />}>
                    <input className="input pl-9" type="date" max={today} value={childDob} onChange={(e) => setChildDob(e.target.value)} required />
                  </Field>
                </div>
                <AgePreview dob={childDob} />
              </div>
            )}

            {role === "clinician" && (
              <p className="flex gap-2 rounded-xl border border-line bg-lav-50 px-4 py-3 text-sm text-ink-soft">
                <Stethoscope size={16} className="mt-0.5 shrink-0 text-navy" />
                As a clinician you add each patient (name and date of birth) from the top bar, and you can curate the task library.
              </p>
            )}
          </div>
        )}

        {step === 3 && (
          <div key="s3" className="animate-step space-y-4">
            <h1 className="text-2xl font-extrabold text-ink">Review &amp; consent</h1>

            <dl className="grid gap-x-6 gap-y-2 rounded-2xl border border-line bg-canvas/60 p-4 text-sm sm:grid-cols-2">
              <div><dt className="text-xs muted">Account type</dt><dd className="font-semibold text-ink">{roleInfo?.title}</dd></div>
              <div><dt className="text-xs muted">Name</dt><dd className="font-semibold text-ink">{fullName.trim()}</dd></div>
              <div><dt className="text-xs muted">Email</dt><dd className="truncate font-semibold text-ink">{email.trim()}</dd></div>
              {role === "guardian" && <div><dt className="text-xs muted">Child</dt><dd className="font-semibold text-ink">{childName.trim()}</dd></div>}
              {subjectAge !== null && subjectBracket && (
                <div><dt className="text-xs muted">Age · tasks</dt><dd className="font-semibold text-ink">{subjectAge} years · Bracket {subjectBracket.id} ({subjectBracket.label})</dd></div>
              )}
              <div className="sm:col-span-2">
                <button type="button" onClick={() => goTo(2)} className="text-xs font-semibold text-brand hover:underline">Edit details</button>
              </div>
            </dl>

            <div className="rounded-2xl border border-lav-200 bg-lav-50 p-4 text-sm leading-relaxed text-ink-soft">
              <div className="mb-2 flex items-center gap-2 font-bold text-navy"><ShieldCheck size={18} /> How your voice data is protected</div>
              <ul className="list-disc space-y-1 pl-5">
                <li>Recordings are processed only to extract speech features and are <b className="text-ink">deleted immediately</b> after analysis. Raw audio is never stored on our servers.</li>
                <li>Playback of your recording happens only in <b className="text-ink">your own browser</b>. Until you press Analyse Now, unfinished recordings are kept in this browser only, and they are removed once the analysis is complete.</li>
                <li>Only derived scores (numbers and transcript) are saved, linked to a pseudonymous patient ID. The SpeakFree administrator can review these results to support follow-up care.</li>
                <li>Aggregated statistics used for research are protected with <b className="text-ink">differential privacy</b> (Component 4).</li>
                <li>SpeakFree is a screening aid. Results do not replace assessment by a qualified speech-language pathologist.</li>
              </ul>
            </div>
            <label className={`flex cursor-pointer items-start gap-3 rounded-xl border-2 p-4 transition ${consent ? "border-ok/50 bg-ok-soft" : "border-line hover:border-lav-200"}`}>
              <input type="checkbox" className="mt-1 h-5 w-5 accent-[#1E3A8A]" checked={consent} onChange={(e) => { setConsent(e.target.checked); setError(null); }} />
              <span className="text-sm text-ink">
                I have read and agree to how SpeakFree processes voice data.
                {role === "guardian" && " As the parent/guardian, I consent on behalf of my child."}
              </span>
            </label>
          </div>
        )}

        <div className="flex items-center justify-between gap-3 border-t border-line pt-5">
          {step > 1 ? (
            <button type="button" className="btn-ghost" onClick={() => goTo((step - 1) as 1 | 2)}>
              <ArrowLeft size={16} /> Back
            </button>
          ) : (
            <Link to="/login" className="text-sm font-medium text-ink-soft hover:text-ink">Already registered? <span className="text-brand">Sign in</span></Link>
          )}
          <button className="btn-primary px-6" disabled={busy || (step === 1 && !role) || (step === 3 && !consent)}>
            {busy && <Loader2 className="animate-spin" size={18} />}
            {step < 3 ? <>Continue <ArrowRight size={16} /></> : "Create account"}
          </button>
        </div>
      </form>
    </AuthShell>
  );
}

export default function AuthFlow({ mode }: { mode: "login" | "signup" }) {
  return mode === "login" ? <LoginForm /> : <SignupForm />;
}
