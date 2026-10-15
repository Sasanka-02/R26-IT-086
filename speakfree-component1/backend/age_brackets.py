"""
Age calculation + age-bracket categorisation (supported range: 6–20 years).

The proposal lists brackets as 6–8, 8–10, ... 18–20. To avoid overlap, the lower
bound is inclusive and the upper bound exclusive (except the last bracket):

    Bracket 1: 6–7   Bracket 2: 8–9   Bracket 3: 10–11  Bracket 4: 12–13
    Bracket 5: 14–15 Bracket 6: 16–17 Bracket 7: 18–20
"""
from datetime import date

MIN_AGE = 6
MAX_AGE = 20

BRACKETS: dict[int, dict] = {
    1: {"label": "Ages 6–8", "min_age": 6, "max_age": 7},
    2: {"label": "Ages 8–10", "min_age": 8, "max_age": 9},
    3: {"label": "Ages 10–12", "min_age": 10, "max_age": 11},
    4: {"label": "Ages 12–14", "min_age": 12, "max_age": 13},
    5: {"label": "Ages 14–16", "min_age": 14, "max_age": 15},
    6: {"label": "Ages 16–18", "min_age": 16, "max_age": 17},
    7: {"label": "Ages 18–20", "min_age": 18, "max_age": 20},
}


def age_from_dob(dob: date, today: date | None = None) -> int:
    today = today or date.today()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


def bracket_for_age(age: int) -> int | None:
    for bracket_id, info in BRACKETS.items():
        if info["min_age"] <= age <= info["max_age"]:
            return bracket_id
    return None


def bracket_info(bracket_id: int) -> dict:
    return {"id": bracket_id, **BRACKETS[bracket_id]}
