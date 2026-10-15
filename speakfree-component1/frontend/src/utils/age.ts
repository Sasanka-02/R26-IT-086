// Age calculation + bracket rules (must match backend/age_brackets.py)

export const MIN_AGE = 6;
export const MAX_AGE = 20;

export const BRACKETS = [
  { id: 1, label: "Ages 6–8", min: 6, max: 7, focus: "Short phonetic sentences, single-action pictures, daily choices" },
  { id: 2, label: "Ages 8–10", min: 8, max: 9, focus: "Compound sentences with consonant blends, multi-subject scenes" },
  { id: 3, label: "Ages 10–12", min: 10, max: 11, focus: "40–50 word paragraphs, cause-and-effect pictures, social reasoning" },
  { id: 4, label: "Ages 12–14", min: 12, max: 13, focus: "Expository passages, environmental scenes, hypothetical dilemmas" },
  { id: 5, label: "Ages 14–16", min: 14, max: 15, focus: "Standardised clinical passages, complex social scenes, critical thinking" },
  { id: 6, label: "Ages 16–18", min: 16, max: 17, focus: "Academic prose, societal themes, persuasive speech" },
  { id: 7, label: "Ages 18–20", min: 18, max: 20, focus: "Professional texts with tonal modulation, data analysis, workplace conflict" },
];

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
