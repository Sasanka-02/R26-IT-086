import { ExerciseType } from "./therapy";

export interface CompletedSession {
  id: string;
  exerciseId: string;
  exerciseType: ExerciseType;
  title: string;
  completedAt: string;
}