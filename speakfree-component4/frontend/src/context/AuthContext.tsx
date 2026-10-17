import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { api, SESSION_KEY, setUnauthorizedHandler } from "../api/client";
import { AgeGroup } from "../types/therapy";

export type UserRole = "student" | "therapist";

export interface AppUser {
  name: string;
  email: string;
  role: UserRole;
  /** Students only. Missing for accounts made before ages were collected. */
  age?: number | null;
  age_group?: AgeGroup;
  /** Students: practice recordings go to the therapist unless this is false. */
  share_recordings?: boolean;
}

interface Session {
  token: string;
  user: AppUser;
}

interface SignupInput {
  email: string;
  name: string;
  password: string;
  role: UserRole;
  inviteCode?: string;
  consent: boolean;
  age?: number;
  guardianConsent?: boolean;
}

interface AuthContextValue {
  user: AppUser | null;
  login: (email: string, password: string) => Promise<AppUser>;
  signup: (input: SignupInput) => Promise<AppUser>;
  logout: () => void;
  /** Replace the stored user (e.g. after setting an age). */
  updateUser: (user: AppUser) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const LEGACY_KEY = "speakfree_c4_demo_user";

function readSession(): Session | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  // Read synchronously so protected routes don't redirect to /login on refresh.
  const [session, setSession] = useState<Session | null>(readSession);

  const store = (next: Session) => {
    localStorage.setItem(SESSION_KEY, JSON.stringify(next));
    localStorage.removeItem(LEGACY_KEY);
    setSession(next);
    return next.user;
  };

  const logout = () => {
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(LEGACY_KEY);
    setSession(null);
  };

  useEffect(() => {
    setUnauthorizedHandler(logout);
  }, []);

  const updateUser = (next: AppUser) => {
    setSession((current) => {
      if (!current) return current;
      const updated = { ...current, user: { ...current.user, ...next } };
      localStorage.setItem(SESSION_KEY, JSON.stringify(updated));
      return updated;
    });
  };

  // Refresh the stored account once per visit, so changes such as an age group
  // set by the therapist reach the browser.
  const sessionEmail = session?.user.email;
  useEffect(() => {
    if (!sessionEmail) return;
    api
      .get("/api/v1/auth/me")
      .then((res) => updateUser(res.data))
      .catch(() => {});
  }, [sessionEmail]);

  const login = async (email: string, password: string) => {
    const res = await api.post("/api/v1/auth/login", { email, password });
    return store(res.data);
  };

  const signup = async ({ email, name, password, role, inviteCode, consent, age, guardianConsent }: SignupInput) => {
    const res = await api.post("/api/v1/auth/signup", {
      email,
      name,
      password,
      role,
      invite_code: inviteCode || null,
      consent,
      age: role === "student" ? age : null,
      guardian_consent: guardianConsent ?? false,
    });
    return store(res.data);
  };

  return (
    <AuthContext.Provider value={{ user: session?.user ?? null, login, signup, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function homePathFor(role: UserRole): string {
  return role === "therapist" ? "/therapist" : "/dashboard";
}
