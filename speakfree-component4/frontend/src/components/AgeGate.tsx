import { FormEvent, useEffect, useState } from "react";
import { HeartPulse } from "lucide-react";
import { api, errorMessage } from "../api/client";
import { AppUser, useAuth } from "../context/AuthContext";
import AgeFields, { ageError } from "./AgeFields";

/**
 * One-time step for students who signed up before ages were collected:
 * "How old are you?" decides which exercises they get.
 */
export default function AgeGate() {
  const { user, updateUser, logout } = useAuth();
  const [checking, setChecking] = useState(true);
  const [age, setAge] = useState("");
  const [guardian, setGuardian] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // The stored session may be older than the account: check the server first.
  useEffect(() => {
    api
      .get<AppUser>("/api/v1/auth/me")
      .then((res) => {
        if (res.data.age_group) updateUser(res.data);
      })
      .catch(() => {})
      .finally(() => setChecking(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const problem = ageError(age);
    if (problem) return setError(problem);
    setSaving(true);
    setError(null);
    try {
      const res = await api.put<AppUser>("/api/v1/auth/me/age", { age: Number(age), guardian_consent: guardian });
      updateUser(res.data);
    } catch (err) {
      setError(errorMessage(err, "Couldn't save your age. Please try again."));
      setSaving(false);
    }
  };

  if (checking) return <div className="min-h-screen bg-shell" />;

  return (
    <div className="flex min-h-screen items-center justify-center bg-shell px-6">
      <div className="w-full max-w-sm rounded-2xl border border-teal-100 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-teal-600 text-white">
            <HeartPulse size={16} />
          </div>
          <span className="font-display text-lg font-semibold text-ink">SpeakFree Therapy</span>
        </div>
        <h1 className="font-display text-xl font-semibold text-ink">How old are you?</h1>
        <p className="mt-1 text-sm text-ink-soft">
          Hi {user?.name?.split(" ")[0]}! Practice is different for children, teens and adults, so we need your age
          once before you continue.
        </p>
        <form onSubmit={submit} className="mt-5 space-y-4">
          <AgeFields age={age} onAge={setAge} guardian={guardian} onGuardian={setGuardian} />
          {error && (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
              {error}
            </p>
          )}
          <button
            disabled={saving}
            className="w-full rounded-full bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-60"
          >
            Continue
          </button>
        </form>
        <button onClick={logout} className="mt-3 w-full text-center text-xs text-ink-soft hover:underline">
          Not you? Sign out
        </button>
      </div>
    </div>
  );
}
