"""
Adaptive therapy plan - the main Component 4 output.

###########################################################################################
#  ★ COMPONENT 4 NOVELTY - ADAPTIVE THERAPY PLAN                                          #
#                                                                                         #
#  build_plan(profile, attempts) closes the loop C1 -> C2 -> C3 -> C4 -> practice -> C4:  #
#                                                                                         #
#   1. FOCUS     C3 disorder -> therapy focus + exercise family   (categories.py)         #
#   2. DOSE      C3 severity -> sessions/week, minutes, exercises/session                 #
#   3. LEVEL     C3 severity -> starting rung; attempts move it up / down  (adaptive.py)  #
#   4. CONTENT   C1 flagged sounds -> generated sound drills         (exercises.py)       #
#   5. RANKING   LinUCB + C3 category prior picks today's exercises  (bandit.py)          #
#   6. GOALS     measurable targets from C1/C2/C3 numbers and the patient's own attempts  #
#   7. RE-SCREEN after 14 days, 12 attempts or a mastered ladder -> a new screening runs  #
#                C1->C2->C3 again and re-anchors the plan (new profile, new prior)         #
#                                                                                         #
#  Every recomputation is deterministic from (profile, attempts), so the plan the patient  #
#  sees and the explanation the admin sees always agree.                                  #
###########################################################################################
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .adaptive import level_state, personal_target_wpm
from .bandit import rank_arms
from .categories import DOSE_BY_SEVERITY, FOCI
from .exercises import exercises_for
from .progress import parse, summary
from .scoring import THRESHOLDS

RESCREEN_DAYS = 14
RESCREEN_ATTEMPTS = 12
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ACTIVE_DAY_PATTERNS = {
    3: [0, 2, 4], 4: [0, 1, 3, 5], 5: [0, 1, 2, 3, 5], 6: [0, 1, 2, 3, 4, 5], 7: list(range(7)),
}


def _profile_attempts(profile: dict, records: list[dict]) -> list[dict]:
    since = profile.get("created_at")
    if not since:
        return records
    t0 = parse(since)
    return [r for r in records if parse(r["completed_at"]) >= t0]


def _ladder_levels(records: list[dict], ladder: str, profile: dict) -> list[int]:
    """Ladder rung at the moment of each attempt (context for the bandit's replay)."""
    return [level_state(records[:i], ladder, profile.get("start_level", "beginner"),
                        profile.get("created_at"))["level_index"] for i in range(len(records))]


def _ladder_exercise(exercises: list[dict], ladder: str, level: str, records: list[dict]) -> dict:
    options = [e for e in exercises if e["type"] == ladder and e.get("level") == level]
    if ladder == "sound_drill":
        counts = {e["id"]: sum(1 for r in records if r["exercise_id"] == e["id"]) for e in options}
        options.sort(key=lambda e: (counts[e["id"]], e.get("sound_rank", 0)))
    return options[0]


def _decorate(ex: dict, records: list[dict]) -> dict:
    out = {k: v for k, v in ex.items()}
    if ex.get("target_wpm"):
        out["base_wpm"] = ex["target_wpm"]
        out["target_wpm"] = personal_target_wpm(ex["target_wpm"], ex["id"], records)
    attempts = [r for r in records if r["exercise_id"] == ex["id"]]
    out["times_practised"] = len(attempts)
    out["last_score"] = attempts[-1]["score"] if attempts else None
    return out


def _goals(profile: dict, attempts: list[dict], level: dict, dose: dict, now: datetime) -> list[dict]:
    focus = profile["focus"]
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    this_week = [r for r in attempts if parse(r["completed_at"]) >= week_start]
    days_practised = len({parse(r["completed_at"]).date() for r in this_week})
    goals = [{
        "id": "weekly_sessions", "text": f"Practise on {dose['sessions_per_week']} days this week",
        "current": days_practised, "target": dose["sessions_per_week"], "unit": "days",
        "met": days_practised >= dose["sessions_per_week"],
    }, {
        "id": "ladder", "text": f"Unlock the next level ({level['progress_text']})",
        "current": level["strong_in_a_row"], "target": level["needed_to_advance"], "unit": "strong in a row",
        "met": level["mastered"],
    }]
    live = [r for r in attempts if r.get("speaking_ratio") is not None][-5:]
    c1 = profile.get("baseline") or {}
    if focus == "fluency":
        pauses = round(sum(r.get("long_pauses", 0) for r in live) / len(live), 1) if live else None
        goals.append({"id": "pauses", "text": "Keep long pauses to 1 or fewer per exercise (last 5)",
                      "current": pauses, "target": 1, "unit": "pauses", "met": pauses is not None and pauses <= 1})
    elif focus == "motor_speech":
        best = max((r.get("max_phonation_sec") or 0 for r in attempts if r["exercise_type"] == "sustained_vowel"), default=None)
        goals.append({"id": "phonation", "text": "Hold a steady 'ahh' for 10 seconds",
                      "current": best, "target": 10, "unit": "s", "met": bool(best and best >= 10)})
        quiet = round(sum(r.get("quiet_warnings", 0) for r in live) / len(live), 1) if live else None
        goals.append({"id": "volume", "text": "No more than 1 'too quiet' warning per exercise (last 5)",
                      "current": quiet, "target": 1, "unit": "warnings", "met": quiet is not None and quiet <= 1})
    elif focus == "speech_sounds":
        drills = [r for r in attempts if r["exercise_type"] == "sound_drill" and r.get("items_total")][-3:]
        acc = round(100 * sum(r["items_clear"] or 0 for r in drills) / sum(r["items_total"] for r in drills)) if drills else None
        goals.append({"id": "sound_accuracy", "text": "Say 80% of drill items clearly (last 3 drills)",
                      "current": acc, "target": 80, "unit": "%", "met": acc is not None and acc >= 80})
    recent = [r["score"] for r in attempts[-5:]]
    avg = round(sum(recent) / len(recent)) if recent else None
    goals.append({"id": "quality", "text": f"Average score of {THRESHOLDS['strong']}+ over your last 5 exercises",
                  "current": avg, "target": THRESHOLDS["strong"], "unit": "points",
                  "met": avg is not None and avg >= THRESHOLDS["strong"]})
    if c1.get("target_metric"):
        goals.append({"id": "screening", "text": c1["target_metric"]["text"], "current": c1["target_metric"]["current"],
                      "target": c1["target_metric"]["target"], "unit": "at next screening", "met": False,
                      "screening_goal": True})
    return goals


def _rescreen(profile: dict, attempts: list[dict], level: dict, now: datetime) -> dict:
    created = parse(profile["created_at"]) if profile.get("created_at") else now
    days = (now - created).days
    reasons = []
    if days >= RESCREEN_DAYS:
        reasons.append(f"{days} days since your last screening")
    if len(attempts) >= RESCREEN_ATTEMPTS:
        reasons.append(f"{len(attempts)} exercises completed")
    if level["mastered"]:
        reasons.append("top level completed")
    return {
        "recommended": bool(reasons),
        "reasons": reasons,
        "days_since_screening": days,
        "attempts_since_screening": len(attempts),
        "due_in_days": max(0, RESCREEN_DAYS - days),
        "attempts_until_due": max(0, RESCREEN_ATTEMPTS - len(attempts)),
    }


def _weekly_schedule(today_plan: list[dict], ranked: list[dict], dose: dict, attempts: list[dict], now: datetime) -> list[dict]:
    active = ACTIVE_DAY_PATTERNS.get(dose["sessions_per_week"], ACTIVE_DAY_PATTERNS[4])
    week_start = (now - timedelta(days=now.weekday())).date()
    ladder = today_plan[0]
    pool = [r for r in ranked if r["id"] != ladder["id"]][:max(4, dose["exercises_per_session"] * 2)]
    days = []
    for d in range(7):
        day = week_start + timedelta(days=d)
        done = [r for r in attempts if parse(r["completed_at"]).date() == day]
        items = []
        if d in active:
            items = [{"id": ladder["id"], "title": ladder["title"], "type": ladder["type"]}]
            for k in range(dose["exercises_per_session"] - 1):
                if pool:
                    p = pool[(d + k) % len(pool)]
                    items.append({"id": p["id"], "title": p["title"], "type": p["type"]})
        days.append({
            "date": day.isoformat(), "day": DAY_NAMES[d], "is_today": day == now.date(), "active": d in active,
            "minutes": dose["minutes_per_session"] if d in active else 0, "exercises": items,
            "completed": len(done),
        })
    return days


def build_plan(profile: dict, records: list[dict], now: datetime | None = None) -> dict:
    """The complete adaptive plan for one patient (patient view + admin explanation)."""
    now = now or datetime.now(timezone.utc)
    focus = FOCI[profile["focus"]]
    ladder = focus["ladder_type"]
    exercises = exercises_for(profile.get("flagged_sounds"))
    attempts = _profile_attempts(profile, records)
    level = level_state(records, ladder, profile.get("start_level", "beginner"), profile.get("created_at"))
    dose = DOSE_BY_SEVERITY.get(int(profile.get("severity_level") or 1), DOSE_BY_SEVERITY[2])

    # arms: everything except ladder exercises on other rungs
    arms = [e for e in exercises if e.get("level") in (None, level["level"])]
    ranked, context = rank_arms(arms, records, profile, level, _ladder_levels(records, ladder, profile))

    ladder_ex = _ladder_exercise(exercises, ladder, level["level"], records)
    today = [dict(_decorate(ladder_ex, records), source="level",
                  reason=f"Your main exercise for “{focus['patient_name']}” at {level['label']} level. {level['progress_text']}")]
    used_types = {ladder_ex["type"]}
    used_ids = {ladder_ex["id"]}
    by_id = {e["id"]: e for e in arms}
    # pass 1: primary-focus exercises of a new type, pass 2: any primary-focus exercise,
    # pass 3: exercises the C3 probabilities still favour, pass 4: anything (bandit order throughout)
    primary = profile["focus"]
    passes = [lambda r: primary in r["focus"] and r["type"] not in used_types,
              lambda r: primary in r["focus"],
              lambda r: r["category_fit"] >= 0.25,
              lambda r: True]
    picks = []
    for accept in passes:
        for row in ranked:
            if len(today) + len(picks) >= dose["exercises_per_session"]:
                break
            if row["id"] in used_ids or not accept(row):
                continue
            picks.append(row)
            used_ids.add(row["id"])
            used_types.add(row["type"])
    for row in picks:
        ex = by_id[row["id"]]
        if row["predicted_score"] is None:
            reason = "New for you - trying it helps the plan learn what suits you."
        else:
            reason = (f"From {row['times_practised']} attempt{'s' if row['times_practised'] != 1 else ''} the plan "
                      f"expects about {row['predicted_score']} points here.")
        today.append(dict(_decorate(ex, records), source="bandit", reason=reason, rank=row["rank"]))
        used_types.add(row["type"])

    library = [dict(_decorate(e, records),
                    locked=bool(e["type"] == ladder and e.get("level") and
                                ["beginner", "intermediate", "advanced"].index(e["level"]) > level["level_index"]))
               for e in exercises]

    return {
        "focus": {k: focus[k] for k in ("key", "patient_name", "tagline", "techniques", "ladder_type")},
        "dose": dose,
        "level": level,
        "today": today,
        "week": _weekly_schedule(today, ranked, dose, attempts, now),
        "goals": _goals(profile, attempts, level, dose, now),
        "rescreen": _rescreen(profile, attempts, level, now),
        "progress": summary(records, now),
        "library": library,
        # ---- admin-only explanation of the adaptive engine ----
        "engine": {
            "context": {
                "vector": [round(float(v), 4) for v in context],
                "labels": ["bias", "level", "avg_score", "trend", "comfort", "severity", "c3_confidence"],
            },
            "arms": ranked,
            "focus_probabilities": profile.get("focus_probabilities"),
            "attempts_since_screening": len(attempts),
        },
    }
