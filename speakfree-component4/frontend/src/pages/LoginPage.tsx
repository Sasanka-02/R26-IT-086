import { FormEvent, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { HeartPulse } from "lucide-react";
import { homePathFor, useAuth } from "../context/AuthContext";
import { errorMessage } from "../api/client";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const account = await login(email, password);
      navigate(homePathFor(account.role));
    } catch (err) {
      setError(errorMessage(err, "Couldn't log in. Check that the therapy service is running."));
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
          <h1 className="font-display text-xl font-semibold text-ink">Welcome back</h1>
          <p className="mt-1 text-sm text-ink-soft">Log in to continue.</p>

          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
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
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-lg border border-teal-100 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                placeholder="••••••••"
              />
            </div>

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
              Log in
            </button>
          </form>

          <p className="mt-4 text-center text-sm text-ink-soft">
            New here?{" "}
            <Link to="/signup" className="font-medium text-teal-600 hover:underline">
              Create an account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
