import re

from app.therapy.schemas import ExerciseType, ReadingLevel, SeverityLevel, TherapyExercise, WordItem

# Starting reading level from the screening severity (Components 1–3).
# Fluency shaping works up a hierarchy, so more severe stuttering starts lower.
START_LEVEL = {
    SeverityLevel.SEVERE: "beginner",
    SeverityLevel.MODERATE: "beginner",
    SeverityLevel.MILD: "intermediate",
}

EXERCISE_BANK: list[TherapyExercise] = [
    # --- Graded reading (adaptive: beginner -> intermediate -> advanced) ---
    TherapyExercise(
        id="reading-beginner",
        type=ExerciseType.READING,
        level=ReadingLevel.BEGINNER,
        difficulty=1,
        title="Reading — Beginner: Sam and Max",
        description=(
            "Short, simple sentences. Read slowly and follow the highlight. "
            "Start each sentence with a soft, easy breath."
        ),
        target_wpm=80,
        passage=(
            "Sam has a red ball. He takes it to the park. "
            "The sun is warm and the sky is blue. "
            "Sam throws the ball to his dog, Max. "
            "Max runs fast and brings it back. "
            "They play until lunch time. "
            "Then they walk home together, happy and tired."
        ),
        recommended_for=[SeverityLevel.SEVERE, SeverityLevel.MODERATE, SeverityLevel.UNKNOWN],
    ),
    TherapyExercise(
        id="reading-intermediate",
        type=ExerciseType.READING,
        level=ReadingLevel.INTERMEDIATE,
        difficulty=2,
        title="Reading — Intermediate: Sunday Bread",
        description=(
            "Longer sentences with commas. Use the commas as natural places to "
            "pause and breathe before you continue."
        ),
        target_wpm=110,
        passage=(
            "Every Sunday, my grandmother bakes bread for the whole family. "
            "She wakes up early, mixes flour, water and yeast, and leaves the dough "
            "to rise near the kitchen window. While she waits, she makes tea and "
            "tells stories about the village where she grew up. By mid-morning the "
            "house smells wonderful. When we arrive, the loaves are golden and still "
            "warm. We sit around the table, share the bread with butter and honey, "
            "and talk about our week. These simple mornings are some of my favourite memories."
        ),
        recommended_for=[SeverityLevel.MODERATE, SeverityLevel.MILD, SeverityLevel.UNKNOWN],
    ),
    TherapyExercise(
        id="reading-advanced",
        type=ExerciseType.READING,
        level=ReadingLevel.ADVANCED,
        difficulty=3,
        title="Reading — Advanced (Final Stage): Speaking with Confidence",
        description=(
            "The final reading stage: long sentences, harder words and a natural "
            "conversational pace. Pause on purpose between ideas."
        ),
        target_wpm=140,
        passage=(
            "Public speaking is often described as one of the most common fears, yet "
            "it is also a skill that can be developed through patient, deliberate "
            "practice. Successful speakers rarely begin with perfect confidence; "
            "instead, they prepare thoroughly, breathe steadily, and accept that small "
            "hesitations are a natural part of communication. Particularly in "
            "professional situations, such as presentations, interviews, or telephone "
            "conversations, it helps to pause purposefully between ideas rather than "
            "rushing to fill every silence. Listeners generally value clarity and "
            "sincerity far more than speed. Remember that every conversation is an "
            "opportunity, not a performance to be judged. By practising regularly, "
            "celebrating gradual progress, and using techniques like gentle onsets and "
            "controlled pacing, you can communicate your thoughts clearly, calmly, and "
            "with genuine confidence."
        ),
        recommended_for=[SeverityLevel.MILD, SeverityLevel.UNKNOWN],
    ),
    # --- Pacing ---
    TherapyExercise(
        id="pacing-easy-1",
        type=ExerciseType.PACING,
        difficulty=1,
        title="Gentle Pacing — The Garden",
        description="Read along at a relaxed, steady pace. Follow the highlight — don't rush to keep up.",
        target_wpm=90,
        passage=(
            "The morning sun rose slowly over the quiet garden. "
            "Birds moved from branch to branch, singing softly. "
            "A gentle breeze passed through the leaves, and everything felt calm."
        ),
        recommended_for=[SeverityLevel.SEVERE, SeverityLevel.MODERATE, SeverityLevel.UNKNOWN],
    ),
    TherapyExercise(
        id="pacing-standard-1",
        type=ExerciseType.PACING,
        difficulty=2,
        title="Standard Pacing — The Market",
        description="Read at a natural conversational pace, staying with the highlighted word.",
        target_wpm=130,
        passage=(
            "On Saturday mornings, the town market fills with color and sound. "
            "Vendors call out the day's prices while children weave between the stalls, "
            "chasing the smell of fresh bread and roasted chestnuts."
        ),
        recommended_for=[SeverityLevel.MILD, SeverityLevel.MODERATE],
    ),
    # --- DAF ---
    TherapyExercise(
        id="daf-1",
        type=ExerciseType.DAF,
        difficulty=2,
        title="Delayed Auditory Feedback",
        description=(
            "Speak normally while hearing your own voice played back with a short delay. "
            "This technique is commonly used to help smooth out speech rhythm. "
            "Start with a short delay and increase gradually if it feels comfortable."
        ),
        recommended_for=[SeverityLevel.SEVERE, SeverityLevel.MODERATE],
    ),
    # --- Picture description ---
    TherapyExercise(
        id="picture-1",
        type=ExerciseType.PICTURE,
        difficulty=1,
        title="Picture Description — A Day at the Park",
        description=(
            "Look at the picture and describe what's happening in your own words. "
            "There's no rush — take as long as you need."
        ),
        image_url="/stimuli/images/picture-1.jpg",
        prompts=[
            "Who can you see in the park?",
            "What is the woman doing with the dog?",
            "What are the children playing?",
            "What is the weather like?",
        ],
        example_sentences=[
            "A woman is walking her brown dog on the path.",
            "A boy is kicking a black and white football.",
            "A girl is riding a blue bike across the grass.",
            "A man is sitting on a bench and reading a book.",
            "The sun is shining and the trees are green.",
        ],
        recommended_for=[SeverityLevel.MILD, SeverityLevel.MODERATE, SeverityLevel.UNKNOWN],
    ),
    TherapyExercise(
        id="picture-2",
        type=ExerciseType.PICTURE,
        difficulty=2,
        title="Picture Description — Cooking Together",
        description=(
            "Describe the kitchen scene: who is there, what each person is doing, "
            "and what you think they are making."
        ),
        image_url="/stimuli/images/picture-2.svg",
        prompts=[
            "How many people are in the kitchen?",
            "What is each person doing?",
            "What food can you see on the table?",
            "What do you think will happen next?",
        ],
        example_sentences=[
            "A family is cooking together in the kitchen.",
            "The mother is stirring soup in a red pot.",
            "The father is cutting orange carrots on the table.",
            "The child is mixing something in a white bowl.",
            "An orange cat is lying on the floor.",
        ],
        recommended_for=[SeverityLevel.MILD, SeverityLevel.MODERATE, SeverityLevel.UNKNOWN],
    ),
    TherapyExercise(
        id="picture-3",
        type=ExerciseType.PICTURE,
        difficulty=2,
        title="Picture Description — At the Beach",
        description=(
            "Describe the beach scene in as much detail as you can. Try to use full "
            "sentences and pause naturally between ideas."
        ),
        image_url="/stimuli/images/picture-3.svg",
        prompts=[
            "What is the family building in the sand?",
            "What can you see in the sea and in the sky?",
            "What is the man under the umbrella doing?",
            "Would you like to be there? Why?",
        ],
        example_sentences=[
            "Two children are building a sandcastle on the beach.",
            "A girl is flying an orange kite in the sky.",
            "A man is reading a book under a pink umbrella.",
            "A white and pink boat is sailing on the blue sea.",
            "There is a small red crab on the sand.",
        ],
        recommended_for=[SeverityLevel.MILD, SeverityLevel.MODERATE, SeverityLevel.UNKNOWN],
    ),
]



def count_syllables(word: str) -> int:
    """Vowel-group heuristic: counts groups of vowels, ignoring a silent final 'e'."""
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and not word.endswith(("le", "ee")) and count > 1:
        count -= 1
    return max(1, count)


def syllables_per_word(passage: str) -> float:
    """Measured from the passage itself, so the words/min conversion is
    derived from the text being read rather than a fixed constant."""
    words = passage.split()
    return sum(count_syllables(w) for w in words) / len(words) if words else 1.4


# --- Word practice: a graded word ladder for children ----------------------
#
# Children can't read long passages, so they practise single words on picture
# cards. The order follows speech-therapy development rules:
#   * sound age — early sounds (p b m n t d w h) before middle (k g f y ng)
#     before late (s z sh ch j l r th v);
#   * length — 1 syllable, then 2, then 3+;
#   * consonant clusters (sp, tr, bl, str) are harder;
#   * for stuttering, words starting with a vowel or a smooth sound
#     (m n s f l) are easiest; stop sounds (p b t d k g) come later.
# After level 7 the ladder continues with a phrase stage: two-word phrases,
# short sentences, then tongue twisters. Pictures are emoji (no image files).

WORD_LEVEL_COUNT = 7  # single-word levels; the phrase stage follows
WORD_LADDER_SIZE = 10  # 7 word levels + 3 phrase stages

_VOWELS = "aeiou"
_SMOOTH = "mnslfwhy"
_STOPS = "pbtdkgc"
_CLUSTERS = ("spl", "spr", "str", "scr", "sp", "st", "sn", "sl", "sm", "sw", "sk",
             "tr", "dr", "pr", "br", "fr", "gr", "cr", "pl", "bl", "fl", "gl", "cl")


def word_tip(text: str) -> str:
    """A fluency tip from how the word starts."""
    word = text.lower().lstrip("'\"")
    if word.startswith(_CLUSTERS):
        return "Slide the sounds together slowly"
    if word[:1] in _VOWELS:
        return "Start softly with an easy breath"
    if word[:1] in _SMOOTH:
        return f"Stretch the first sound gently: {word[0] * 3}-{word[1:]}"
    if word[:1] in _STOPS:
        return "Light touch on the first sound"
    return "Say it slowly and smoothly"


def _cards(items: list[tuple[str, int, str]]) -> list[WordItem]:
    return [WordItem(text=t, syllables=s, emoji=e, tip=word_tip(t)) for t, s, e in items]


_ALL = [SeverityLevel.MILD, SeverityLevel.MODERATE, SeverityLevel.SEVERE, SeverityLevel.UNKNOWN]

# (word level, id suffix, title, description, difficulty, cards: (text, syllables, emoji))
_WORD_LADDER = [
    (1, "1", "Easy start", "Words that begin with an open vowel or a smooth sound — the easiest to start.", 1, [
        ("eye", 1, "👁️"), ("egg", 1, "🥚"), ("owl", 1, "🦉"), ("arm", 1, "💪"), ("moon", 1, "🌙"),
        ("me", 1, "🙋"), ("no", 1, "🙅"), ("more", 1, "➕"), ("sun", 1, "☀️"), ("fish", 1, "🐟"),
    ]),
    (2, "2", "Early sounds", "Short words with the first sounds children learn: b, m, d, h, p, t.", 1, [
        ("ball", 1, "⚽"), ("bee", 1, "🐝"), ("map", 1, "🗺️"), ("mum", 1, "👩"), ("dog", 1, "🐶"),
        ("hat", 1, "🎩"), ("pie", 1, "🥧"), ("top", 1, "🔝"), ("bed", 1, "🛏️"), ("two", 1, "2️⃣"),
    ]),
    (3, "3", "Two syllables", "Two-beat words made from early sounds. Keep the voice on between the beats.", 1, [
        ("baby", 2, "👶"), ("mummy", 2, "👩‍👧"), ("puppy", 2, "🐕"), ("happy", 2, "😄"), ("teddy", 2, "🧸"),
        ("water", 2, "💧"), ("window", 2, "🪟"), ("button", 2, "🔘"), ("honey", 2, "🍯"), ("tummy", 2, "😋"),
    ]),
    (4, "4", "Middle sounds", "Words with k, g and f sounds, including some two-syllable words.", 2, [
        ("cat", 1, "🐱"), ("cup", 1, "🥤"), ("cake", 1, "🎂"), ("goat", 1, "🐐"), ("fan", 1, "🪭"),
        ("kite", 1, "🪁"), ("coffee", 2, "☕"), ("cookie", 2, "🍪"), ("finger", 2, "👆"), ("garden", 2, "🌷"),
    ]),
    (5, "5", "Late sounds", "Words with the later sounds: s, z, sh, ch, j, l, r, th and v.", 2, [
        ("sock", 1, "🧦"), ("zoo", 1, "🦓"), ("shoe", 1, "👟"), ("chair", 1, "🪑"), ("jam", 1, "🫙"),
        ("lion", 2, "🦁"), ("rabbit", 2, "🐰"), ("thumb", 1, "👍"), ("van", 1, "🚐"), ("red", 1, "🔴"),
    ]),
    (6, "6", "Clusters", "Two consonants together at the start (sp, st, tr, bl…). Slide them slowly.", 3, [
        ("spoon", 1, "🥄"), ("star", 1, "⭐"), ("snake", 1, "🐍"), ("tree", 1, "🌳"), ("train", 1, "🚆"),
        ("frog", 1, "🐸"), ("blue", 1, "🔵"), ("plane", 1, "✈️"), ("flower", 2, "🌸"), ("sleep", 1, "😴"),
    ]),
    (7, "7", "Long and tricky", "Long words with three or more syllables. Say them beat by beat.", 3, [
        ("butterfly", 3, "🦋"), ("elephant", 3, "🐘"), ("umbrella", 3, "☂️"), ("banana", 3, "🍌"),
        ("tomato", 3, "🍅"), ("helicopter", 4, "🚁"), ("caterpillar", 4, "🐛"), ("strawberry", 3, "🍓"),
        ("ambulance", 3, "🚑"), ("hippopotamus", 5, "🦛"),
    ]),
    (8, "phrases", "Two-word phrases", "Join two words with one smooth breath.", 3, [
        ("big ball", 2, "⚽"), ("red car", 2, "🚗"), ("my dog", 2, "🐶"), ("hot sun", 2, "☀️"),
        ("blue sky", 2, "🌤️"), ("little fish", 3, "🐟"),
    ]),
    (9, "sentences", "Short sentences", "Short sentences. Keep the words flowing like one long word.", 3, [
        ("I see a cat.", 4, "🐱"), ("The sun is hot.", 4, "☀️"), ("My dog can run.", 4, "🐶"),
        ("The bird can fly.", 4, "🐦"), ("I like red apples.", 5, "🍎"), ("We go to school.", 4, "🏫"),
    ]),
    (10, "twisters", "Tongue twisters", "Fun tongue twisters. Slow is the secret — speed doesn't matter.", 3, [
        ("Red lorry, yellow lorry", 6, "🚚"), ("Big black bug", 3, "🐞"), ("She sells sea shells", 4, "🐚"),
        ("Fresh fried fish", 3, "🐟"), ("Six slippery snails", 5, "🐌"),
    ]),
]


def word_stage_label(word_level: int) -> str:
    """'Word Level 3' for 1–7, 'Phrase Stage 2' for the three phrase stages."""
    if word_level <= WORD_LEVEL_COUNT:
        return f"Word Level {word_level}"
    return f"Phrase Stage {word_level - WORD_LEVEL_COUNT}"


WORD_EXERCISES: list[TherapyExercise] = [
    TherapyExercise(
        id=f"words-{suffix}",
        type=ExerciseType.WORDS,
        word_level=word_level,
        difficulty=difficulty,
        title=f"{word_stage_label(word_level)} — {name}",
        description=description,
        words=_cards(cards),
        recommended_for=_ALL,
    )
    for word_level, suffix, name, description, difficulty, cards in _WORD_LADDER
] + [
    TherapyExercise(
        id="words-sri-lanka",
        type=ExerciseType.WORDS,
        word_level=None,
        difficulty=2,
        title="Bonus — Sri Lankan words",
        description="Words from home: fruit, food and animals from Sri Lanka. Open any time.",
        words=_cards([
            ("mango", 2, "🥭"), ("rice", 1, "🍚"), ("tea", 1, "🍵"), ("coconut", 3, "🥥"), ("papaya", 3, "🍈"),
            ("tuk-tuk", 2, "🛺"), ("peacock", 2, "🦚"), ("elephant", 3, "🐘"), ("pineapple", 3, "🍍"),
        ]),
        recommended_for=_ALL,
    ),
]

# Word exercises go after the original bank, so the planner simulation (which
# uses the original exercises) and existing arm indices stay unchanged.
EXERCISE_BANK.extend(WORD_EXERCISES)
WORD_LADDER_IDS = {ex.word_level: ex.id for ex in WORD_EXERCISES if ex.word_level is not None}

EXERCISES_BY_ID: dict[str, TherapyExercise] = {ex.id: ex for ex in EXERCISE_BANK}


def get_exercise(exercise_id: str) -> TherapyExercise | None:
    return EXERCISES_BY_ID.get(exercise_id)


def recommend_exercises(severity: SeverityLevel) -> list[TherapyExercise]:
    matches = [ex for ex in EXERCISE_BANK if severity in ex.recommended_for]
    return matches if matches else EXERCISE_BANK
