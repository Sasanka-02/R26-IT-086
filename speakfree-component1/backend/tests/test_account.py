"""Account settings + appointment requests."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

import main
from database import SessionLocal, run_migrations
from seed import seed
from tests.test_db import admin_headers, login, register


@pytest.fixture(scope="module")
def client():
    run_migrations()
    with SessionLocal() as db:
        seed(db)
    return TestClient(main.app)


def test_update_name_and_change_password(client):
    acc = register(client, age=13)
    r = client.patch("/api/v1/auth/me", headers=acc["headers"], json={"full_name": "New Name"})
    assert r.status_code == 200
    me = client.get("/api/v1/auth/me", headers=acc["headers"]).json()
    assert me["full_name"] == "New Name" and me["patients"][0]["full_name"] == "New Name"

    bad = client.post("/api/v1/auth/change-password", headers=acc["headers"],
                      json={"current_password": "wrong-pass", "new_password": "newpassword1"})
    assert bad.status_code == 400
    ok = client.post("/api/v1/auth/change-password", headers=acc["headers"],
                     json={"current_password": "password123", "new_password": "newpassword1"})
    assert ok.status_code == 204
    assert login(client, acc["email"], "newpassword1").status_code == 200
    assert login(client, acc["email"], "password123").status_code == 401


def test_appointment_request_flow(client):
    acc = register(client, role="guardian", age=9)
    pid = acc["user"]["patients"][0]["id"]
    body = {"patient_id": pid, "preferred_date": (date.today() + timedelta(days=3)).isoformat(),
            "preferred_time": "morning", "mode": "online", "reason": "Follow-up on screening results"}
    r = client.post("/api/v1/appointments", headers=acc["headers"], json=body)
    assert r.status_code == 201, r.text
    appt = r.json()
    assert appt["status"] == "pending"
    past = {**body, "preferred_date": (date.today() - timedelta(days=1)).isoformat()}
    assert client.post("/api/v1/appointments", headers=acc["headers"], json=past).status_code == 422

    other = register(client, age=12)
    assert client.post("/api/v1/appointments", headers=other["headers"], json=body).status_code == 404
    assert client.get("/api/v1/admin/appointments", headers=acc["headers"]).status_code == 403

    h = admin_headers(client)
    assert any(a["id"] == appt["id"] for a in client.get("/api/v1/admin/appointments?status=pending", headers=h).json())
    assert client.patch(f"/api/v1/admin/appointments/{appt['id']}", headers=h, json={"status": "confirmed"}).status_code == 422
    when = f"{(date.today() + timedelta(days=4)).isoformat()}T10:00:00+05:30"
    r = client.patch(f"/api/v1/admin/appointments/{appt['id']}", headers=h,
                     json={"status": "confirmed", "scheduled_at": when, "admin_note": "Zoom link by e-mail"})
    assert r.json()["status"] == "confirmed" and r.json()["scheduled_at"]
    mine = client.get("/api/v1/appointments", headers=acc["headers"]).json()
    assert mine[0]["status"] == "confirmed" and mine[0]["admin_note"] == "Zoom link by e-mail"
    assert client.post(f"/api/v1/appointments/{appt['id']}/cancel", headers=acc["headers"]).json()["status"] == "cancelled"
