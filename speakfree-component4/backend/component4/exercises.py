"""
Exercise bank for the four therapy foci.

Every exercise is tagged with the foci it serves (`focus`), a difficulty (1-3) and, for ladder
exercises, a `level`. The bandit (bandit.py) may recommend any exercise, but the category
prior steers it towards the patient's focus; sound drills are generated for the exact sounds
Component 1 flagged.

The core of every plan is the 24 age-bracket exercises (bracket_tasks.py: `bracket` 1-8 x
`task_type` reading | picture | conversation). The exercises below are the extra practice the
bandit adds around them; `min_bracket` keeps an exercise away from learners who are too young
for it. `legacy` exercises were superseded by the bracket tasks - they are never planned, but
still resolve so old attempts keep their titles and scores.

Exercise types and what the browser measures (never raw audio):
  reading / pacing / clear_speech  highlighted passage at a target speed + live metrics
  picture / conversation           free description / spontaneous answer + live metrics
  loudness                         phrases read with a loudness meter + live metrics
  sustained_vowel                  hold "ahh" - longest continuous voicing (max_phonation_sec)
  sound_drill                      target-sound words / phrases / sentences + self-check
  daf                              delayed auditory feedback (Web Audio delay node)
"""
from __future__ import annotations

import re

from .bracket_tasks import BRACKET_EXERCISES, bracket_exercises

LEVELS = ["beginner", "intermediate", "advanced"]

# ------------------------------------------------------------------------------- static bank
EXERCISE_BANK: list[dict] = [
    # ---------------- fluency (stuttering) + maintenance: graded reading ladder ----------------
    {
        "id": "reading-beginner", "type": "reading", "level": "beginner", "difficulty": 1, "legacy": True,
        "focus": ["fluency", "maintenance"],
        "title": "Reading - Beginner: Sam and Max",
        "description": "Short, simple sentences. Read slowly and follow the highlight. Start each sentence with a soft, easy breath.",
        "target_wpm": 80,
        "passage": ("Sam has a red ball. He takes it to the park. The sun is warm and the sky is blue. "
                    "Sam throws the ball to his dog, Max. Max runs fast and brings it back. "
                    "They play until lunch time. Then they walk home together, happy and tired."),
    },
    {
        "id": "reading-intermediate", "type": "reading", "level": "intermediate", "difficulty": 2, "legacy": True,
        "focus": ["fluency", "maintenance"],
        "title": "Reading - Intermediate: Sunday Bread",
        "description": "Longer sentences with commas. Use the commas as natural places to pause and breathe.",
        "target_wpm": 110,
        "passage": ("Every Sunday, my grandmother bakes bread for the whole family. She wakes up early, mixes flour, "
                    "water and yeast, and leaves the dough to rise near the kitchen window. While she waits, she makes "
                    "tea and tells stories about the village where she grew up. By mid-morning the house smells "
                    "wonderful. When we arrive, the loaves are golden and still warm."),
    },
    {
        "id": "reading-advanced", "type": "reading", "level": "advanced", "difficulty": 3, "legacy": True,
        "focus": ["fluency", "maintenance"],
        "title": "Reading - Advanced: Speaking with Confidence",
        "description": "The final reading stage: long sentences and a natural conversational pace. Pause on purpose between ideas.",
        "target_wpm": 140,
        "passage": ("Public speaking is often described as one of the most common fears, yet it is also a skill that can "
                    "be developed through patient, deliberate practice. Successful speakers rarely begin with perfect "
                    "confidence; instead, they prepare thoroughly, breathe steadily, and accept that small hesitations "
                    "are a natural part of communication. Listeners generally value clarity and sincerity far more than speed."),
    },
    # ---------------- fluency: pacing + DAF + breathing (extra practice around the bracket tasks) ----------------
    {
        "id": "pacing-easy", "type": "pacing", "difficulty": 1, "focus": ["fluency"],
        "title": "Gentle Pacing - The Garden",
        "description": "Read along at a relaxed, steady pace. Follow the highlight - don't rush to keep up.",
        "target_wpm": 90,
        "passage": ("The morning sun rose slowly over the quiet garden. Birds moved from branch to branch, singing softly. "
                    "A gentle breeze passed through the leaves, and everything felt calm."),
    },
    {
        "id": "pacing-standard", "type": "pacing", "difficulty": 2, "focus": ["fluency", "maintenance"], "min_bracket": 4,
        "title": "Standard Pacing - The Market",
        "description": "Read at a natural conversational pace, staying with the highlighted word.",
        "target_wpm": 130,
        "passage": ("On Saturday mornings, the town market fills with colour and sound. Vendors call out the day's prices "
                    "while children weave between the stalls, chasing the smell of fresh bread and roasted nuts."),
    },
    {
        "id": "daf", "type": "daf", "difficulty": 2, "focus": ["fluency"], "min_bracket": 3,
        "title": "Delayed Auditory Feedback",
        "description": ("Speak while hearing your own voice played back with a short delay. Many people find it naturally "
                        "slows and smooths their rhythm. Use headphones."),
    },
    {
        "id": "calm-breathing", "type": "sustained_vowel", "difficulty": 1, "focus": ["fluency", "maintenance"],
        "title": "Calm Breathing - Easy Onset",
        "description": ("Breathe in slowly through your nose, then let the air out on a soft, gentle 'haaa'. "
                        "Keep it relaxed and smooth - no pushing. Repeat three times."),
        "target_seconds": 6,
    },
    # ---------------- motor speech (dysarthria): clear-speech ladder + loudness + phonation ----------------
    {
        "id": "clear-beginner", "type": "clear_speech", "level": "beginner", "difficulty": 1, "focus": ["motor_speech"],
        "title": "Clear Speech - Beginner: One Beat Each",
        "description": "Short phrases. Give every syllable its own beat and move your lips and tongue a little more than usual.",
        "target_wpm": 70,
        "passage": "Good morning. I want a cup of tea. Please pass the bread. The bus is late today. Thank you very much.",
    },
    {
        "id": "clear-intermediate", "type": "clear_speech", "level": "intermediate", "difficulty": 2, "focus": ["motor_speech"],
        "title": "Clear Speech - Intermediate: At the Shop",
        "description": "Everyday sentences. Breathe before each sentence and finish every word clearly.",
        "target_wpm": 95,
        "passage": ("I would like two kilos of rice and a bottle of milk. Do you have any fresh mangoes today? "
                    "How much does the big packet cost? I will pay with cash, thank you."),
    },
    {
        "id": "clear-advanced", "type": "clear_speech", "level": "advanced", "difficulty": 3, "focus": ["motor_speech"],
        "title": "Clear Speech - Advanced: Telling a Story",
        "description": "Longer sentences at a natural pace. Keep your voice strong right to the end of each sentence.",
        "target_wpm": 115,
        "passage": ("Last weekend we travelled to the hills to visit my cousin. The road was narrow and full of bends, "
                    "so the driver went slowly and carefully. When we finally arrived, the air was cool and fresh, "
                    "and my cousin had prepared a wonderful lunch for everyone."),
    },
    {
        "id": "loudness-phrases", "type": "loudness", "difficulty": 1, "focus": ["motor_speech"],
        "title": "Think Loud - Everyday Phrases",
        "description": "Say each phrase with a strong, healthy voice. Keep the loudness meter in the green zone.",
        "target_wpm": 80,
        "passage": "Hello, how are you? I need some help, please. Can you hear me? Let's go outside. I am ready now.",
    },
    {
        "id": "sustained-vowel", "type": "sustained_vowel", "difficulty": 1, "focus": ["motor_speech"],
        "title": "Breath Support - Long 'Ahh'",
        "description": "Take a deep breath and say 'ahh' in a strong, steady voice for as long as you comfortably can. Repeat three times.",
        "target_seconds": 10,
    },
    # ---------------- shared: picture description (legacy - replaced by the bracket picture tasks) ----------------
    {
        "id": "picture-park", "type": "picture", "difficulty": 1, "legacy": True,
        "focus": ["fluency", "speech_sounds", "maintenance", "motor_speech"],
        "title": "Picture Description - A Day at the Park",
        "description": "Look at the picture and describe what's happening in your own words. No rush.",
        "image_url": "/therapy/picture-1.jpg",
        "prompts": ["Who can you see in the park?", "What is the woman doing with the dog?",
                    "What are the children playing?", "What is the weather like?"],
    },
    {
        "id": "picture-kitchen", "type": "picture", "difficulty": 2, "legacy": True,
        "focus": ["fluency", "speech_sounds", "maintenance"],
        "title": "Picture Description - Cooking Together",
        "description": "Describe the kitchen scene: who is there, what each person is doing, and what they are making.",
        "image_url": "/therapy/picture-2.svg",
        "prompts": ["How many people are in the kitchen?", "What is each person doing?",
                    "What food can you see?", "What do you think will happen next?"],
    },
    {
        "id": "picture-beach", "type": "picture", "difficulty": 2, "legacy": True,
        "focus": ["fluency", "motor_speech", "maintenance"],
        "title": "Picture Description - At the Beach",
        "description": "Describe the beach scene in as much detail as you can, in full sentences.",
        "image_url": "/therapy/picture-3.svg",
        "prompts": ["What is the family building in the sand?", "What can you see in the sea and sky?",
                    "What is the man under the umbrella doing?", "Would you like to be there? Why?"],
    },
]

# ------------------------------------------------------------------------------- sound drills
# Keys match Component 1's TARGET_SOUNDS labels (scoring.py) so flagged sounds map directly.
SOUND_MATERIAL: dict[str, dict] = {
    "/s/": {"name": "S", "words": ["sun", "sock", "bus", "glass", "pencil", "seven", "house", "sister"],
            "phrases": ["a sunny sky", "six small socks", "sit on the bus", "a glass of juice"],
            "sentences": ["Sam sees seven seals by the sea.", "The bus stops outside our house.",
                          "My sister sells sweet lemon juice."]},
    "/z/": {"name": "Z", "words": ["zoo", "zip", "buzz", "nose", "rose", "zero", "easy", "lazy"],
            "phrases": ["a busy zoo", "zip it up", "a red rose", "the bees buzz"],
            "sentences": ["The zebra at the zoo is lazy.", "Bees buzz around the roses.", "Zara zips her blue coat."]},
    "/r/": {"name": "R", "words": ["red", "rain", "rabbit", "car", "tree", "carrot", "road", "orange"],
            "phrases": ["a red rose", "run in the rain", "a rabbit's carrot", "the green tree"],
            "sentences": ["The rabbit runs around the red car.", "Rain is falling on the road.",
                          "Rita reads a book under the tree."]},
    "/l/": {"name": "L", "words": ["lion", "leaf", "ball", "yellow", "lamp", "lemon", "bell", "light"],
            "phrases": ["a little lamb", "a yellow ball", "ring the bell", "a lemon leaf"],
            "sentences": ["Lily likes yellow lemons.", "The lion lies by the lake.", "Please turn on the light."]},
    "/θ/ (th)": {"name": "TH", "words": ["thumb", "three", "bath", "tooth", "think", "thank", "mouth", "earth"],
                 "phrases": ["three thin books", "thank you", "brush your teeth", "a hot bath"],
                 "sentences": ["I think there are three birds.", "Thank you for the thick blanket.",
                               "Brush your teeth after your bath."]},
    "/ʃ/ (sh)": {"name": "SH", "words": ["shoe", "ship", "fish", "wash", "shell", "sheep", "brush", "push"],
                 "phrases": ["a big ship", "wash the dish", "she shops", "a shiny shell"],
                 "sentences": ["She sells shells on the shore.", "Wash the fish in the dish.",
                               "The sheep is in the shade."]},
    "/tʃ/ (ch)": {"name": "CH", "words": ["chair", "cheese", "chip", "watch", "beach", "lunch", "teacher", "church"],
                  "phrases": ["a cheese sandwich", "lunch on the beach", "a red chair", "watch the match"],
                  "sentences": ["The teacher sits on a chair.", "We ate chips at lunch.", "Charlie watches the chickens."]},
    "/k/": {"name": "K", "words": ["cat", "cup", "kite", "book", "duck", "cake", "key", "basket"],
            "phrases": ["a cup of coffee", "fly a kite", "a black cat", "cut the cake"],
            "sentences": ["The cat sits in the basket.", "Kim flies a kite in the park.", "Can I have a cup of cocoa?"]},
    "/f/": {"name": "F", "words": ["fish", "fan", "leaf", "phone", "five", "coffee", "foot", "sofa"],
            "phrases": ["five funny fish", "a fast fan", "a phone call", "fall leaves"],
            "sentences": ["Five fish swim fast.", "Fred found his phone on the sofa.", "The leaf fell off the tree."]},
    "/v/": {"name": "V", "words": ["van", "vest", "five", "love", "seven", "cave", "vase", "river"],
            "phrases": ["a violet vase", "a very big van", "seven vests", "by the river"],
            "sentences": ["Vera drives a van.", "I love the view of the river.", "Seven violets are in the vase."]},
}
DEFAULT_SOUNDS = ["/s/", "/r/", "/l/"]
DRILL_LEVEL_KEY = {"beginner": "words", "intermediate": "phrases", "advanced": "sentences"}
DRILL_LEVEL_TITLE = {"beginner": "Words", "intermediate": "Phrases", "advanced": "Sentences"}


def sound_drills(flagged_sounds: list[str] | None) -> list[dict]:
    """One 3-rung drill ladder (words -> phrases -> sentences) for each flagged sound (max 3)."""
    sounds = [s for s in (flagged_sounds or []) if s in SOUND_MATERIAL][:3] or DEFAULT_SOUNDS
    drills = []
    for rank, sound in enumerate(sounds):
        mat = SOUND_MATERIAL[sound]
        slug = re.sub(r"[^a-z]", "", mat["name"].lower())
        for i, level in enumerate(LEVELS):
            drills.append({
                "id": f"sound-{slug}-{level}", "type": "sound_drill", "level": level, "difficulty": i + 1,
                "focus": ["speech_sounds"], "sound": sound, "sound_rank": rank,
                "title": f"Sound Practice '{mat['name']}' - {DRILL_LEVEL_TITLE[level]}",
                "description": (f"Say each item slowly and clearly, focusing on the '{mat['name']}' sound. "
                                "Tick the ones that felt clear."),
                "items": mat[DRILL_LEVEL_KEY[level]],
            })
    return drills


def exercises_for(flagged_sounds: list[str] | None) -> list[dict]:
    """The full bank a patient can use: bracket tasks + static exercises + drills for their flagged sounds."""
    return BRACKET_EXERCISES + EXERCISE_BANK + sound_drills(flagged_sounds)


def exercises_for_bracket(bracket: int) -> list[dict]:
    """The bracket's three core tasks (reading, picture, conversation)."""
    return bracket_exercises(bracket)


def suits_bracket(exercise: dict, bracket: int) -> bool:
    """Extra practice the bandit may add at this practice bracket (bracket tasks and legacy items excluded)."""
    if exercise.get("legacy") or exercise.get("bracket") is not None:
        return False
    return exercise.get("min_bracket", 1) <= bracket


def get_exercise(exercise_id: str, flagged_sounds: list[str] | None = None) -> dict | None:
    for ex in exercises_for(flagged_sounds):
        if ex["id"] == exercise_id:
            return ex
    # drills for sounds that are no longer flagged still resolve (old attempts)
    for ex in sound_drills(list(SOUND_MATERIAL)):
        if ex["id"] == exercise_id:
            return ex
    return None


def count_syllables(word: str) -> int:
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    count = len(re.findall(r"[aeiouy]+", word))
    if word.endswith("e") and not word.endswith(("le", "ee")) and count > 1:
        count -= 1
    return max(1, count)


def syllables_per_word(passage: str) -> float:
    words = passage.split()
    return sum(count_syllables(w) for w in words) / len(words) if words else 1.4
