import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { PatientIntake } from "../types/intake";

interface IntakeContextValue {
  intake: PatientIntake | null;
  hasIntake: boolean;
  saveIntake: (data: PatientIntake) => void;
  clearIntake: () => void;
}

const IntakeContext = createContext<IntakeContextValue | undefined>(undefined);
const STORAGE_KEY = "speakfree_demo_intake";

export function IntakeProvider({ children }: { children: ReactNode }) {
  const [intake, setIntake] = useState<PatientIntake | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setIntake(JSON.parse(stored));
      } catch {
        localStorage.removeItem(STORAGE_KEY);
      }
    }
  }, []);

  const saveIntake = (data: PatientIntake) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    setIntake(data);
  };

  const clearIntake = () => {
    localStorage.removeItem(STORAGE_KEY);
    setIntake(null);
  };

  return (
    <IntakeContext.Provider
      value={{ intake, hasIntake: intake !== null, saveIntake, clearIntake }}
    >
      {children}
    </IntakeContext.Provider>
  );
}

export function useIntake(): IntakeContextValue {
  const ctx = useContext(IntakeContext);
  if (!ctx) throw new Error("useIntake must be used within IntakeProvider");
  return ctx;
}