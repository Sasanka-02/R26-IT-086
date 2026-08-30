from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "whisper_loaded" in body
    assert "hubert_loaded" in body


def test_extract_features_rejects_bad_mime_type():
    files = {"audio_file": ("test.txt", b"not audio", "text/plain")}
    data = {
        "task_type": "picture_description",
        "session_id": "test-session",
        "age_category": "adults",
    }
    response = client.post("/api/v1/extract-features", files=files, data=data)
    assert response.status_code == 415
