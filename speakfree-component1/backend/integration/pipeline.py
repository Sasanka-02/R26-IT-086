"""
Backend pipeline for one finalised screening session:  C1 -> C2 -> C3 -> C4.

Called by POST /api/v1/sessions/{id}/finalize right after Component 1 has pooled the session
(and by the admin "re-run" button). Every stage runs in-process and its output is stored, so
the admin dashboards can show each hand-off. Patients never see C2/C3 output - only the plan
that C4 builds from it.

A failure in C2/C3/C4 never fails the patient's screening: the run is stored as "failed" /
"partial" with the error, and the admin can re-run it.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import Analysis, PipelineRun, ScreeningSession, TherapyProfile

from . import COMPONENT_DIRS  # noqa: F401  (sys.path bootstrap)

log = logging.getLogger("speakfree.integration")


def _recordings(db: Session, summary: dict) -> list[dict]:
    ids = [t["analysis_id"] for t in summary.get("tasks", [])]
    rows = db.scalars(select(Analysis).where(Analysis.id.in_(ids))).all() if ids else []
    order = {aid: i for i, aid in enumerate(ids)}
    return [json.loads(r.result_json) for r in sorted(rows, key=lambda r: order[r.id])]


def run_session_pipeline(db: Session, session_id: str) -> PipelineRun:
    from component2 import run_component2
    from component3 import run_component3
    from component4 import build_profile

    session = db.get(ScreeningSession, session_id)
    if session is None:
        raise ValueError(f"Unknown session {session_id}")
    summary = json.loads(session.summary_json)
    run = db.get(PipelineRun, session_id) or PipelineRun(session_id=session_id, patient_id=session.patient_id)
    timings: dict[str, int] = {}
    c2 = c3 = None
    run.error = None

    try:
        # ---- Component 2: articulation score (C1 session JSON in, C3 hand-off out) ----
        t0 = time.perf_counter()
        titles = {t["task_id"]: t["title"] for t in summary.get("tasks", [])}
        c2 = run_component2(summary, _recordings(db, summary), titles)
        timings["component2_ms"] = int((time.perf_counter() - t0) * 1000)
        if not c2["ready_for_component3"]:
            raise RuntimeError(c2["session_articulation"].get("message") or "Component 2 produced no hand-off")

        # ---- Component 3: model-based severity classification ----
        t0 = time.perf_counter()
        c3 = run_component3(session_id, session.patient_id, c2)
        timings["component3_ms"] = int((time.perf_counter() - t0) * 1000)

        # ---- Component 4: therapy profile (the plan itself is rebuilt on every request) ----
        t0 = time.perf_counter()
        existing = db.scalar(select(TherapyProfile).where(TherapyProfile.session_id == session_id))
        created = (existing.created_at if existing else datetime.now(timezone.utc))
        created_iso = (created if created.tzinfo else created.replace(tzinfo=timezone.utc)).isoformat(timespec="seconds")
        profile = build_profile(c3, summary, c2, created_at=created_iso, session_id=session_id)
        if existing is None:
            existing = TherapyProfile(patient_id=session.patient_id, session_id=session_id, created_at=created)
            db.add(existing)
        existing.focus = profile["focus"]
        existing.severity_level = profile["severity_level"]
        existing.profile_json = json.dumps(profile)
        timings["component4_ms"] = int((time.perf_counter() - t0) * 1000)
        run.status = "completed"
    except Exception as exc:  # stored for the admin, never raised to the patient
        log.exception("Pipeline failed for session %s", session_id)
        run.status = "partial" if c2 else "failed"
        run.error = f"{type(exc).__name__}: {exc}"

    run.articulation_score = (c2 or {}).get("session_articulation", {}).get("score")
    run.primary_disorder = (c3 or {}).get("primary_disorder")
    run.severity_level = (c3 or {}).get("severity_level")
    run.risk_level = (c3 or {}).get("risk_level")
    run.therapy_focus = (c3 or {}).get("therapy_focus")
    run.c2_json = json.dumps(c2) if c2 else None
    run.c3_json = json.dumps(c3) if c3 else None
    run.stage_timings_json = json.dumps(timings)
    run.created_at = datetime.now(timezone.utc)
    if run not in db:
        db.add(run)
    db.commit()
    return run
