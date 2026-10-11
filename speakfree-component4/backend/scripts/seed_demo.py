"""
Seed realistic demo data for presentations.

    python -m scripts.seed_demo          # add demo therapist + students
    python -m scripts.seed_demo --clean  # remove every *@demo.local account

Run from the backend folder with the virtual environment active. Only
accounts ending in @demo.local are created or removed; real accounts are
never touched.

Demo logins (password for all: demo1234)
    therapist: dr.silva@demo.local
    students:  amal@demo.local, nimali@demo.local, kasun@demo.local,
               tharushi@demo.local, ravi@demo.local
"""

import json
import sys
import uuid
from datetime import datetime, timedelta, timezone

import numpy as np

from app.therapy import progress_store, scoring, therapist_store, user_store
from app.therapy.adaptive import level_state
from app.therapy.auth import hash_password
from app.therapy.exercises import EXERCISE_BANK, get_exercise

SUFFIX = "@demo.local"
PASSWORD = "demo1234"

STUDENTS = [
    # name, registered days ago, sessions, skill 0-1, improvement per session, last active days ago
    ("Amal Perera", 45, 22, 0.45, 0.012, 0),
    ("Nimali Fernando", 38, 14, 0.62, -0.008, 1),
    ("Kasun Jayasuriya", 30, 7, 0.5, 0.004, 10),
    ("Tharushi Wijesinghe", 3, 0, 0.5, 0.0, None),
    ("Ravi Kumar", 25, 16, 0.7, 0.01, 0),
]


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def clean() -> None:
    for path in (progress_store.DATA_FILE, user_store.USERS_FILE, therapist_store.STORE_FILE):
        data = _load(path)
        _write(path, {k: v for k, v in data.items() if not k.endswith(SUFFIX)})
    scoring.calibrate()
    print("Removed demo accounts.")


def _attempt(rng, ex, skill, when) -> dict:
    live = ex.passage is not None
    pauses = int(max(0, rng.poisson(max(0.2, 3.2 * (1 - skill)))))
    ratio = float(np.clip(rng.normal(0.35 + 0.5 * skill, 0.06), 0.15, 0.95)) if live else None
    duration = float(rng.uniform(35, 110))
    target = ex.target_wpm
    wpm = int(target * rng.uniform(0.8, 1.35)) if live and target else None
    rating = "hard" if skill < 0.4 and rng.random() < 0.5 else ("easy" if skill > 0.75 and rng.random() < 0.5 else "ok")
    attempt = {
        "exercise_id": ex.id,
        "exercise_type": ex.type.value,
        "title": ex.title,
        "level": ex.level.value if ex.level else None,
        "difficulty": ex.difficulty,
        "duration_seconds": round(duration, 1),
        "speaking_ratio": round(ratio, 3) if ratio is not None else None,
        "long_pauses": pauses if live else 0,
        "quiet_warnings": int(rng.poisson(0.5)) if live else 0,
        "syllables": None,
        "measured_wpm": wpm,
        "target_wpm": target,
        "self_rating": rating,
    }
    score, breakdown = scoring.score_with_breakdown(attempt)
    return {
        "id": uuid.uuid4().hex,
        "completed_at": when.isoformat(),
        **attempt,
        "score": score,
        "score_breakdown": breakdown,
    }


def _expert_rating(rng, record) -> int:
    """A simulated therapist: weighs long pauses and speed more heavily than the
    starting weights do, so calibration has something real to learn."""
    minutes = max(record["duration_seconds"] / 60, 0.25)
    if record["speaking_ratio"] is None:
        score = 70 + 10 * {"easy": 1, "ok": 0, "hard": -1}[record["self_rating"]]
    else:
        rate_dev = abs(record["measured_wpm"] - record["target_wpm"]) / record["target_wpm"] if record["measured_wpm"] else 0
        score = 30 + 75 * record["speaking_ratio"] - 18 * record["long_pauses"] / minutes - 45 * rate_dev
    score += rng.normal(0, 6)
    return int(np.clip(round(score / 25 + 1), 1, 5))


def seed() -> None:
    clean()
    rng = np.random.default_rng(42)
    now = datetime.now(timezone.utc)
    users = _load(user_store.USERS_FILE)
    progress = _load(progress_store.DATA_FILE)
    settings = _load(therapist_store.STORE_FILE)
    pw = hash_password(PASSWORD)

    therapist = "dr.silva" + SUFFIX
    users[therapist] = {
        "email": therapist, "name": "Dr. Silva", "role": "therapist",
        "registered_at": (now - timedelta(days=60)).isoformat(), "last_login": now.isoformat(),
        "password_hash": pw,
    }

    non_reading = [ex for ex in EXERCISE_BANK if ex.level is None]
    for name, reg_ago, n, skill, slope, last_ago in STUDENTS:
        email = name.split()[0].lower() + SUFFIX
        users[email] = {
            "email": email, "name": name, "role": "student",
            "registered_at": (now - timedelta(days=reg_ago)).isoformat(),
            "last_login": (now - timedelta(days=last_ago if last_ago is not None else reg_ago)).isoformat(),
            "password_hash": pw,
        }
        records = []
        level = 0
        for i in range(n):
            days_ago = last_ago + (reg_ago - 2 - last_ago) * (n - 1 - i) / max(1, n - 1)
            when = now - timedelta(days=days_ago, hours=float(rng.uniform(0, 6)))
            s = float(np.clip(skill + slope * i, 0.1, 0.95))
            if i % 2 == 0:
                ex = get_exercise(["reading-beginner", "reading-intermediate", "reading-advanced"][level])
            else:
                ex = non_reading[int(rng.integers(len(non_reading)))]
            record = _attempt(rng, ex, s, when)
            records.append(record)
            level = level_state(records)["level_index"]
        if records:
            for record in rng.choice(records, size=min(5, len(records)), replace=False):
                record["expert"] = {
                    "rating": _expert_rating(rng, record), "note": None, "by": therapist,
                    "at": now.isoformat(),
                }
            progress[email] = records

    settings["nimali" + SUFFIX] = {
        "assigned": [{"exercise_id": "pacing-easy-1", "by": therapist, "at": now.isoformat()}],
        "level_override": None,
        "goals": [
            {"id": uuid.uuid4().hex, "metric": "long_pauses_per_reading", "target": 1,
             "by": therapist, "created_at": now.isoformat()},
            {"id": uuid.uuid4().hex, "metric": "sessions_per_week", "target": 4,
             "by": therapist, "created_at": now.isoformat()},
        ],
        "notes": [{"id": uuid.uuid4().hex, "text": "Blocks mostly on plosives (p, b, t). Practise soft onsets.",
                   "by": therapist, "at": now.isoformat()}],
    }
    settings["amal" + SUFFIX] = {
        "assigned": [], "level_override": None,
        "goals": [{"id": uuid.uuid4().hex, "metric": "average_score", "target": 70,
                   "by": therapist, "created_at": now.isoformat()}],
        "notes": [],
    }

    _write(user_store.USERS_FILE, users)
    _write(progress_store.DATA_FILE, progress)
    _write(therapist_store.STORE_FILE, settings)
    cal = scoring.calibrate()
    print(f"Seeded {len(STUDENTS)} students + 1 therapist. Password: {PASSWORD}")
    print(f"Expert ratings: {cal['n_ratings']} · scoring model: {cal['active']} · thresholds: {cal['thresholds']}")


if __name__ == "__main__":
    clean() if "--clean" in sys.argv else seed()
