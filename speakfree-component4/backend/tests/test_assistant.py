from app.therapy.assistant import answer
from app.therapy.intent_classifier import CONFIDENCE_THRESHOLD, classifier, leave_one_out_accuracy


def test_classifier_cross_validated_accuracy():
    assert leave_one_out_accuracy()["accuracy"] >= 80


def test_known_questions_are_classified():
    assert classifier.predict("how am i doing lately")[0] == "progress"
    assert classifier.predict("i talk too fast")[0] == "tip_speed"
    assert classifier.predict("why is my score so low")[0] == "score_explain"


def test_out_of_domain_is_not_guessed():
    _, confidence = classifier.predict("what is the weather in colombo")
    assert confidence < CONFIDENCE_THRESHOLD


def test_answers_are_personal():
    records = [{
        "id": "1", "exercise_id": "reading-beginner", "exercise_type": "reading", "title": "Reading",
        "level": "beginner", "score": 88, "self_rating": "ok", "duration_seconds": 40,
        "speaking_ratio": 0.8, "long_pauses": 0, "quiet_warnings": 0,
        "completed_at": "2026-01-01T10:00:00+00:00",
    }]
    with_data = answer("a@x.com", "Amal", "how am i doing", records)
    without = answer("b@x.com", "Bina", "how am i doing", [])
    assert with_data["source"] == "classifier"
    assert "88" in with_data["reply"]
    assert with_data["reply"] != without["reply"]


def test_unknown_question_uses_fallback_without_llm(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    reply = answer("a@x.com", "Amal", "tell me a joke about cats", [])
    assert reply["source"] == "fallback"
