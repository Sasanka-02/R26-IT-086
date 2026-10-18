"""
Age calculation + age-bracket categorisation (supported range: 6–100 years).

The bracket rules have ONE source of truth, shared with Component 4's therapy planner:
speakfree-component4/backend/component4/brackets.py (`age_bracket_for`). Lower bound inclusive,
upper bound inclusive:

    Bracket 1: 6–7   Bracket 2: 8–9   Bracket 3: 10–11  Bracket 4: 12–13
    Bracket 5: 14–15 Bracket 6: 16–17 Bracket 7: 18–20  Bracket 8: 21+

The screening task library and speech-rate norms cover brackets 1–7; adults (bracket 8) are
screened with the bracket-7 tasks (`screening_bracket`) and practise with the bracket-8 therapy
content. Keep frontend/src/utils/age.ts in sync.
"""
from datetime import date

import integration  # noqa: F401  (puts the component packages on sys.path)
from component4.brackets import (  # noqa: F401  (re-exported for the platform)
    BRACKETS,
    MAX_AGE,
    MIN_AGE,
    TOO_YOUNG_MESSAGE,
    age_bracket_for,
    bracket_info,
)

ADULT_AGE = 18                 # under 18: a parent or guardian must agree to the account
SCREENING_MAX_BRACKET = 7      # highest bracket in the screening task library


def age_from_dob(dob: date, today: date | None = None) -> int:
    today = today or date.today()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


def bracket_for_age(age: int | None) -> int | None:
    """Like age_bracket_for, but None instead of an error for unknown / unsupported ages."""
    if age is None:
        return None
    try:
        return age_bracket_for(age)
    except ValueError:
        return None


def screening_bracket(bracket: int) -> int:
    """Screening tasks + norms exist for brackets 1–7; adults use the bracket-7 set."""
    return min(bracket, SCREENING_MAX_BRACKET)


def patient_age(patient) -> int | None:
    """Current age: from the date of birth when known, otherwise the age the person entered."""
    if patient.date_of_birth is not None:
        return age_from_dob(patient.date_of_birth)
    return patient.age
