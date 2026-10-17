import { FormEvent, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { HeartPulse } from "lucide-react";
import { homePathFor, useAuth, UserRole } from "../context/AuthContext";
import RolePicker from "../components/RolePicker";
import { errorMessage } from "../api/client";
import AgeFields, { ageError } from "../components/AgeFields";

export default function SignupPage() {
  const navigate = useNavigate();
  const { signup } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("student");
  const [submitting, setSubmitting] = useState(false);
  const [inviteCode, setInviteCode] = useState("");
  const [consent, setConsent] = useState(false);
  const [age, setAge] = useState("");
  const [guardian, setGuardian] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (role === "student") {
      const problem = ageError(age);
      if (problem) return setError(problem);
    }
    setSubmitting(true);
    setError(null);
    try {
      const account = await signup({
        email, name, password, role, inviteCode, consent,
        age: role === "student" ? Number(age) : undefined,
        guardianConsent: guardian,
      });
      navigate(homePathFor(account.role));
    } catch (err) {
      setError(errorMessage(err, "Couldn't create the account. Check that the therapy service is running."));
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-shell px-6">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-teal-600 text-white">
            <HeartPulse size={16} />
          </div>
          <span className="font-display text-lg font-semibold text-ink">
            SpeakFree Therapy
          </span>
        </div>

        <div className="rounded-2xl border border-teal-100 bg-white p-6 shadow-sm">
          <h1 className="font-display text-xl font-semibold text-ink">Create your account</h1>
          <p className="mt-1 text-sm text-ink-soft">Start practicing in minutes.</p>

          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            <RolePicker value={role} onChange={setRole} />
            {role === "therapist" && (
              <div>
                <label className="text-sm font-medium text-ink-soft">Clinic invite code</label>
                <input
                  type="text"
                  required
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-teal-100 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  placeholder="Provided by your clinic"
                />
              </div>
            )}
            <div>
              <label className="text-sm font-medium text-ink-soft">Full name</label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 w-full rounded-lg border border-teal-100 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                placeholder="Jane Doe"
              />
            </div>
            {role === "student" && (
              <AgeFields age={age} onAge={setAge} guardian={guardian} onGuardian={setGuardian} />
            )}
            <div>
              <label className="text-sm font-medium text-ink-soft">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded-lg border border-teal-100 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-ink-soft">Password</label>
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-lg border border-teal-100 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                placeholder="••••••••"
              />
            </div>

            <label className="flex items-start gap-2 rounded-lg bg-shell/60 p-3 text-xs text-ink-soft">
              <input
                type="checkbox"
                required
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-0.5 accent-teal-600"
              />
              <span>
                I agree that SpeakFree stores my practice results (scores, timings, pauses, how each exercise felt)
                so that I and my therapist can track progress. My practice recordings are shared with my therapist so they can give feedback (I can switch this off). I can download
                or delete my data at any time from the Privacy page (Personal Data Protection Act No. 9 of 2022).
                If I am under 18, a parent or guardian has agreed to this.
              </span>
            </label>

            {error && (
              <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full disabled:opacity-60 rounded-full bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-700"
            >
              Create account
            </button>
          </form>

          <p className="mt-4 text-center text-sm text-ink-soft">
            Already have an account?{" "}
            <Link to="/login" className="font-medium text-teal-600 hover:underline">
              Log in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
