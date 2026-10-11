import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { useAuth } from "./AuthContext";
import { getProgress, submitResult } from "../therapy/therapyApi";
import {
  ExerciseResultInput,
  ExerciseResultResponse,
  ProgressSummary,
} from "../types/therapy";

interface PracticeHistoryContextValue {
  userId: string;
  progress: ProgressSummary | null;
  progressError: boolean;
  /** Bumps after every saved result so views can refetch their own data. */
  version: number;
  recordCompletion: (result: ExerciseResultInput) => Promise<ExerciseResultResponse>;
  refresh: () => void;
}

const PracticeHistoryContext = createContext<PracticeHistoryContextValue | undefined>(
  undefined
);

export function PracticeHistoryProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const userId = user?.email.trim().toLowerCase() ?? "";
  const [progress, setProgress] = useState<ProgressSummary | null>(null);
  const [progressError, setProgressError] = useState(false);
  const [version, setVersion] = useState(0);

  const refresh = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    setProgress(null);
    setProgressError(false);
    if (!userId) return;
    let active = true;
    getProgress(userId)
      .then((data) => active && setProgress(data))
      .catch(() => active && setProgressError(true));
    return () => {
      active = false;
    };
  }, [userId, version]);

  const recordCompletion = async (result: ExerciseResultInput) => {
    const saved = await submitResult(userId, result);
    refresh();
    return saved;
  };

  return (
    <PracticeHistoryContext.Provider
      value={{ userId, progress, progressError, version, recordCompletion, refresh }}
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
