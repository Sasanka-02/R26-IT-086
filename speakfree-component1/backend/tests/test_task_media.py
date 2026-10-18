"""
Screening task media: short scenario videos (upload rules, serving, task payload), media linking
by file name, and the custom picture / scenario content that replaces the starter tasks.
"""
import pytest
from fastapi.testclient import TestClient

import main
import seed as seed_module
from custom_tasks import CUSTOM_TASKS, DISABLED_TASKS, apply_custom
from database import AssessmentTask, SessionLocal, run_migrations
from seed import seed
from task_bank import seed_rows
from task_service import task_payload
from tests.test_db import admin_headers, register

MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64   # ISO-BMFF "ftyp" box at byte 4
WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture(scope="module")
def client():
    run_migrations()
    with SessionLocal() as db:
        seed(db)
    return TestClient(main.app)


def task_form(task_type="scenario", bracket="4"):
    return {"age_bracket": bracket, "task_type": task_type, "title": "Video task", "instructions": "Watch, then answer.",
            "content_text": "What happens in the video?"}


# --------------------------------------------------------------------------- upload rules
def test_scenario_accepts_mp4_and_webm_videos(client):
    h = {"Authorization": f"Bearer {register(client, role='clinician')['token']}"}
    for name, data, ctype in (("clip.mp4", MP4, "video/mp4"), ("clip.webm", WEBM, "video/webm")):
        r = client.post("/api/v1/admin/tasks", headers=h, data=task_form(), files={"image": (name, data, ctype)})
        assert r.status_code == 201, r.text
        task = r.json()
        assert task["video_url"].endswith(name.removeprefix("clip")) and task["image_url"] is None
        served = client.get(task["video_url"].replace("http://testserver", ""))
        assert served.status_code == 200 and served.headers["content-type"] == ctype


def test_videos_only_for_scenarios_and_must_be_real(client):
    h = admin_headers(client)
    picture = client.post("/api/v1/admin/tasks", headers=h, data=task_form("picture"), files={"image": ("clip.mp4", MP4, "video/mp4")})
    assert picture.status_code == 422 and "scenario" in picture.json()["detail"]
    fake = client.post("/api/v1/admin/tasks", headers=h, data=task_form(), files={"image": ("clip.mp4", PNG, "video/mp4")})
    assert fake.status_code == 422
    other = client.post("/api/v1/admin/tasks", headers=h, data=task_form(), files={"image": ("clip.avi", MP4, "video/x-msvideo")})
    assert other.status_code == 422


def test_replacing_a_video_with_a_picture(client):
    h = admin_headers(client)
    task = client.post("/api/v1/admin/tasks", headers=h, data=task_form(), files={"image": ("clip.mp4", MP4, "video/mp4")}).json()
    updated = client.patch(f"/api/v1/admin/tasks/{task['id']}", headers=h, files={"image": ("still.png", PNG, "image/png")}).json()
    assert updated["video_url"] is None and updated["image_url"].endswith(".png")


# --------------------------------------------------------------------------- patient payload + linking by file name
def test_scenario_payload_carries_the_video_url():
    task = AssessmentTask(id="b4-scn-9", age_bracket=4, task_type="scenario", title="T", instructions="I",
                          content_text="P", image_path="tasks/b4-scn-9.mp4", keywords=[], max_seconds=60)
    payload = task_payload(task, "http://api/")
    assert payload["video_url"] == "http://api/static/tasks/b4-scn-9.mp4" and payload["image_url"] is None


def test_seed_links_videos_only_to_scenarios(tmp_path):
    (tmp_path / "tasks").mkdir()
    (tmp_path / "tasks" / "b2-scn-1.mp4").write_bytes(MP4)
    (tmp_path / "tasks" / "b2-pic-1.mp4").write_bytes(MP4)
    assert seed_module.find_task_image("b2-scn-1", str(tmp_path), "scenario") == "tasks/b2-scn-1.mp4"
    assert seed_module.find_task_image("b2-pic-1", str(tmp_path), "picture") is None


# --------------------------------------------------------------------------- custom content
def test_custom_content_covers_two_pictures_and_two_scenarios_per_bracket():
    ids = {r["id"]: r for r in seed_rows()}
    assert set(CUSTOM_TASKS) <= set(ids)
    for b in range(1, 8):
        for kind in ("pic", "scn"):
            assert {f"b{b}-{kind}-1", f"b{b}-{kind}-2"} <= set(CUSTOM_TASKS)
            assert f"b{b}-{kind}-3" in DISABLED_TASKS
    for task_id, custom in CUSTOM_TASKS.items():
        if "-pic-" in task_id:
            assert len(custom["keywords"]) >= 8 and all(k == k.lower() and " " not in k for k in custom["keywords"])


def test_new_databases_get_custom_text_and_two_active_per_type():
    rows = [apply_custom(r) for r in seed_rows()]
    by_id = {r["id"]: r for r in rows}
    assert by_id["b1-pic-1"]["title"] == "Flying Kites" and by_id["b3-scn-2"]["title"] == "The Race"
    for b in range(1, 8):
        for task_type in ("picture", "scenario"):
            active = [r for r in rows if r["age_bracket"] == b and r["task_type"] == task_type and r["is_active"]]
            assert len(active) == 2, (b, task_type)
