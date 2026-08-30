from app.therapy.schemas import ExerciseType, SeverityLevel, TherapyExercise

EXERCISE_BANK: list[TherapyExercise] = [
    TherapyExercise(
        id="pacing-easy-1",
        type=ExerciseType.PACING,
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
    TherapyExercise(
        id="daf-1",
        type=ExerciseType.DAF,
        title="Delayed Auditory Feedback",
        description=(
            "Speak normally while hearing your own voice played back with a short delay. "
            "This technique is commonly used to help smooth out speech rhythm. "
            "Start with a short delay and increase gradually if it feels comfortable."
        ),
        recommended_for=[SeverityLevel.MILD, SeverityLevel.MODERATE, SeverityLevel.SEVERE],
    ),
    TherapyExercise(
        id="picture-1",
        type=ExerciseType.PICTURE,
        title="Picture Description",
        description=(
            "Look at the picture and describe what's happening in your own words. "
            "There's no rush — take as long as you need."
        ),
        image_url="/stimuli/images/picture-1.jpg",
        recommended_for=[
            SeverityLevel.MILD,
            SeverityLevel.MODERATE,
            SeverityLevel.SEVERE,
            SeverityLevel.UNKNOWN,
        ],
    ),
]


def recommend_exercises(severity: SeverityLevel) -> list[TherapyExercise]:
    matches = [ex for ex in EXERCISE_BANK if severity in ex.recommended_for]
    return matches if matches else EXERCISE_BANK
