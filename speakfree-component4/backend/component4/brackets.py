"""
Clinical age brackets - the single source of truth for age -> bracket (used by C1 and C4).

###########################################################################################
#  ★ COMPONENT 4 NOVELTY - AGE-BRACKETED THERAPY                                          #
#                                                                                         #
#  Therapy content, speed, tone and look are planned by clinical age bracket, because     #
#  reading level, vocabulary, attention span and motivation differ sharply with age:      #
#                                                                                         #
#     Bracket  Ages    Reading                        target_wpm   UI theme    AI tone    #
#       1      6-7     3-4 word phonetic sentences        70       playful     playful    #
#       2      8-9     compound sentences, blends         85       playful     playful    #
#       3      10-11   paragraph, 40-50 words            100       playful     simple     #
#       4      12-13   expository, 60-80 words           110       modern      simple     #
#       5      14-15   clinical-style, 80-100 words      120       modern      friendly   #
#       6      16-17   academic prose, 100-120 words     130       modern      friendly   #
#       7      18-20   professional + tone, 120-150      140       professional friendly  #
#       8      21+     professional / news, 150-180      150       professional respectful#
#                                                                                         #
#  The AGE bracket fixes the tone and theme (a 10-year-old is always spoken to as a       #
#  10-year-old); the PRACTICE bracket (adaptive.py) moves with performance and picks the  #
#  content: start = age bracket (severe screening -> one lower), 2 strong -> up (max age   #
#  bracket + 1), 2 difficult -> down (min 1). A therapist override always wins.           #
###########################################################################################

Keep in sync with speakfree-component1/frontend/src/utils/age.ts.
"""
from __future__ import annotations

MIN_AGE = 6
MAX_AGE = 100
MIN_BRACKET, MAX_BRACKET = 1, 8
SEVERE_LEVEL = 4  # Component 3 severity level for "Severe"
TOO_YOUNG_MESSAGE = "This app is for ages 6 and above"

BRACKETS: dict[int, dict] = {
    1: {"min_age": 6, "max_age": 7, "label": "Ages 6–7", "target_wpm": 70, "theme": "playful", "tone": "playful"},
    2: {"min_age": 8, "max_age": 9, "label": "Ages 8–9", "target_wpm": 85, "theme": "playful", "tone": "playful"},
    3: {"min_age": 10, "max_age": 11, "label": "Ages 10–11", "target_wpm": 100, "theme": "playful", "tone": "simple"},
    4: {"min_age": 12, "max_age": 13, "label": "Ages 12–13", "target_wpm": 110, "theme": "modern", "tone": "simple"},
    5: {"min_age": 14, "max_age": 15, "label": "Ages 14–15", "target_wpm": 120, "theme": "modern", "tone": "friendly"},
    6: {"min_age": 16, "max_age": 17, "label": "Ages 16–17", "target_wpm": 130, "theme": "modern", "tone": "friendly"},
    7: {"min_age": 18, "max_age": 20, "label": "Ages 18–20", "target_wpm": 140, "theme": "professional", "tone": "friendly"},
    8: {"min_age": 21, "max_age": MAX_AGE, "label": "Ages 21+", "target_wpm": 150, "theme": "professional", "tone": "respectful"},
}


def age_bracket_for(age: int) -> int:
    """Clinical age bracket (1-8). Raises ValueError for ages outside 6-100."""
    if age < MIN_AGE:
        raise ValueError(TOO_YOUNG_MESSAGE)
    if age > MAX_AGE:
        raise ValueError(f"Please enter an age between {MIN_AGE} and {MAX_AGE}")
    for bracket_id, info in BRACKETS.items():
        if info["min_age"] <= age <= info["max_age"]:
            return bracket_id
    raise ValueError(f"No bracket for age {age}")  # unreachable: brackets cover 6-100


def bracket_info(bracket_id: int) -> dict:
    return {"id": bracket_id, **BRACKETS[bracket_id]}


def ages_text(bracket_id: int) -> str:
    """Plain-language age range, e.g. 'ages 10–11' or 'ages 21+'."""
    return BRACKETS[bracket_id]["label"].replace("Ages", "ages")


def clamp_bracket(bracket: int) -> int:
    return max(MIN_BRACKET, min(MAX_BRACKET, int(bracket)))


def max_bracket_for(age_bracket: int) -> int:
    """The adaptive ladder may go one bracket above the learner's age, never further."""
    return clamp_bracket(age_bracket + 1)


def start_bracket(age_bracket: int, severity_level: int | None) -> int:
    """Severe screening result -> start one bracket lower; mild / moderate / normal / unknown -> age bracket."""
    if severity_level is not None and int(severity_level) >= SEVERE_LEVEL:
        return max(MIN_BRACKET, age_bracket - 1)
    return age_bracket
