import re

from app.therapy.schemas import ExerciseType, ReadingLevel, SeverityLevel, TherapyExercise

ALL_SEVERITIES = [
    SeverityLevel.MILD,
    SeverityLevel.MODERATE,
    SeverityLevel.SEVERE,
    SeverityLevel.UNKNOWN,
]

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
        recommended_for=ALL_SEVERITIES,
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
        recommended_for=ALL_SEVERITIES,
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
        recommended_for=ALL_SEVERITIES,
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
        recommended_for=[SeverityLevel.MILD, SeverityLevel.MODERATE, SeverityLevel.SEVERE],
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
        recommended_for=ALL_SEVERITIES,
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
        recommended_for=ALL_SEVERITIES,
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
        recommended_for=ALL_SEVERITIES,
    ),
]

EXERCISES_BY_ID: dict[str, TherapyExercise] = {ex.id: ex for ex in EXERCISE_BANK}


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


def get_exercise(exercise_id: str) -> TherapyExercise | None:
    return EXERCISES_BY_ID.get(exercise_id)


def recommend_exercises(severity: SeverityLevel) -> list[TherapyExercise]:
    matches = [ex for ex in EXERCISE_BANK if severity in ex.recommended_for]
    return matches if matches else EXERCISE_BANK
