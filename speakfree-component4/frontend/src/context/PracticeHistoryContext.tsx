import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { CompletedSession } from "../types/history";
import { TherapyExercise } from "../types/therapy";

interface PracticeHistoryContextValue {
  history: CompletedSession[];
  recordCompletion: (exercise: TherapyExercise) => void;
  totalCompleted: number;
  lastCompletedAt: string | null;
}

const PracticeHistoryContext = createContext<PracticeHistoryContextValue | undefined>(
  undefined
);
const STORAGE_KEY = "speakfree_c4_practice_history";

export function PracticeHistoryProvider({ children }: { children: ReactNode }) {
  const [history, setHistory] = useState<CompletedSession[]>([]);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setHistory(JSON.parse(stored));
      } catch {
        localStorage.removeItem(STORAGE_KEY);
      }
    }
  }, []);

  const recordCompletion = (exercise: TherapyExercise) => {
    const entry: CompletedSession = {
      id: `${exercise.id}-${Date.now()}`,
      exerciseId: exercise.id,
      exerciseType: exercise.type,
      title: exercise.title,
      completedAt: new Date().toISOString(),
    };
    setHistory((prev) => {
      const updated = [entry, ...prev];
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });
  };

  return (
    <PracticeHistoryContext.Provider
      value={{
        history,
        recordCompletion,
        totalCompleted: history.length,
        lastCompletedAt: history[0]?.completedAt ?? null,
      }}
    >
      {children}
    </PracticeHistoryContext.Provider>
  );
}

export function usePracticeHistory(): PracticeHistoryContextValue {
  const ctx = useContext(PracticeHistoryContext);
  if (!ctx) throw new Error("usePracticeHistory must be used within PracticeHistoryProvider");
  return ctx;
}