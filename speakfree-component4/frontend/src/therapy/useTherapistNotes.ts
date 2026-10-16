import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { TherapistNotes } from "../types/therapy";
import { getMyNotes, markNotesRead } from "./therapyApi";

// The bell and the dashboard card each use this hook; this event keeps them in sync.
const CHANGED = "speakfree:notes-changed";

/**
 * Notes the therapist shared with the logged-in student. Refreshes when the
 * page regains focus, so a note added while the student is logged in appears
 * without reloading. Therapists get an empty result (no requests made).
 */
export function useTherapistNotes() {
  const { user } = useAuth();
  const isStudent = user?.role === "student";
  const [data, setData] = useState<TherapistNotes>({ notes: [], unread: 0 });

  const load = useCallback(() => {
    if (!isStudent || !user) return;
    getMyNotes(user.email)
      .then(setData)
      .catch(() => {});
  }, [isStudent, user]);

  useEffect(() => {
    load();
    window.addEventListener(CHANGED, load);
    window.addEventListener("focus", load);
    return () => {
      window.removeEventListener(CHANGED, load);
      window.removeEventListener("focus", load);
    };
  }, [load]);

  const markRead = useCallback(async () => {
    if (!isStudent || !user) return;
    setData(await markNotesRead(user.email));
    window.dispatchEvent(new Event(CHANGED));
  }, [isStudent, user]);

  return { ...data, markRead };
}
