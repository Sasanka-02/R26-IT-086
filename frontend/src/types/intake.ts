import { AgeCategory } from "./index";

export type DisorderType = "none" | "stuttering" | "dysarthria" | "articulation";

export interface PatientIntake {
  nickname: string;
  ageCategory: AgeCategory;
  disorderType: DisorderType | null;
  previousTherapyNotes: string;
  consents: {
    regulatoryCompliance: boolean;
    audioStoragePolicy: boolean;
    participationConsent: boolean;
  };
  completedAt: string;
}

export const DISORDER_TYPE_LABELS: Record<DisorderType, string> = {
  none: "None / Not sure",
  stuttering: "Stuttering (repetitions, blocks)",
  dysarthria: "Dysarthria (muscle weakness / slurred speech)",
  articulation: "Articulation disorder (specific sounds)",
};