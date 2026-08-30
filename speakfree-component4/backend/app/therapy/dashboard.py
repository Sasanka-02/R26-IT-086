"""
SO3 - Personalized Dashboard.

Generates the trend data the dashboard visualises. Real session history
doesn't exist yet for a brand-new demo account, so this produces a
plausible synthetic 4-week trend on first load — clearly a placeholder
for real accumulated session data, not a claim of real patient history.
"""

import random


def generate_weekly_trend(weeks: int = 4) -> list[dict]:
    base_stutter_freq = random.uniform(4.0, 7.0)
    base_articulation = random.uniform(65, 75)
    base_rate = random.uniform(95, 115)

    trend = []
    for week in range(1, weeks + 1):
        base_stutter_freq = max(0.5, base_stutter_freq - random.uniform(0.1, 0.6))
        base_articulation = min(98, base_articulation + random.uniform(0.5, 2.5))
        base_rate = base_rate + random.uniform(-3, 5)

        trend.append(
            {
                "week": week,
                "stuttering_events_per_min": round(base_stutter_freq, 2),
                "articulation_accuracy": round(base_articulation, 1),
                "speech_rate_wpm": round(base_rate, 1),
                "sessions_completed": random.randint(2, 5),
            }
        )
    return trend


def summarize_streak(trend: list[dict]) -> dict:
    total_sessions = sum(w["sessions_completed"] for w in trend)
    return {
        "total_practice_sessions": total_sessions,
        "current_streak_weeks": len(trend),
        "total_practice_hours": round(total_sessions * 0.25, 1),
    }
