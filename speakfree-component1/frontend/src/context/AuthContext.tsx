import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, tokenStore, type RegisterPayload } from "../api/client";
import type { Patient, User } from "../types";

const ACTIVE_PATIENT_KEY = "speakfree.activePatient";

interface AuthState {
  user: User | null;
  loading: boolean;
  activePatient: Patient | null;
  setActivePatientId: (id: string) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterPayload) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

function readActive(): string | null {
  try {
    return localStorage.getItem(ACTIVE_PATIENT_KEY);
  } catch {
    return null;
  }
}
function writeActive(id: string | null) {
  try {
    if (id) localStorage.setItem(ACTIVE_PATIENT_KEY, id);
    else localStorage.removeItem(ACTIVE_PATIENT_KEY);
  } catch {
    /* ignore */
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeId, setActiveId] = useState<string | null>(readActive());

  const refresh = useCallback(async () => {
    if (!tokenStore.get()) {
      setUser(null);
      return;
    }
    try {
      setUser(await api.me());
    } catch {
      tokenStore.set(null);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.login(email, password);
    tokenStore.set(res.access_token);
    setUser(res.user);
  }, []);

  const register = useCallback(async (data: RegisterPayload) => {
    const res = await api.register(data);
    tokenStore.set(res.access_token);
    setUser(res.user);
  }, []);

  const logout = useCallback(() => {
    tokenStore.set(null);
    writeActive(null);
    setActiveId(null);
    setUser(null);
  }, []);

  const setActivePatientId = useCallback((id: string) => {
    writeActive(id);
    setActiveId(id);
  }, []);

  const activePatient = useMemo(() => {
    if (!user || user.patients.length === 0) return null;
    return user.patients.find((p) => p.id === activeId) ?? user.patients[0];
  }, [user, activeId]);

  const value = useMemo(
    () => ({ user, loading, activePatient, setActivePatientId, login, register, logout, refresh }),
    [user, loading, activePatient, setActivePatientId, login, register, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
