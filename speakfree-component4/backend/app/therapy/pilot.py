"""
Pilot study: did real users' practice scores change from their first week to
their last week?

For every real student (demo accounts are excluded, as they are synthetic):
  * first week  = attempts in the 7 days from their first practice
  * last week   = attempts in the 7 days up to their latest practice
A participant is included once their practice spans at least MIN_SPAN_DAYS
days and both weeks contain at least MIN_ATTEMPTS attempts. With a span under
14 days the two weeks overlap; the shared attempts count in both, which pulls
the difference towards zero, so the estimate is conservative.

Reported:
  * per participant: mean score in each week, the change, and long pauses per
    reading in each week;
  * overall: mean change with a 95% confidence interval (t distribution),
    how many improved, and an exact two-sided sign test (no assumption that
    the changes are normally distributed — suitable for 5–10 users).
"""

import math
from datetime import datetime, timedelta

from app.therapy.progress_store import all_records
from app.therapy.user_store import get_user, is_demo_account

WEEK = timedelta(days=7)
MIN_SPAN_DAYS = 7
MIN_ATTEMPTS = 2

# Two-sided 95% critical values of Student's t, by degrees of freedom.
_T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262,
         10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110,
         18: 2.101, 19: 2.093, 20: 2.086, 25: 2.060, 30: 2.042, 40: 2.021, 60: 2.000, 120: 1.980}


def _t975(df: int) -> float:
    key = min((k for k in _T975 if k >= df), default=None)
    return _T975[key] if key else 1.96


def sign_test_p(improved: int, worsened: int) -> float | None:
    """Exact two-sided sign test (ties dropped)."""
    n = improved + worsened
    if n == 0:
        return None
    k = min(improved, worsened)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return round(min(1.0, 2 * tail), 3)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _pauses(records: list[dict]) -> float | None:
    readings = [r.get("long_pauses", 0) for r in records if r.get("speaking_ratio") is not None]
    return round(_mean(readings), 1) if readings else None


def participant(user_id: str, records: list[dict]) -> dict:
    times = [datetime.fromisoformat(r["completed_at"]) for r in records]
    start, end = min(times), max(times)
    first = [r for r, t in zip(records, times) if t < start + WEEK]
    last = [r for r, t in zip(records, times) if t > end - WEEK]
    span = (end - start).days
    included = span >= MIN_SPAN_DAYS and len(first) >= MIN_ATTEMPTS and len(last) >= MIN_ATTEMPTS
    first_avg = _mean([r["score"] for r in first])
    last_avg = _mean([r["score"] for r in last])
    user = get_user(user_id)
    return {
        "student": user_id,
        "name": user["name"] if user else user_id,
        "span_days": span,
        "attempts": len(records),
        "first_week_attempts": len(first),
        "last_week_attempts": len(last),
        "first_week_score": round(first_avg, 1),
        "last_week_score": round(last_avg, 1),
        "change": round(last_avg - first_avg, 1),
        "first_week_pauses": _pauses(first),
        "last_week_pauses": _pauses(last),
        "included": included,
        "reason": None if included else (
            f"needs {MIN_SPAN_DAYS}+ days of practice (has {span})" if span < MIN_SPAN_DAYS
            else f"needs {MIN_ATTEMPTS}+ attempts in both weeks"
        ),
    }


def report() -> dict:
    rows = []
    for user_id, records in all_records().items():
        if not records or is_demo_account(user_id):
            continue
        user = get_user(user_id)
        if user and user.get("role") == "therapist":
            continue
        rows.append(participant(user_id, records))
    rows.sort(key=lambda r: (not r["included"], r["name"].lower()))

    changes = [r["change"] for r in rows if r["included"]]
    n = len(changes)
    summary = {
        "participants": n,
        "not_yet_included": sum(1 for r in rows if not r["included"]),
        "mean_first": None, "mean_last": None, "mean_change": None, "sd_change": None, "ci95": None,
        "improved": sum(1 for c in changes if c > 0),
        "worsened": sum(1 for c in changes if c < 0),
        "no_change": sum(1 for c in changes if c == 0),
        "sign_test_p": None,
    }
    if n:
        included = [r for r in rows if r["included"]]
        mean = sum(changes) / n
        summary.update(
            mean_first=round(_mean([r["first_week_score"] for r in included]), 1),
            mean_last=round(_mean([r["last_week_score"] for r in included]), 1),
            mean_change=round(mean, 1),
            sign_test_p=sign_test_p(summary["improved"], summary["worsened"]),
        )
        if n >= 2:
            sd = math.sqrt(sum((c - mean) ** 2 for c in changes) / (n - 1))
            half = _t975(n - 1) * sd / math.sqrt(n)
            summary.update(sd_change=round(sd, 1), ci95=[round(mean - half, 1), round(mean + half, 1)])
    return {
        "rules": {"week_days": 7, "min_span_days": MIN_SPAN_DAYS, "min_attempts_per_week": MIN_ATTEMPTS},
        "summary": summary,
        "participants": rows,
    }
