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
        title="Reading — Beginner: Morning News",
        description=(
            "A short news-style paragraph. Read slowly with the highlight and start "
            "each sentence with a soft, easy breath."
        ),
        target_wpm=120,
        passage=(
            "Colombo will have light rain this afternoon, the weather office said. "
            "Trains on the coastal line are running on time. "
            "A new bus service between Kandy and Nuwara Eliya starts next Monday. "
            "Tea prices rose slightly at this week's auction. "
            "Schools reopen on the first of next month."
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

# --- Practice by age group ----------------------------------------------------------
#
# Every age group has its own Beginner -> Intermediate -> Advanced ladder (an
# exercise is on a ladder when it has a `level`); a level can hold several
# exercises, and the level engine counts only the student's own group.
#
#   child (6–13):  picture words -> phrases & short sentences -> a short story
#   teen (14–20):  school/hobby reading -> class presentations -> role-plays
#   adult (21+):   news reading -> everyday role-plays -> interviews & work talks
#
# Role-plays show a situation and the lines the other person says; the student
# answers out loud (recorded like picture description).

_KIDS, _TEENS, _ADULTS = ["child"], ["teen"], ["adult"]


def _roleplay(id, groups, level, difficulty, title, situation, lines, examples):
    return TherapyExercise(
        id=id, type=ExerciseType.ROLEPLAY, level=level, difficulty=difficulty, age_groups=groups,
        title=title, description=situation, prompts=lines, example_sentences=examples, recommended_for=_ALL,
    )


AGE_EXERCISES: list[TherapyExercise] = [
    # --- Child ladder ---
    TherapyExercise(
        id="child-words", type=ExerciseType.WORDS, level=ReadingLevel.BEGINNER, difficulty=1, age_groups=_KIDS,
        title="Kids Beginner — Picture words",
        description="Look at the picture, press Listen, then say the word slowly. Easy, soft starts!",
        words=_cards([
            ("eye", 1, "👁️"), ("egg", 1, "🥚"), ("moon", 1, "🌙"), ("sun", 1, "☀️"),
            ("ball", 1, "⚽"), ("dog", 1, "🐶"), ("cat", 1, "🐱"), ("cup", 1, "🥤"),
        ]),
        recommended_for=_ALL,
    ),
    TherapyExercise(
        id="child-phrases", type=ExerciseType.WORDS, level=ReadingLevel.INTERMEDIATE, difficulty=2, age_groups=_KIDS,
        title="Kids Intermediate — Little phrases",
        description="Two words, then short sentences. Say them in one smooth breath.",
        words=_cards([
            ("big ball", 2, "⚽"), ("red car", 2, "🚗"), ("my dog", 2, "🐶"), ("hot sun", 2, "☀️"),
            ("I see a cat.", 4, "🐱"), ("The sun is hot.", 4, "☀️"), ("I like mangoes.", 4, "🥭"),
            ("We ride a tuk-tuk.", 5, "🛺"),
        ]),
        recommended_for=_ALL,
    ),
    TherapyExercise(
        id="child-story", type=ExerciseType.READING, level=ReadingLevel.ADVANCED, difficulty=3, age_groups=_KIDS,
        title="Kids Advanced — Sam and Max (story + tongue twister)",
        description="A tiny story to read slowly with the highlight. Finish with a fun tongue twister!",
        target_wpm=70,
        passage=(
            "Sam has a red ball. He throws it to his dog, Max. "
            "Max runs fast and brings it back. They are happy and tired. "
            "Red lorry, yellow lorry, red lorry, yellow lorry!"
        ),
        recommended_for=_ALL,
    ),
    TherapyExercise(
        id="child-pacing", type=ExerciseType.PACING, difficulty=1, age_groups=_KIDS,
        title="Slow Snail Pacing — The Little Boat",
        description="Read like a slow snail 🐌 — follow the yellow word and don't rush.",
        target_wpm=70,
        passage="A little boat sails on the sea. The wind is soft. A fish jumps up. Splash! The boat goes home.",
        recommended_for=_ALL,
    ),
    TherapyExercise(
        id="child-pacing-2", type=ExerciseType.PACING, difficulty=1, age_groups=_KIDS,
        title="Slow Snail Pacing — The Sleepy Cat",
        description="Read like a slow snail 🐌 — one word at a time, nice and soft.",
        target_wpm=65,
        passage="My cat is sleepy. She sits on the mat. She licks her paw. Then she naps in the sun. Shh!",
        recommended_for=_ALL,
    ),
    TherapyExercise(
        id="child-pacing-3", type=ExerciseType.PACING, difficulty=1, age_groups=_KIDS,
        title="Slow Snail Pacing — The Tuk-Tuk Ride",
        description="A slow snail ride 🐌🛺 — follow the yellow word and keep your voice gentle.",
        target_wpm=75,
        passage=(
            "We ride in a red tuk-tuk. It goes beep, beep! We see a big elephant. "
            "We wave to the man. Then we go home for rice."
        ),
        recommended_for=_ALL,
    ),
    # --- Picture description by age ---
    TherapyExercise(
        id="picture-teen-canteen", type=ExerciseType.PICTURE, difficulty=2, age_groups=_TEENS,
        title="Picture Description — The School Canteen",
        description=(
            "Describe what is happening in the school canteen at interval. Talk about the people, "
            "what they are doing and what you think happens next."
        ),
        image_url="/stimuli/images/picture-teen-canteen.svg",
        prompts=[
            "What are the students in the queue waiting for?",
            "What is each student at the table doing?",
            "What happened to the boy near the front, and what should he do now?",
            "What is the notice board about? Would you take part?",
        ],
        example_sentences=[
            "Two students are waiting in the queue to buy fish buns and tea.",
            "One girl at the table is laughing, another is reading a book, and a boy is drinking water.",
            "A boy has spilled his drink on the floor, so he should tell the canteen aunty and clean it up.",
            "The notice says the sports meet is on Friday at eight in the morning.",
            "It is half past ten, so it must be the interval.",
        ],
        recommended_for=_ALL,
    ),
    TherapyExercise(
        id="picture-teen-cricket", type=ExerciseType.PICTURE, difficulty=2, age_groups=_TEENS,
        title="Picture Description — The Inter-House Cricket Match",
        description=(
            "Describe the cricket match like a sports commentator. Explain who is doing what "
            "and how the game is going."
        ),
        image_url="/stimuli/images/picture-teen-cricket.svg",
        prompts=[
            "What is the batsman doing right now?",
            "Who else can you see on the field, and what are their jobs?",
            "What does the scoreboard tell you? Is Blue House winning?",
            "How are the students under the tree feeling? How do you know?",
        ],
        example_sentences=[
            "The batsman is swinging his bat at the red ball.",
            "The bowler has just bowled, the wicketkeeper is waiting behind the stumps, and the umpire is watching.",
            "Blue House has scored 124 runs for 3 wickets after 18 overs, and they need 150 to win.",
            "The students are cheering and holding a banner that says Go Blue House.",
            "If they hit a few more fours, they can win the match.",
        ],
        recommended_for=_ALL,
    ),
    TherapyExercise(
        id="picture-adult-market", type=ExerciseType.PICTURE, difficulty=3, age_groups=_ADULTS,
        title="Picture Description (Advanced) — A Busy Market Street",
        description=(
            "A detailed, busy scene. Describe it in an organised way — from left to right, or from the "
            "street to the shops — then explain what problems people might be facing and why."
        ),
        image_url="/stimuli/images/picture-adult-market.svg",
        prompts=[
            "Describe the scene in order, as if you were explaining it to someone on the phone.",
            "What is the traffic policeman doing, and why is it needed here?",
            "Why do you think the man on the right is running?",
            "If you needed medicine and a new phone charger, where would you go and how would you get there?",
            "What could be done to make this street safer or less crowded?",
        ],
        example_sentences=[
            "This is a crowded market street in the morning, with shops on both sides and heavy traffic in the middle.",
            "The traffic policeman is blowing his whistle and directing the vehicles, because the crossing is very busy.",
            "The man is probably running to catch the 138 bus to Kottawa before it leaves.",
            "I would go to the pharmacy first, then walk across the zebra crossing to Mobile World.",
            "A separate lane for buses and fewer vendors on the road would make it safer for pedestrians.",
        ],
        recommended_for=_ALL,
    ),
    TherapyExercise(
        id="picture-adult-station", type=ExerciseType.PICTURE, difficulty=3, age_groups=_ADULTS,
        title="Picture Description (Advanced) — Railway Station at Rush Hour",
        description=(
            "A complex scene with information to read and situations to explain. Describe what is "
            "happening, use the details to make sensible guesses, and say what you would do."
        ),
        image_url="/stimuli/images/picture-adult-station.svg",
        prompts=[
            "What time is it, and what does the departure board tell travellers?",
            "Why do you think the man near the front is checking his watch?",
            "Describe three different people on the platform and what they are doing.",
            "If you were travelling to Badulla, what would you do now, and why?",
            "How could the station make the delay less stressful for passengers?",
        ],
        example_sentences=[
            "It is a quarter to six in the evening, and the board shows the Badulla train is delayed by twenty minutes.",
            "He is probably worried because his train is late and he has somewhere important to be.",
            "A mother is holding her child's hand, an elderly man is resting on a bench, and a vendor is selling peanuts.",
            "I would buy my ticket now, find a seat, and call home to say I will be late.",
            "They could make clear announcements and show the new departure time on the board.",
        ],
        recommended_for=_ALL,
    ),
    # --- Teen ladder ---
    TherapyExercise(
        id="teen-school", type=ExerciseType.READING, level=ReadingLevel.BEGINNER, difficulty=1, age_groups=_TEENS,
        title="Teen Beginner — A Day at School",
        description="A short paragraph about school life. Read with the highlight and start each sentence softly.",
        target_wpm=105,
        passage=(
            "School starts at half past seven, so I leave home early with my friends. "
            "We usually talk about cricket or a new song on the way. "
            "The first lesson is maths, which is hard but useful. "
            "At the interval we share snacks in the canteen. "
            "After school I stay for drama practice twice a week."
        ),
        recommended_for=_ALL,
    ),
    TherapyExercise(
        id="teen-hobby", type=ExerciseType.READING, level=ReadingLevel.BEGINNER, difficulty=1, age_groups=_TEENS,
        title="Teen Beginner — My Weekend Hobby",
        description="A short paragraph about a hobby. Pause at the commas and keep a steady pace.",
        target_wpm=110,
        passage=(
            "On Saturdays I play cricket with my cousins in the ground near our house. "
            "We do not have proper stumps, so we use a chair and a few bricks. "
            "My younger brother always wants to bat first, and we always let him. "
            "When it gets too hot, we stop for king coconut water and argue about the score."
        ),
        recommended_for=_ALL,
    ),
    _roleplay("teen-present-self", _TEENS, ReadingLevel.INTERMEDIATE, 2, "Teen Intermediate — Introduce yourself to the class",
              "It's the first day with a new class teacher. Stand up and introduce yourself for about one minute.",
              ["What is your name and which school did you come from?", "What do you like doing after school?",
               "Which subject do you enjoy most, and why?", "What is one thing you want to do this year?"],
              ["Good morning everyone, my name is Dinuli and I came from a school in Kandy.",
               "After school I like playing badminton and drawing.",
               "My favourite subject is science, because I like doing experiments.",
               "This year I want to join the debating team."]),
    _roleplay("teen-present-sport", _TEENS, ReadingLevel.INTERMEDIATE, 2, "Teen Intermediate — My favourite sport (1-minute talk)",
              "Give a one-minute class presentation about your favourite sport.",
              ["Which sport is it, and how did you start?", "What are the basic rules?",
               "Who is a player you admire?", "Why should others try it?"],
              ["My favourite sport is cricket. I started playing with my father when I was seven.",
               "Each team bats and bowls, and the team with more runs wins.",
               "I admire Kumar Sangakkara because he was calm under pressure.",
               "Everyone should try it — it teaches teamwork and patience."]),
    _roleplay("teen-roleplay-teacher", _TEENS, ReadingLevel.ADVANCED, 3, "Teen Advanced — Answering the teacher",
              "Your teacher asks you a question in front of the class. Answer clearly in two or three sentences.",
              ["Teacher: Can you explain what photosynthesis is?", "Teacher: Why do you think it's important?",
               "Teacher: Can you give an example from everyday life?"],
              ["Photosynthesis is how plants make food using sunlight, water and carbon dioxide.",
               "It's important because it gives us oxygen and food.",
               "For example, the paddy fields need sunlight to grow rice."]),
    _roleplay("teen-roleplay-food", _TEENS, ReadingLevel.ADVANCED, 3, "Teen Advanced — Ordering kottu with friends",
              "You're at a kottu stall with friends and it's your turn to order for everyone.",
              ["Seller: What would you like?", "Seller: Chicken or vegetable? Spicy?",
               "Seller: Anything to drink?", "Seller: That's 2,400 rupees."],
              ["Can we have three chicken kottu and one vegetable kottu, please?",
               "Medium spicy for all of them, please.", "Four bottles of water, thank you.",
               "Here you are. Can we have the bill, please?"]),
    _roleplay("teen-roleplay-friend", _TEENS, ReadingLevel.ADVANCED, 3, "Teen Advanced — Phone call to a friend",
              "Call a friend to plan going to the cinema this weekend.",
              ["Friend: Hello? Who's this?", "Friend: Which film do you want to see?",
               "Friend: What time should we meet?", "Friend: How are we getting there?"],
              ["Hi, it's Kavindu. Are you free on Saturday?", "Let's watch the new animated film.",
               "The show starts at four, so let's meet at half past three.", "We can take a tuk-tuk from my place."]),
    _roleplay("teen-roleplay-interview", _TEENS, ReadingLevel.ADVANCED, 3, "Teen Advanced — University admission interview",
              "You are being interviewed for a place on a university course. Answer each question calmly.",
              ["Interviewer: Why do you want to study this course?", "Interviewer: Tell us about a project you are proud of.",
               "Interviewer: How do you handle pressure before exams?", "Interviewer: Do you have any questions for us?"],
              ["I want to study engineering because I enjoy solving practical problems.",
               "I built a small solar lamp for our science exhibition.",
               "I make a timetable and take short breaks so I don't panic.",
               "Yes — are there chances to do research in the first year?"]),
    # --- Adult ladder (reading-beginner/intermediate/advanced are on it too) ---
    _roleplay("adult-roleplay-doctor", _ADULTS, ReadingLevel.INTERMEDIATE, 2, "Adult Intermediate — Booking a doctor's appointment",
              "Phone a clinic to book an appointment with a doctor.",
              ["Receptionist: Good morning, City Medical Centre. How can I help?", "Receptionist: Which doctor would you like to see?",
               "Receptionist: Is Thursday at 5.30 suitable?", "Receptionist: Can I have your name and phone number?"],
              ["Good morning, I'd like to book an appointment, please.",
               "I'd like to see Dr. Fernando, the general physician.",
               "Thursday at 5.30 is fine, thank you.",
               "My name is Sunil Perera and my number is 077 123 4567."]),
    _roleplay("adult-roleplay-restaurant", _ADULTS, ReadingLevel.INTERMEDIATE, 2, "Adult Intermediate — Ordering at a restaurant",
              "You're at a restaurant with a colleague. Order for both of you and ask about the bill.",
              ["Waiter: Are you ready to order?", "Waiter: Would you like rice and curry or fried rice?",
               "Waiter: Anything to drink?", "Waiter: Would you like the bill now?"],
              ["Yes, we're ready, thank you.", "Two rice and curry, please — one with fish and one vegetarian.",
               "Two lime juices, please.", "Yes please, and can I pay by card?"]),
    _roleplay("adult-roleplay-work-intro", _ADULTS, ReadingLevel.INTERMEDIATE, 2, "Adult Intermediate — Introducing yourself at work",
              "It's your first day at a new office. Introduce yourself to your team at the morning meeting.",
              ["Manager: Everyone, this is our new team member.", "Colleague: What did you do before joining us?",
               "Colleague: What will you be working on?", "Manager: Anything else you'd like to share?"],
              ["Good morning, everyone. I'm Nadeesha and I've joined as an accountant.",
               "Before this, I worked at a bank in Colombo for three years.",
               "I'll be handling the monthly reports and supplier payments.",
               "I'm looking forward to working with you all."]),
    _roleplay("adult-interview-about", _ADULTS, ReadingLevel.ADVANCED, 3, "Adult Advanced — Job interview: Tell me about yourself",
              "A job interview for a role you'd like. Answer the interviewer's questions in full sentences.",
              ["Interviewer: Tell me about yourself.", "Interviewer: Why do you want this job?",
               "Interviewer: Where do you see yourself in five years?"],
              ["I'm a marketing graduate with two years of experience in digital campaigns.",
               "This role matches my skills, and I admire your company's work in tourism.",
               "In five years I'd like to be leading a small team."]),
    _roleplay("adult-interview-strengths", _ADULTS, ReadingLevel.ADVANCED, 3, "Adult Advanced — Job interview: Strengths and weaknesses",
              "The interviewer asks about your strengths and how you handle challenges.",
              ["Interviewer: What are your strengths?", "Interviewer: What is one weakness you're working on?",
               "Interviewer: Tell me about a difficult situation at work and what you did."],
              ["I'm organised, and I stay calm when deadlines are close.",
               "I used to avoid speaking in meetings, so I now prepare two points in advance.",
               "When a supplier delivered late, I rearranged the schedule and kept the client informed."]),
    _roleplay("adult-presentation", _ADULTS, ReadingLevel.ADVANCED, 3, "Adult Advanced — A 2-minute work presentation",
              "Present a short update to your team about a project. Aim for about two minutes.",
              ["What is the project and why does it matter?", "What has been done so far?",
               "What problems came up and how were they solved?", "What happens next, and what do you need from the team?"],
              ["Today I'll update you on the new customer feedback system.",
               "We have collected 300 responses in the first month.",
               "Response rates were low at first, so we added SMS reminders.",
               "Next month we'll share a report, and I'd like two volunteers to review it."]),
    _roleplay("adult-meeting", _ADULTS, ReadingLevel.ADVANCED, 3, "Adult Advanced — Speaking up in a meeting",
              "In a team meeting, the manager asks for opinions. Give your view and a suggestion.",
              ["Manager: Does anyone have concerns about the new schedule?", "Colleague: I think it will work fine.",
               "Manager: What would you suggest instead?"],
              ["I have one concern: the Friday deadline clashes with month-end closing.",
               "I agree it can work, but we may need one more day.",
               "Could we move the deadline to Monday and review progress on Thursday?"]),
]

# Which age groups each existing exercise suits. Original readings form the
# adult ladder; pacing speeds are personalised per group (PACE_RANGE).
_AGE_TAGS = {
    "reading-beginner": _ADULTS, "reading-intermediate": _ADULTS, "reading-advanced": _ADULTS,
    "pacing-easy-1": ["teen", "adult"], "pacing-standard-1": ["teen", "adult"],
    "daf-1": ["teen", "adult"],
    "picture-1": _KIDS, "picture-2": _KIDS, "picture-3": ["teen", "adult"],
}
for _ex in EXERCISE_BANK:
    if _ex.id in _AGE_TAGS:
        _ex.age_groups = _AGE_TAGS[_ex.id]
    elif _ex.type == ExerciseType.WORDS:
        _ex.age_groups = _KIDS  # the word ladder and the Sri Lankan bonus set
EXERCISE_BANK.extend(AGE_EXERCISES)

# Comfortable highlight speeds (words/min) for each age group.
PACE_RANGE = {"child": (60, 80), "teen": (100, 130), "adult": (120, 150)}


def exercises_for(age_group: str) -> list[TherapyExercise]:
    return [ex for ex in EXERCISE_BANK if age_group in ex.age_groups]

EXERCISES_BY_ID: dict[str, TherapyExercise] = {ex.id: ex for ex in EXERCISE_BANK}


def get_exercise(exercise_id: str) -> TherapyExercise | None:
    return EXERCISES_BY_ID.get(exercise_id)


def recommend_exercises(severity: SeverityLevel) -> list[TherapyExercise]:
    matches = [ex for ex in EXERCISE_BANK if severity in ex.recommended_for]
    return matches if matches else EXERCISE_BANK
