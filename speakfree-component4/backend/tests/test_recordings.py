from tests.conftest import save_result, signup

AUDIO = b"\x1aE\xdf\xa3fake-webm-audio" * 10


def test_student_recording_reaches_the_therapist(client):
    therapist = signup(client, "dr@x.com", role="therapist")
    student = signup(client, "a@x.com")
    other = signup(client, "b@x.com")
    rec = save_result(client, student, "a@x.com")["record"]
    url = f"/api/v1/therapy/recordings/a@x.com/{rec['id']}"

    up = client.put(url, content=AUDIO, headers={**student, "Content-Type": "audio/webm;codecs=opus"})
    assert up.status_code == 200 and up.json()["bytes"] == len(AUDIO)

    detail = client.get("/api/v1/therapist/students/a@x.com", headers=therapist).json()
    assert detail["records"][0]["has_recording"]
    heard = client.get(url, headers=therapist)
    assert heard.status_code == 200 and heard.content == AUDIO and heard.headers["content-type"].startswith("audio/webm")
    # The therapist rates it after listening.
    rated = client.put(f"/api/v1/therapist/students/a@x.com/records/{rec['id']}/rating",
                       json={"rating": 4, "heard_audio": True}, headers=therapist)
    assert rated.status_code == 200
    # Nobody else can hear it.
    assert client.get(url, headers=other).status_code == 403
    assert client.put(url, content=AUDIO, headers={**other, "Content-Type": "audio/webm"}).status_code == 403


def test_bad_uploads_are_rejected(client):
    student = signup(client, "a@x.com")
    rec = save_result(client, student, "a@x.com")["record"]
    url = f"/api/v1/therapy/recordings/a@x.com/{rec['id']}"
    assert client.put(url, content=b"<script>", headers={**student, "Content-Type": "text/html"}).status_code == 400
    assert client.put(url, content=b"", headers={**student, "Content-Type": "audio/webm"}).status_code == 400
    missing = "/api/v1/therapy/recordings/a@x.com/nope"
    assert client.put(missing, content=AUDIO, headers={**student, "Content-Type": "audio/webm"}).status_code == 404
    assert client.get(url, headers=student).status_code == 404  # nothing uploaded yet


def test_student_can_switch_sharing_off_and_deletion_removes_recordings(client):
    therapist = signup(client, "dr@x.com", role="therapist")
    student = signup(client, "a@x.com")
    rec = save_result(client, student, "a@x.com")["record"]
    url = f"/api/v1/therapy/recordings/a@x.com/{rec['id']}"
    client.put(url, content=AUDIO, headers={**student, "Content-Type": "audio/webm"})

    off = client.put("/api/v1/auth/me/recording-sharing", json={"share": False}, headers=student)
    assert off.json()["share_recordings"] is False
    assert client.put(url, content=AUDIO, headers={**student, "Content-Type": "audio/webm"}).status_code == 409

    client.delete("/api/v1/auth/me", headers=student)
    assert client.get(url, headers=therapist).status_code == 404
