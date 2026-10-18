"""
Adaptive therapy plan - the main Component 4 output.

###########################################################################################
#  ★ COMPONENT 4 NOVELTY - ADAPTIVE THERAPY PLAN                                          #
#                                                                                         #
#  build_plan(profile, attempts, learner) closes the loop C1 -> C2 -> C3 -> C4 -> practice:#
#                                                                                         #
#   1. AGE       learner's age -> clinical bracket 1-8 -> tone, theme   (brackets.py)     #
#   2. FOCUS     C3 disorder -> therapy focus + exercise family   (categories.py)         #
#   3. DOSE      C3 severity -> sessions/week, minutes, exercises/session                 #
#   4. LEVEL     age bracket (+ C3 severity) -> starting practice bracket; attempts move  #
#                it up / down, a therapist override pins it         (adaptive.py)        #
#   5. CONTENT   the bracket's reading + picture + conversation tasks (bracket_tasks.py)  #
#                + C1 flagged sounds -> generated sound drills       (exercises.py)       #
#   6. RANKING   LinUCB + C3 category prior orders the bracket tasks and adds extra       #
#                practice suited to the bracket (pacing, DAF, breathing ...) (bandit.py)  #
#   7. GOALS     measurable targets from C1/C2/C3 numbers and the patient's own attempts  #
#   8. RE-SCREEN after 14 days, 12 attempts or a mastered ladder -> a new screening runs  #
#                C1->C2->C3 again and re-anchors the plan (new profile, new prior)         #
#                                                                                         #
#  Today = therapist-assigned exercises (always first) + the 3 bracket tasks (bandit       #
#  order) + extra practice, up to the severity dose. Every recomputation is deterministic #
#  from (profile, attempts, learner), so the plan the patient sees and the explanation    #
#  the admin sees always agree.                                                            #
###########################################################################################
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .adaptive import learner_bracket, level_state, personal_target_wpm
from .bandit import bracket_position, rank_arms
from .brackets import BRACKETS
from .categories import DOSE_BY_SEVERITY, FOCI
from .exercises import LEVELS, exercises_for, get_exercise, suits_bracket
from .progress import parse, summary
from .scoring import THRESHOLDS

RESCREEN_DAYS = 14
RESCREEN_ATTEMPTS = 12
CORE_TASKS = 3  # reading + picture + conversation of the current bracket
SKILL_LADDERS = ("clear_speech", "sound_drill")  # Beginner -> Advanced inside these families
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ACTIVE_DAY_PATTERNS = {
    3: [0, 2, 4], 4: [0, 1, 3, 5], 5: [0, 1, 2, 3, 5], 6: [0, 1, 2, 3, 4, 5], 7: list(range(7)),
}
CORE_REASON = {
    "reading": "Read the passage for your level at a steady pace.",
    "picture": "Describe the picture in your own words - free speech practice.",
    "conversation": "Answer the questions out loud - real-life speaking practice.",
}


def _profile_attempts(profile: dict, records: list[dict]) -> list[dict]:
    since = profile.get("created_at")
    if not since:
        return records
    t0 = parse(since)
    return [r for r in records if parse(r["completed_at"]) >= t0]


def skill_ladder(profile: dict) -> str | None:
    ladder = FOCI[profile["focus"]]["ladder_type"]
    return ladder if ladder in SKILL_LADDERS else None


def skill_state(profile: dict, records: list[dict]) -> dict | None:
    ladder = skill_ladder(profile)
    if ladder is None:
        return None
    return level_state(records, ladder, profile.get("start_level", "beginner"), profile.get("created_at"))


def _bracket_positions(records: list[dict], profile: dict, learner: dict | None) -> list[float]:
    """Practice bracket at the moment of each attempt (context for the bandit's replay)."""
    return [bracket_position(learner_bracket(profile, records[:i], learner)["bracket"]) for i in range(len(records))]


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


def _rescreen(profile: dict, attempts: list[dict], mastered: bool, now: datetime) -> dict:
    created = parse(profile["created_at"]) if profile.get("created_at") else now
    days = (now - created).days
    reasons = []
    if days >= RESCREEN_DAYS:
        reasons.append(f"{days} days since your last screening")
    if len(attempts) >= RESCREEN_ATTEMPTS:
        reasons.append(f"{len(attempts)} exercises completed")
    if mastered:
        reasons.append("top level completed")
    return {
        "recommended": bool(reasons),
        "reasons": reasons,
        "days_since_screening": days,
        "attempts_since_screening": len(attempts),
        "due_in_days": max(0, RESCREEN_DAYS - days),
        "attempts_until_due": max(0, RESCREEN_ATTEMPTS - len(attempts)),
    }


def _weekly_schedule(fixed: list[dict], pool: list[dict], extras_per_day: int, dose: dict,
                     attempts: list[dict], now: datetime) -> list[dict]:
    """Every active day: assigned + bracket tasks (fixed), plus extra practice rotating through the bandit's pool."""
    active = ACTIVE_DAY_PATTERNS.get(dose["sessions_per_week"], ACTIVE_DAY_PATTERNS[4])
    week_start = (now - timedelta(days=now.weekday())).date()
    days = []
    for d in range(7):
        day = week_start + timedelta(days=d)
        done = [r for r in attempts if parse(r["completed_at"]).date() == day]
        items = []
        if d in active:
            items = [{"id": e["id"], "title": e["title"], "type": e["type"]} for e in fixed]
            for k in range(min(extras_per_day, len(pool))):
                p = pool[(d + k) % len(pool)]
                items.append({"id": p["id"], "title": p["title"], "type": p["type"]})
        days.append({
            "date": day.isoformat(), "day": DAY_NAMES[d], "is_today": day == now.date(), "active": d in active,
            "minutes": dose["minutes_per_session"] if d in active else 0, "exercises": items,
            "completed": len(done),
        })
    return days


def build_plan(profile: dict, records: list[dict], now: datetime | None = None, learner: dict | None = None) -> dict:
    """
    The complete adaptive plan for one patient (patient view + admin explanation).

    learner = {"age": 10, "age_bracket": 3, "bracket_override": None, "assigned": ["daf"]} comes from the
    platform's patient record; without it the learner is treated as an adult with no age cap.
    """
    now = now or datetime.now(timezone.utc)
    learner = learner or {}
    focus = FOCI[profile["focus"]]
    flagged = profile.get("flagged_sounds")
    exercises = exercises_for(flagged)
    attempts = _profile_attempts(profile, records)
    level = learner_bracket(profile, records, learner)
    bracket = level["bracket"]
    age_bracket = level["age_bracket"]
    skill = skill_state(profile, records)
    ladder = skill_ladder(profile)
    dose = DOSE_BY_SEVERITY.get(int(profile.get("severity_level") or 1), DOSE_BY_SEVERITY[2])

    # arms: the current bracket's 3 tasks + extra practice suited to the bracket (skill ladder: current rung only)
    core = [e for e in exercises if e.get("bracket") == bracket]
    extras = [e for e in exercises if suits_bracket(e, bracket)
              and (e["type"] != ladder or e.get("level") in (None, (skill or {}).get("level")))]
    ranked, context = rank_arms(core + extras, records, profile, bracket, _bracket_positions(records, profile, learner))
    by_id = {e["id"]: e for e in core + extras}

    # 1. therapist-assigned exercises always come first
    assigned = []
    for ex_id in learner.get("assigned") or []:
        ex = get_exercise(ex_id, flagged)
        if ex and ex["id"] not in {a["id"] for a in assigned}:
            assigned.append(dict(_decorate(ex, records), source="therapist", reason="Assigned by your therapist."))
    used_ids = {a["id"] for a in assigned}

    # 2. the bracket's reading / picture / conversation tasks, in bandit order
    today = list(assigned)
    for row in [r for r in ranked if r["bracket"] == bracket]:
        if row["id"] in used_ids:
            continue
        ex = by_id[row["id"]]
        reason = f"{level['label']} ({level['ages']}): {CORE_REASON[ex['task_type']]}"
        today.append(dict(_decorate(ex, records), source="bracket", reason=reason, rank=row["rank"]))
        used_ids.add(row["id"])

    # 3. extra practice up to the dose: the skill-ladder exercise first, then the bandit's picks
    #    pass 1: primary-focus exercises of a new type, pass 2: any primary-focus exercise,
    #    pass 3: exercises the C3 probabilities still favour (bandit order throughout). An exercise
    #    that serves none of these is never added just to fill the dose.
    n_extra = max(1, dose["exercises_per_session"] - CORE_TASKS - len(assigned))
    picks: list[dict] = []
    if skill:
        ladder_ex = _ladder_exercise(exercises, ladder, skill["level"], records)
        if ladder_ex["id"] not in used_ids:
            picks.append(dict(_decorate(ladder_ex, records), source="level",
                              reason=f"Your skill step for “{focus['patient_name']}”: {skill['label']}. {skill['progress_text']}"))
            used_ids.add(ladder_ex["id"])
    used_types = {e["type"] for e in today + picks}
    primary = profile["focus"]
    passes = [lambda r: primary in r["focus"] and r["type"] not in used_types,
              lambda r: primary in r["focus"],
              lambda r: r["category_fit"] >= 0.25]
    for accept in passes:
        for row in ranked:
            if len(picks) >= n_extra:
                break
            if row["id"] in used_ids or row["bracket"] is not None or not accept(row):
                continue
            if row["predicted_score"] is None:
                reason = "New for you - trying it helps the plan learn what suits you."
            else:
                reason = (f"From {row['times_practised']} attempt{'s' if row['times_practised'] != 1 else ''} the plan "
                          f"expects about {row['predicted_score']} points here.")
            picks.append(dict(_decorate(by_id[row["id"]], records), source="bandit", reason=reason, rank=row["rank"]))
            used_ids.add(row["id"])
            used_types.add(row["type"])
    today += picks

    pool = [r for r in ranked if r["bracket"] is None and r["id"] not in {a["id"] for a in assigned}]
    pool = pool[:max(4, n_extra * 2)]
    fixed = [e for e in today if e["source"] in ("therapist", "bracket")]

    library = [dict(_decorate(e, records),
                    locked=bool(e["type"] == ladder and e.get("level") and skill and
                                LEVELS.index(e["level"]) > skill["level_index"]))
               for e in core + [e for e in exercises if suits_bracket(e, bracket)]]

    return {
        "learner": {
            "age": learner.get("age"),
            "age_bracket": age_bracket,
            "age_label": BRACKETS[age_bracket]["label"],
            "theme": BRACKETS[age_bracket]["theme"],
            "tone": BRACKETS[age_bracket]["tone"],
            "practice_bracket": bracket,
            "override": level["override"],
        },
        "focus": {k: focus[k] for k in ("key", "patient_name", "tagline", "techniques", "ladder_type")},
        "dose": dose,
        "level": level,
        "skill_level": skill,
        "today": today,
        "week": _weekly_schedule(fixed, pool, n_extra, dose, attempts, now),
        "goals": _goals(profile, attempts, level, dose, now),
        "rescreen": _rescreen(profile, attempts, level["mastered"] or bool(skill and skill["mastered"]), now),
        "progress": summary(records, now),
        "library": library,
        # ---- admin-only explanation of the adaptive engine ----
        "engine": {
            "context": {
                "vector": [round(float(v), 4) for v in context],
                "labels": ["bias", "bracket", "avg_score", "trend", "comfort", "severity", "c3_confidence"],
            },
            "arms": ranked,
            "focus_probabilities": profile.get("focus_probabilities"),
            "attempts_since_screening": len(attempts),
        },
    }
