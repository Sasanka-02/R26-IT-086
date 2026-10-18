"""
Therapy categories - how a Component 3 result becomes a therapy focus.

###########################################################################################
#  ★ COMPONENT 4 NOVELTY - CATEGORY-SPECIFIC ADAPTIVE THERAPY                              #
#                                                                                         #
#  Component 3's disorder class selects one of four therapy foci. Each focus has its own   #
#  exercise family (with a Beginner -> Intermediate -> Advanced ladder), its own technique #
#  vocabulary for the AI assistant, its own weekly dose and its own measurable goals.      #
#                                                                                         #
#     C3 disorder    ->  focus            ladder family     patient-facing name            #
#     stuttering     ->  fluency          reading           "Smooth, confident speech"     #
#     dysarthria     ->  motor_speech     clear_speech      "A clear, strong voice"        #
#     articulation   ->  speech_sounds    sound_drill       "Crisp speech sounds"          #
#     normal         ->  maintenance      reading           "Keep your speech sharp"       #
#                                                                                         #
#  Patients only ever see the friendly name - never the disorder label or severity level   #
#  (those stay in the admin dashboards).                                                   #
###########################################################################################
"""
from __future__ import annotations

DISORDER_TO_FOCUS = {
    "stuttering": "fluency",
    "dysarthria": "motor_speech",
    "articulation": "speech_sounds",
    "normal": "maintenance",
}

FOCI: dict[str, dict] = {
    "fluency": {
        "key": "fluency",
        "c3_disorder": "stuttering",
        "admin_name": "Fluency therapy (stuttering)",
        "patient_name": "Smooth, confident speech",
        "tagline": "Gentle starts, steady pacing and relaxed breathing so words flow more easily.",
        "ladder_type": "reading",
        "techniques": [
            "Easy onset: start each phrase with a soft, breathy voice",
            "Pacing: follow a steady, slightly slower rhythm",
            "Light contacts: touch lips and tongue gently on hard sounds",
            "Pause on purpose between ideas and take a calm breath",
        ],
        "tips": {
            "core": "Start each sentence with a slow breath out and a soft, easy first sound. "
                    "If you feel a block coming, pause, breathe, and slide gently into the word.",
            "speed": "Follow the highlighted word rather than racing ahead. A slower, even pace "
                     "usually means fewer blocks.",
            "pause": "Pausing on purpose between ideas is a strength, not a mistake. Stop, breathe "
                     "through your nose, and restart with a gentle onset.",
        },
    },
    "motor_speech": {
        "key": "motor_speech",
        "c3_disorder": "dysarthria",
        "admin_name": "Motor-speech therapy (dysarthria)",
        "patient_name": "A clear, strong voice",
        "tagline": "Breath support, a louder voice and clear, deliberate words so people understand you easily.",
        "ladder_type": "clear_speech",
        "techniques": [
            "Think loud: use a strong, healthy voice from your belly",
            "Over-articulate: move lips, tongue and jaw a little more than usual",
            "Breath support: take a full breath before each phrase",
            "Slow down and give every syllable its own beat",
        ],
        "tips": {
            "core": "Take a full breath before each phrase and 'think loud' - imagine speaking to "
                    "someone across the room. Move your mouth a little more than feels normal.",
            "volume": "Sit tall, breathe from your belly and aim your voice at the far wall. "
                      "Loud, not shouting - a strong, healthy voice.",
            "speed": "Give every syllable its own beat. Slower speech gives your muscles time to "
                     "reach each sound clearly.",
        },
    },
    "speech_sounds": {
        "key": "speech_sounds",
        "c3_disorder": "articulation",
        "admin_name": "Articulation therapy (speech sounds)",
        "patient_name": "Crisp speech sounds",
        "tagline": "Short, focused practice on the exact sounds that were tricky in your screening.",
        "ladder_type": "sound_drill",
        "techniques": [
            "Find the sound: notice where your tongue and lips go",
            "Practise the sound in words, then phrases, then sentences",
            "Say it slowly first, then at normal speed",
            "Listen back and compare with a clear model",
        ],
        "tips": {
            "core": "Say the target sound on its own first, then at the start of words, then in "
                    "short phrases. Slow and accurate beats fast and fuzzy.",
            "sound": "Look in a mirror while you practise - watching your lips and tongue helps you "
                     "find the right position for the sound.",
        },
    },
    "maintenance": {
        "key": "maintenance",
        "c3_disorder": "normal",
        "admin_name": "Maintenance (typical range)",
        "patient_name": "Keep your speech sharp",
        "tagline": "Your screening was in the typical range - light practice keeps speech confident and clear.",
        "ladder_type": "reading",
        "techniques": [
            "Read aloud with expression",
            "Describe pictures and events in full sentences",
            "Keep a natural, relaxed pace",
        ],
        "tips": {
            "core": "A few minutes of reading aloud or describing your day keeps your speech "
                    "confident. Try to use full sentences and natural pauses.",
        },
    },
}

# Weekly dose by Component 3 severity level (more severe -> more frequent sessions).
# exercises_per_session = the 3 age-bracket tasks (reading, picture, conversation) + extra practice.
DOSE_BY_SEVERITY = {
    4: {"sessions_per_week": 6, "minutes_per_session": 12, "exercises_per_session": 4},
    3: {"sessions_per_week": 5, "minutes_per_session": 15, "exercises_per_session": 5},
    2: {"sessions_per_week": 4, "minutes_per_session": 18, "exercises_per_session": 5},
    1: {"sessions_per_week": 3, "minutes_per_session": 12, "exercises_per_session": 4},
}

# Starting rung of the skill ladder by severity (levels: beginner, intermediate, advanced).
# The age-bracket ladder has its own start rule (brackets.start_bracket).
START_LEVEL_BY_SEVERITY = {4: "beginner", 3: "beginner", 2: "intermediate", 1: "advanced"}


def focus_for(disorder: str | None) -> str:
    return DISORDER_TO_FOCUS.get(disorder or "normal", "maintenance")


def focus_probabilities(disorder_breakdown: dict | None, fallback_focus: str) -> dict[str, float]:
    """C3 disorder probabilities re-keyed by therapy focus (used by the bandit's category prior)."""
    if not disorder_breakdown:
        return {k: (1.0 if k == fallback_focus else 0.0) for k in FOCI}
    probs = {DISORDER_TO_FOCUS[d]: float(p) for d, p in disorder_breakdown.items() if d in DISORDER_TO_FOCUS}
    total = sum(probs.values()) or 1.0
    return {k: round(probs.get(k, 0.0) / total, 4) for k in FOCI}
