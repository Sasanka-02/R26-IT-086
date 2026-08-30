import { createContext, ReactNode, useContext, useState } from "react";
import { AgeCategory } from "../types";

interface SessionContextValue {
  sessionId: string;
  ageCategory: AgeCategory | null;
  setAgeCategory: (age: AgeCategory) => void;
  resetSession: () => void;
}

function generateSessionId(): string {
  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

const SessionContext = createContext<SessionContextValue | undefined>(undefined);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState(generateSessionId);
  const [ageCategory, setAgeCategoryState] = useState<AgeCategory | null>(null);

  const setAgeCategory = (age: AgeCategory) => setAgeCategoryState(age);

  const resetSession = () => {
    setSessionId(generateSessionId());
    setAgeCategoryState(null);
  };

  return (
    <SessionContext.Provider
      value={{ sessionId, ageCategory, setAgeCategory, resetSession }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}