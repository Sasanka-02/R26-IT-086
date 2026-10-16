"""
AI Therapy Assistant - one coach, four personalities.

###########################################################################################
#  ★ COMPONENT 4 NOVELTY - CATEGORY-AWARE AI ASSISTANT                                    #
#                                                                                         #
#  answer(message, profile, plan, attempts):                                              #
#    1. Naive-Bayes intent classifier  P(intent | words) ∝ P(intent) Π P(word | intent)    #
#    2. confident (p >= threshold) -> a handler answers from the patient's OWN data        #
#       (plan, level, goals, scores) using the tip set of THEIR therapy focus:             #
#         fluency -> easy onset / pacing,  motor_speech -> loud & clear / breath,          #
#         speech_sounds -> the exact flagged sounds,  maintenance -> keep-sharp practice   #
#    3. not confident -> optional Claude model with a focus-specific system prompt         #
#    4. otherwise a safe fallback listing what the assistant can do                        #
#  Every reply reports its route (classifier / llm / fallback) and confidence.             #
#  The assistant never names a disorder or severity level - only the friendly focus name.  #
###########################################################################################
"""
from __future__ import annotations

from . import llm
from .categories import FOCI
from .exercises import SOUND_MATERIAL
from .intent_classifier import classifier

from .intent_classifier import CONFIDENCE_THRESHOLD  # noqa: E402  (single source of truth)

SUGGESTIONS = {
    "fluency": ["How am I doing?", "What should I practise next?", "Give me a tip for blocks", "Why am I doing these exercises?"],
    "motor_speech": ["How am I doing?", "How do I get a stronger voice?", "What should I practise next?", "Why am I doing these exercises?"],
    "speech_sounds": ["How am I doing?", "How do I say my practice sound?", "What should I practise next?", "Why am I doing these exercises?"],
    "maintenance": ["How am I doing?", "What should I practise next?", "When should I do another screening?", "Explain my score"],
}

EXPLAIN = {
    "daf": "Delayed Auditory Feedback plays your voice back with a tiny delay. It naturally slows and smooths speech. Use headphones and speak at a relaxed pace.",
    "pacing": "Pacing exercises highlight one word at a time at a target speed. Follow the highlight without rushing - the speed adapts to how you do.",
    "picture": "Picture description is free speech practice: describe what you see in your own words, in full sentences, pausing between ideas.",
    "reading": "Reading has three levels. Two strong readings in a row unlock the next one; two hard ones move you back so practice stays comfortable.",
    "drill": "Sound practice goes from words, to phrases, to sentences. Say each item slowly, then tick it if it felt clear. Two strong drills unlock the next step.",
}


def _first(name: str) -> str:
    return (name or "there").split()[0]


def _focus(profile: dict) -> dict:
    return FOCI[profile.get("focus", "maintenance")]


def _sound_tip(profile: dict) -> str:
    sounds = [s for s in profile.get("flagged_sounds") or [] if s in SOUND_MATERIAL]
    if not sounds:
        return FOCI["speech_sounds"]["tips"]["core"]
    mat = SOUND_MATERIAL[sounds[0]]
    return (f"Your practice sound is '{mat['name']}'. Say it on its own a few times, then in words like "
            f"{', '.join(mat['words'][:3])}. {FOCI['speech_sounds']['tips']['sound']}")


def build_briefing(name: str, profile: dict, plan: dict) -> dict:
    focus = _focus(profile)
    prog = plan["progress"]
    level = plan["level"]
    lines = [f"Your plan focuses on {focus['patient_name'].lower()}: {focus['tagline']}"]
    if prog["has_data"]:
        lines.append(f"You've completed {prog['total_sessions']} exercise{'s' if prog['total_sessions'] != 1 else ''} "
                     f"with an average score of {prog['average_score']}. {prog['trend']['detail']}")
    else:
        lines.append("Complete your first exercise and I'll start adapting your plan to you.")
    lines.append(f"Level: {level['label']}. {level['progress_text']}")
    if prog["streak_days"] >= 2:
        lines.append(f"You're on a {prog['streak_days']}-day practice streak. Nice!")
    if plan["rescreen"]["recommended"]:
        lines.append("It's a good time for a new screening - it will update your plan.")
    first = plan["today"][0]
    return {
        "greeting": f"Hi {_first(name)}!",
        "focus": {"name": focus["patient_name"], "tagline": focus["tagline"], "techniques": focus["techniques"]},
        "summary": lines,
        "tip": focus["tips"]["core"] if profile.get("focus") != "speech_sounds" else _sound_tip(profile),
        "next_step": {"exercise_id": first["id"], "title": first["title"], "reason": first["reason"]},
        "suggestions": SUGGESTIONS[focus["key"]],
        "llm_enabled": llm.is_enabled(),
    }


def _handle(intent: str, name: str, profile: dict, plan: dict, attempts: list[dict]) -> tuple[str, dict | None]:
    focus = _focus(profile)
    prog, level = plan["progress"], plan["level"]
    first = plan["today"][0]
    if intent == "greeting":
        return f"Hello {_first(name)}! How can I help with your practice today?", None
    if intent == "thanks":
        return "You're welcome! Keep going - every session counts.", None
    if intent == "explain_focus":
        return (f"Your plan focuses on {focus['patient_name'].lower()}. It was built from your screening and "
                f"adapts after every exercise. We'll work on: {'; '.join(focus['techniques'][:3]).lower()}."), None
    if intent in ("next", "level"):
        others = ", ".join(e["title"] for e in plan["today"][1:])
        reply = f"Start with \"{first['title']}\". {first['reason']}"
        if others:
            reply += f" Then: {others}."
        return reply, {"exercise_id": first["id"], "label": f"Start {first['title']}"}
    if intent == "progress":
        if not prog["has_data"]:
            return "You haven't completed an exercise yet. Do one and I'll tell you exactly how it went.", None
        last = prog["recent"][0]
        return (f"You've done {prog['total_sessions']} exercises with an average score of {prog['average_score']} "
                f"(best {prog['best_score']}). Latest: \"{last['title']}\" - {last['score']}, {last['verdict'].lower()}. "
                f"Trend: {prog['trend']['label'].lower()}."), None
    if intent == "goals":
        parts = [f"{g['text']} ({'done ✓' if g['met'] else 'now ' + str(g['current'] if g['current'] is not None else '-')})"
                 for g in plan["goals"][:4]]
        return "Your goals: " + "; ".join(parts) + ".", None
    if intent == "score_explain":
        if not attempts:
            return "Once you save an exercise I can explain exactly how its score was worked out.", None
        last = attempts[-1]
        top = sorted(last.get("score_breakdown") or [], key=lambda p: abs(p["points"]), reverse=True)
        detail = "; ".join(f"{p['label']}: {p['points']:+g}" for p in top if p["feature"] != "intercept")[:300]
        return f"Your last score ({last['score']}) adds up points from each part of the attempt. Biggest effects - {detail}.", None
    if intent in ("tip_pause", "tip_speed"):
        key = "pause" if intent == "tip_pause" else "speed"
        return focus["tips"].get(key) or FOCI["fluency"]["tips"][key], None
    if intent in ("tip_volume", "tip_voice"):
        return FOCI["motor_speech"]["tips"]["volume" if intent == "tip_volume" else "core"], None
    if intent == "tip_sound":
        return _sound_tip(profile), None
    if intent == "tip_general":
        tip = _sound_tip(profile) if focus["key"] == "speech_sounds" else focus["tips"]["core"]
        return f"Here's a tip for “{focus['patient_name']}”: {tip}", None
    if intent == "anxiety":
        return ("It's completely fine if this feels hard. Short, relaxed sessions every day help more than long, "
                "stressful ones - try an easier exercise first and breathe slowly before you start."), None
    if intent == "streak":
        return (f"Your current streak is {prog['streak_days']} day{'s' if prog['streak_days'] != 1 else ''}. "
                f"Your plan asks for {plan['dose']['sessions_per_week']} short sessions a week."), None
    if intent == "rescreen":
        r = plan["rescreen"]
        if r["recommended"]:
            return f"Now is a good time for a new screening ({', '.join(r['reasons'])}). It will update your plan.", {"href": "/assessment", "label": "Start a new screening"}
        return (f"Your next screening is suggested in about {r['due_in_days']} days or after "
                f"{r['attempts_until_due']} more exercises - whichever comes first."), None
    if intent == "privacy":
        return ("Your practice recordings never leave your browser. Only small numbers (how long you spoke, pauses, "
                "speed) and your rating are saved. Your clinician can see your results; nobody else can."), None
    if intent == "badges":
        return f"You've completed {prog['total_sessions']} exercises - keep going to unlock the next level!", None
    if intent.startswith("explain_"):
        kind = intent.split("_", 1)[1]
        return EXPLAIN.get(kind, ""), None
    return "", None


FALLBACK = ("I'm not sure about that one. I can tell you how you're doing, what to practise next, explain your plan "
            "and your score, or give tips for your practice.")


def _llm_context(plan: dict, attempts: list[dict]) -> dict:
    return {
        "level": plan["level"]["label"],
        "level_progress": plan["level"]["progress_text"],
        "exercises_completed": plan["progress"]["total_sessions"],
        "average_score": plan["progress"]["average_score"],
        "trend": plan["progress"]["trend"]["label"],
        "recent": [{"exercise": r["title"], "score": r["score"], "felt": r["self_rating"]} for r in attempts[-5:]],
        "goals": [{"goal": g["text"], "met": g["met"]} for g in plan["goals"]],
        "today": [{"exercise": e["title"], "why": e["reason"]} for e in plan["today"]],
    }


def answer(message: str, name: str, profile: dict, plan: dict, attempts: list[dict]) -> dict:
    focus = _focus(profile)
    base = {"suggestions": SUGGESTIONS[focus["key"]], "action": None}
    text = message.strip()
    if not text:
        return {**base, "reply": "Ask me anything about your practice - for example, \"How am I doing?\"",
                "intent": None, "confidence": 0.0, "source": "fallback"}
    intent, confidence = classifier.predict(text)
    if confidence >= CONFIDENCE_THRESHOLD:
        reply, action = _handle(intent, name, profile, plan, attempts)
        if reply:
            return {**base, "reply": reply, "action": action, "intent": intent,
                    "confidence": round(confidence, 2), "source": "classifier"}
    llm_reply = llm.ask(text, _first(name), focus, _llm_context(plan, attempts))
    if llm_reply:
        return {**base, "reply": llm_reply, "intent": intent, "confidence": round(confidence, 2), "source": "llm"}
    return {**base, "reply": FALLBACK, "intent": intent, "confidence": round(confidence, 2), "source": "fallback"}
