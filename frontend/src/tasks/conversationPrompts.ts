import { AgeCategory } from "../types";

export interface ConversationPrompt {
  id: string;
  text: string;
}

export const CONVERSATION_PROMPTS: Record<AgeCategory, ConversationPrompt[]> = {
  kids: [
    { id: "k1", text: "Hi! Can you tell me your favorite game to play?" },
    { id: "k2", text: "What did you do at school or at home today?" },
    { id: "k3", text: "If you could have any pet, what would you choose and why?" },
  ],
  adults: [
    { id: "a1", text: "Hello. Could you tell me a little about your typical day?" },
    { id: "a2", text: "What is a hobby or activity you enjoy, and why?" },
    { id: "a3", text: "Can you describe a place you would like to visit and what draws you to it?" },
  ],
};
