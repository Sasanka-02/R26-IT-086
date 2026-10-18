// Age calculation + bracket rules (must match speakfree-component4/backend/component4/brackets.py,
// re-exported by backend/age_brackets.py)

export const MIN_AGE = 6;
export const MAX_AGE = 100;
export const ADULT_AGE = 18; // under 18: a parent or guardian must agree to the account
export const TOO_YOUNG_MESSAGE = "This app is for ages 6 and above";

export type BracketTheme = "playful" | "modern" | "professional";

export const BRACKETS: { id: number; label: string; min: number; max: number; theme: BracketTheme; focus: string }[] = [
  { id: 1, label: "Ages 6–7", min: 6, max: 7, theme: "playful", focus: "Short phonetic sentences, single-action pictures, daily choices" },
  { id: 2, label: "Ages 8–9", min: 8, max: 9, theme: "playful", focus: "Compound sentences with consonant blends, multi-subject scenes, problem solving" },
  { id: 3, label: "Ages 10–11", min: 10, max: 11, theme: "playful", focus: "40–50 word paragraphs, cause-and-effect pictures, social reasoning" },
  { id: 4, label: "Ages 12–13", min: 12, max: 13, theme: "modern", focus: "Expository passages, environmental scenes, hypothetical dilemmas" },
  { id: 5, label: "Ages 14–15", min: 14, max: 15, theme: "modern", focus: "Clinical-style passages, complex social scenes, critical thinking" },
  { id: 6, label: "Ages 16–17", min: 16, max: 17, theme: "modern", focus: "Academic prose, societal themes, persuasive speech" },
  { id: 7, label: "Ages 18–20", min: 18, max: 20, theme: "professional", focus: "Professional texts with tonal modulation, chart interpretation, workplace conflict" },
  { id: 8, label: "Ages 21+", min: 21, max: MAX_AGE, theme: "professional", focus: "Professional and news texts, real-life scenes, job interviews and phone calls" },
];

/** The screening task library covers brackets 1–7; adults (bracket 8) are screened with the bracket-7 tasks. */
export const SCREENING_BRACKETS = BRACKETS.filter((b) => b.id <= 7);

export function calculateAge(dob: string, today: Date = new Date()): number | null {
  if (!dob) return null;
  const birth = new Date(`${dob}T00:00:00`);
  if (Number.isNaN(birth.getTime())) return null;
  let age = today.getFullYear() - birth.getFullYear();
  const beforeBirthday =
    today.getMonth() < birth.getMonth() || (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate());
  if (beforeBirthday) age -= 1;
  return age;
}

export function bracketForAge(age: number | null) {
  if (age === null) return null;
  return BRACKETS.find((b) => age >= b.min && age <= b.max) ?? null;
}

/** Validation message for an entered age, or null when it is accepted. */
export function ageError(age: number | null): string | null {
  if (age === null || Number.isNaN(age)) return "Please enter your age.";
  if (!Number.isInteger(age)) return "Please enter your age in whole years.";
  if (age < MIN_AGE) return TOO_YOUNG_MESSAGE;
  if (age > MAX_AGE) return `Please enter an age between ${MIN_AGE} and ${MAX_AGE}.`;
  return null;
}

/** Visual style per age bracket: bright + big for 6–11, modern + clean for 12–17, calm + professional for 18+. */
export const THEMES: Record<BracketTheme, {
  hero: string; button: string; card: string; accent: string; celebrate: boolean; listen: boolean; emoji: string;
}> = {
  playful: {
    hero: "bg-gradient-to-br from-[#FF7A59] via-[#F59E0B] to-[#7C6CF0]",
    button: "rounded-2xl px-7 py-4 text-lg",
    card: "rounded-3xl border-2",
    accent: "#F59E0B",
    celebrate: true,
    listen: true,
    emoji: "🌟",
  },
  modern: {
    hero: "bg-gradient-to-br from-navy via-[#2A3FB0] to-lav-500",
    button: "px-6 py-3 text-base",
    card: "rounded-2xl border",
    accent: "#7C6CF0",
    celebrate: false,
    listen: false,
    emoji: "",
  },
  professional: {
    hero: "bg-gradient-to-br from-[#1F2A44] via-[#26365E] to-[#3B4A6B]",
    button: "px-6 py-3 text-base",
    card: "rounded-2xl border",
    accent: "#1E3A8A",
    celebrate: false,
    listen: false,
    emoji: "",
  },
};

export function themeFor(theme: BracketTheme | undefined | null) {
  return THEMES[theme ?? "modern"];
}

/** Theme name for an age-bracket id (e.g. the active patient's), "modern" when unknown. */
export function themeNameForBracket(bracketId: number | null | undefined): BracketTheme {
  return BRACKETS.find((b) => b.id === bracketId)?.theme ?? "modern";
}
