import { createContext, ReactNode, useContext, useState } from "react";

interface SessionContextValue {
  sessionId: string;
  resetSession: () => void;
}

function generateSessionId(): string {
  return `c4-session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

const SessionContext = createContext<SessionContextValue | undefined>(undefined);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState(generateSessionId);

  const resetSession = () => setSessionId(generateSessionId());

  return (
    <SessionContext.Provider value={{ sessionId, resetSession }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}
