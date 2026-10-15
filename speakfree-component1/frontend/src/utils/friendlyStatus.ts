// Patient-facing wording for the 1–4 screening level (no clinical jargon, no numbers).
import { COLORS } from "../components/ui";

export const FRIENDLY_STATUS: Record<number, { title: string; text: string; color: string }> = {
  1: { title: "On track", text: "Your speech is within the typical range for your age. Great work!", color: COLORS.ok },
  2: { title: "Keep an eye on it", text: "You're mostly on track. A little regular practice will help in a couple of areas.", color: COLORS.brand },
  3: { title: "Moderate concern", text: "Some areas would benefit from regular practice and a check-in with a speech therapist.", color: COLORS.warn },
  4: { title: "Let's get some support", text: "We recommend sharing these results with a speech therapist so they can help you.", color: COLORS.bad },
};

export const friendlyStatus = (level: number) => FRIENDLY_STATUS[level] ?? FRIENDLY_STATUS[2];
