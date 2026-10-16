"""
Therapy Assistant — a personal coach grounded in the student's own data.

Pipeline for a chat message:
  1. The Naive Bayes intent classifier (intent_classifier.py) predicts the
     intent and a confidence.
  2. Confident -> a handler builds the answer from the student's records,
     goals, badges, plan and score breakdown.
  3. Not confident -> the optional language model (llm.py) answers using a
     summary of the same data; if it is not configured, a safe fallback
     lists what the assistant can help with.

Every reply reports which route produced it (classifier / llm / fallback)
and the classifier's confidence, so the behaviour is transparent.
"""

from app.therapy import llm
from app.therapy.adaptive import LEVEL_LABELS
from app.therapy.bandit import recommend_weekly_plan
from app.therapy.exercises import exercises_for
from app.therapy.dashboard import build_progress_summary
from app.therapy.intent_classifier import CONFIDENCE_THRESHOLD, classifier
from app.therapy.therapist_store import get_settings

DEFAULT_SUGGESTIONS = [
    "How am I doing?",
    "What should I practise next?",
    "Why did I get this score?",
    "Am I meeting my goals?",
    "Give me a tip for long pauses",
]

GENERAL_TIPS = {
    "pause": (
        "When you feel a block or a long pause coming, stop, take a slow breath "
        "through your nose, and restart the word gently with a soft, easy onset. "
        "Pausing on purpose between ideas is a strength, not a mistake."
    ),
    "volume": (
        "Sit up straight, take a comfortable breath from your belly, and imagine "
        "your voice reaching someone across the room. Aim for steady, relaxed volume."
    ),
    "flow": (
        "Try linking words together smoothly, as if the sentence were one long word. "
        "Keep your voice gently 'on' between words instead of stopping after each one."
    ),
    "speed": (
        "Follow the highlighted word rather than racing ahead. Stretch the first sound "
        "of each phrase slightly and pause at commas — a slower, even pace usually "
        "means fewer blocks."
    ),
    "comfort": (
        "If an exercise feels hard, it's completely fine to go back to an easier one. "
        "Short, relaxed sessions every day help more than long, stressful ones. "
        "Try the breathing warm-up before you start."
    ),
    "challenge": (
        "You're doing well — try the next reading level, or use the picture "
        "descriptions to practise speaking in your own words."
    ),
    "words": (
        "Tip: press 🔊 Listen first, take a slow breath, then start the word softly — "
        "stretch the first sound a little (mmm-oon) and keep it gentle. For words that "
        "start with two sounds together (sp, tr, bl), slide them slowly."
    ),
}

EXERCISE_EXPLANATIONS = {
    "daf": (
        "Delayed Auditory Feedback (DAF) plays your voice back to you with a tiny delay. "
        "Many people find it naturally slows their speech and smooths the rhythm. "
        "Use headphones, start with the calibrated delay, and speak at a relaxed pace."
    ),
    "pacing": (
        "Pacing exercises highlight one word at a time at a target speed. Follow the "
        "highlight without rushing. The speed adapts to you: strong attempts speed it up "
        "a little, difficult ones slow it down."
    ),
    "picture": (
        "Picture description is free speech practice: describe what you see in your "
        "own words. Use the guiding questions if you get stuck, and pause between ideas."
    ),
    "words": (
        "Word practice is a picture-card game. Each round shows one picture and word at a time: "
        "press 🔊 Listen to hear it said slowly, then 🎤 Say it, and tap 😊 Got it, 😐 Almost or "
        "😟 Hard. There are 7 word levels — easy starting sounds, then early sounds, two-syllable "
        "words, middle sounds, late sounds, clusters and long tricky words — and then a phrase "
        "stage with short phrases, sentences and tongue twisters. One good round moves you up a "
        "level; two hard ones in a row take you back one, so it never gets too hard."
    ),
    "reading": (
        "Reading practice has three levels: Beginner, Intermediate and Advanced (the "
        "final stage). One strong reading unlocks the next level, and if two in a "
        "row feel hard, you'll move back a level so practice stays comfortable."
    ),
}

# --- Talking to each age group -------------------------------------------------
# child: very short, simple, cheerful, with an emoji; teen: friendly and
# encouraging; adult: respectful and professional (the default texts above).
KID_TIPS = {
    "pause": "Stuck on a word? 🌬️ Take a slow breath and start again, nice and soft. You can do it!",
    "volume": "Use your big lion voice! 🦁 Breathe in, then speak to the back of the room.",
    "flow": "Glue your words together like a long snake 🐍 — smooth and slow.",
    "speed": "Be a slow snail 🐌 — follow the yellow word and don't rush.",
    "comfort": "Hard today? That's okay! 💛 Try an easy one and have fun.",
    "challenge": "Wow, you're doing great! ⭐ Try the next level!",
    "words": "Press 🔊 Listen, take a breath, then say it softly. ⭐",
}
KID_EXPLANATIONS = {
    "words": "Look at the picture, press 🔊 Listen, then say the word! Tap 😊 if it was easy. ⭐",
    "reading": "Read the little story slowly with the yellow word. One good try moves you up! 🚀",
    "picture": "Look at the picture and tell me what you see. 🖼️ There are no wrong answers!",
    "pacing": "Follow the yellow word like a slow snail 🐌. Nice and steady!",
    "daf": "You hear your own voice a tiny bit late. It helps you talk slowly. 🎧",
}
TEEN_CHEERS = {
    "progress": " Keep it up — you're building a real skill. 💪",
    "next": " You've got this!",
    "level": " Every strong attempt counts.",
    "streak": " Nice consistency!",
}
EXERCISE_EXPLANATIONS_ROLEPLAY = (
    "Role-plays put you in a real situation — a phone call, an interview or a class talk. Read the "
    "situation, then answer each line out loud. Use the example answers if you get stuck, and pause "
    "between ideas."
)


def _kid(text: str) -> str:
    """First sentence only, plus a friendly emoji — short and simple for children."""
    first = text.split(". ")[0].rstrip(".!")
    return f"{first}! ⭐"


def _exercise_id(age_group: str, kind: str, level: str | None = None) -> str | None:
    """An exercise of this kind (and level) that suits the age group."""
    for ex in exercises_for(age_group):
        if ex.type.value == kind and (level is None or (ex.level and ex.level.value == level)):
            return ex.id
    return None


def _style(reply: str, intent: str, age_group: str) -> str:
    if age_group == "child":
        if intent.startswith("tip_") or intent == "anxiety":
            key = {"tip_pause": "pause", "tip_volume": "volume", "tip_speed": "speed", "anxiety": "comfort"}[intent]
            return KID_TIPS[key]
        if intent.startswith("explain_"):
            return KID_EXPLANATIONS.get(intent.split("_", 1)[1], _kid(reply))
        return _kid(reply)
    if age_group == "teen":
        if intent in ("greeting", "thanks", "privacy"):
            return reply
        return reply + TEEN_CHEERS.get(intent, " You've got this! 💪")
    return reply


FOCUS_TITLES = {
    "pause": "Smoother starts after pauses",
    "volume": "A clear, steady voice",
    "flow": "Keeping a continuous flow",
    "speed": "A slower, even pace",
    "comfort": "Practising at a comfortable level",
    "challenge": "Taking on a new challenge",
}


def _first_name(name: str) -> str:
    return (name or "there").split()[0]


def _focus_area(records: list[dict]) -> str:
    recent = records[-5:]
    if not recent:
        return "flow"
    if sum(1 for r in recent if r["self_rating"] == "hard") >= 2:
        return "comfort"
    live = [r for r in recent if r.get("speaking_ratio") is not None]
    if live:
        if sum(r["long_pauses"] for r in live) / len(live) >= 1:
            return "pause"
        fast = [r for r in live if r.get("measured_wpm") and r.get("target_wpm")]
        if fast and sum(r["measured_wpm"] > 1.15 * r["target_wpm"] for r in fast) >= 2:
            return "speed"
        if sum(r["quiet_warnings"] for r in live) / len(live) >= 2:
            return "volume"
        if sum(r["speaking_ratio"] for r in live) / len(live) < 0.45:
            return "flow"
    if sum(r["score"] for r in recent) / len(recent) >= 75:
        return "challenge"
    return "flow"


def _context(user_id: str, records: list[dict]) -> tuple[dict, dict, dict]:
    settings = get_settings(user_id)
    summary = build_progress_summary(user_id, records)
    plan = recommend_weekly_plan(records, settings, age_group=summary["age_group"])
    return settings, summary, plan


def build_briefing(user_id: str, name: str, records: list[dict]) -> dict:
    settings, summary, plan = _context(user_id, records)
    level = summary["level"]
    next_ex = plan["exercises"][0]

    if not summary["has_data"]:
        lines = [
            "Welcome! I'm your practice assistant. I learn from every exercise you "
            "complete and adjust your plan to suit you.",
            f"You're starting at the {level['label']} level. {level['progress_text']}",
        ]
    else:
        lines = [
            f"You've completed {summary['total_sessions']} exercise"
            f"{'s' if summary['total_sessions'] != 1 else ''} "
            f"({summary['total_minutes']} minutes) with an average score of {summary['average_score']}.",
            f"Trend: {summary['trend']['label']} — {summary['trend']['detail']}",
            f"Your level: {level['label']}. {level['progress_text']}",
        ]
        if summary["streak_days"] >= 2:
            lines.append(f"You're on a {summary['streak_days']}-day practice streak. Nice!")
    met = [g for g in summary["goals"] if g["met"]]
    if summary["goals"]:
        lines.append(f"Therapist goals: {len(met)} of {len(summary['goals'])} met this week.")

    focus = _focus_area(records)
    kid = summary["age_group"] == "child"
    if kid:
        lines = [_kid(line) for line in lines[:3]]
    return {
        "greeting": f"Hi {_first_name(name)}! 👋" if kid else f"Hi {_first_name(name)}!",
        "summary": lines,
        "focus": {"title": FOCUS_TITLES[focus], "tip": KID_TIPS[focus] if kid else GENERAL_TIPS[focus]},
        "next_step": {
            "exercise_id": next_ex["id"],
            "title": next_ex["title"],
            "reason": next_ex["reason"],
        },
        "goals": summary["goals"],
        "badges_earned": sum(1 for b in summary["badges"] if b["earned"]),
        "badges_total": len(summary["badges"]),
        "suggestions": DEFAULT_SUGGESTIONS,
        "llm_enabled": llm.is_enabled(),
    }


def _handle(intent: str, name: str, records: list[dict], summary: dict, plan: dict) -> tuple[str, dict | None]:
    reply, action = _handle_plain(intent, name, records, summary, plan)
    if action and action.get("exercise_id") is None:
        action = None  # that kind of exercise isn't part of this age group's practice
    return (_style(reply, intent, summary["age_group"]) if reply else reply), action


def _handle_plain(intent: str, name: str, records: list[dict], summary: dict, plan: dict) -> tuple[str, dict | None]:
    level = summary["level"]
    group = summary["age_group"]
    level_ex = next((e["id"] for e in plan["exercises"] if e["source"] == "level"),
                    _exercise_id(group, "reading", level["level"]))
    if intent == "greeting":
        return f"Hello {_first_name(name)}! How can I help with your practice today?", None
    if intent == "thanks":
        return "You're welcome! Keep going — every session counts.", None
    if intent == "level":
        return (
            f"You're at the {level['label']} level. {level['progress_text']}",
            {"exercise_id": level_ex, "label": f"Start a {LEVEL_LABELS[level['level']]} exercise"},
        )
    if intent == "next":
        first = plan["exercises"][0]
        others = ", ".join(e["title"] for e in plan["exercises"][1:])
        reply = f"I'd start with “{first['title']}”. {first['reason']}"
        if others:
            reply += f" After that, try: {others}."
        return reply, {"exercise_id": first["id"], "label": f"Start {first['title']}"}
    if intent == "progress":
        if not summary["has_data"]:
            return "You haven't completed any exercises yet. Finish one and I'll tell you exactly how it went.", None
        last = summary["recent"][0]
        return (
            f"You've done {summary['total_sessions']} exercises with an average score of "
            f"{summary['average_score']} (best {summary['best_score']}). "
            f"Your latest was “{last['title']}” — {last['score']}, {last['verdict'].lower()}. "
            f"Overall trend: {summary['trend']['label'].lower()}.",
            None,
        )
    if intent == "goals":
        goals = summary["goals"]
        if not goals:
            return "Your therapist hasn't set any goals yet. Your plan still adapts to your results.", None
        parts = [
            f"{g['text']}: now {g['current'] if g['current'] is not None else 'no data'} "
            f"({'met ✓' if g['met'] else 'not yet'})"
            for g in goals
        ]
        return "Your goals this week — " + "; ".join(parts) + ".", None
    if intent == "badges":
        earned = [b["title"] for b in summary["badges"] if b["earned"]]
        locked = [b for b in summary["badges"] if not b["earned"]]
        reply = (f"You've earned {len(earned)} badge{'s' if len(earned) != 1 else ''}: {', '.join(earned)}."
                 if earned else "No badges yet — complete your first exercise to earn one.")
        if locked:
            reply += f" Next one to aim for: “{locked[0]['title']}” — {locked[0]['description'].lower()}."
        return reply, None
    if intent == "score_explain":
        if not records:
            return "Once you save an exercise I can explain exactly how its score was worked out.", None
        last = records[-1]
        parts = last.get("score_breakdown") or []
        if not parts:
            return f"Your last score was {last['score']}. It comes from how steadily you spoke, long pauses, volume, speed and how it felt.", None
        top = sorted(parts, key=lambda p: abs(p["points"]), reverse=True)[:4]
        detail = "; ".join(f"{p['label']}: {p['points']:+g}" for p in top if p["feature"] != "intercept")
        return (
            f"Your last score ({last['score']}) for “{last['title']}” adds up points from each part of "
            f"the attempt. Biggest effects — {detail}. These weights are calibrated against "
            "therapist ratings, not guessed.",
            None,
        )
    if intent == "tip_pause":
        return GENERAL_TIPS["pause"], None
    if intent == "tip_volume":
        return GENERAL_TIPS["volume"], None
    if intent == "tip_speed":
        timed = [r for r in records if r.get("measured_wpm")]
        extra = (f" Your last measured speed was about {timed[-1]['measured_wpm']} words/min "
                 f"(target {timed[-1]['target_wpm']}).") if timed else ""
        return GENERAL_TIPS["speed"] + extra, {"exercise_id": _exercise_id(group, "pacing"), "label": "Start pacing"}
    if intent == "anxiety":
        return GENERAL_TIPS["comfort"], {
            "exercise_id": _exercise_id(group, "reading", "beginner") or _exercise_id(group, "words", "beginner"),
            "label": "Start an easy exercise",
        }
    if intent == "streak":
        return (
            f"Your current streak is {summary['streak_days']} day{'s' if summary['streak_days'] != 1 else ''}. "
            "Short daily practice (10–15 minutes) works better than occasional long sessions.",
            None,
        )
    if intent == "privacy":
        return (
            "Your voice recordings never leave your browser. Only small numbers (how long you spoke, "
            "long pauses, speed) plus your rating are saved, under your account. Your therapist can see "
            "your results; other students cannot.",
            None,
        )
    if intent.startswith("explain_"):
        kind = intent.split("_", 1)[1]
        action = {
            "daf": {"exercise_id": _exercise_id(group, "daf"), "label": "Start DAF"},
            "pacing": {"exercise_id": _exercise_id(group, "pacing"), "label": "Start pacing"},
            "picture": {"exercise_id": _exercise_id(group, "picture"), "label": "Start picture description"},
            "reading": {"exercise_id": level_ex, "label": "Start your level"},
            "words": {
                "exercise_id": summary["word_level"]["exercise_id"] if group == "child" else None,
                "label": "Start word practice",
            },
        }[kind]
        reply = EXERCISE_EXPLANATIONS[kind]
        if kind == "reading":
            reply = (
                f"Your practice has three levels — Beginner, Intermediate and Advanced — made for your age group. "
                f"One strong attempt unlocks the next level; two hard ones in a row move you back. "
                f"You're currently at {level['label']}."
            )
            if group != "child":
                reply += " " + EXERCISE_EXPLANATIONS_ROLEPLAY
        if kind == "words":
            reply += f" {summary['word_level']['progress_text']} {GENERAL_TIPS['words']}"
        return reply, action
    return "", None


FALLBACK = (
    "I'm not sure about that one. I can tell you how you're doing, what to practise next, "
    "your level and goals, explain your score, or give tips for pauses, speed and volume."
)


def _llm_context(summary: dict, plan: dict, records: list[dict]) -> dict:
    return {
        "age_group": summary["age_group"],
        "practice_level": summary["level"]["label"],
        "word_level": summary["word_level"]["progress_text"],
        "level_progress": summary["level"]["progress_text"],
        "exercises_completed": summary["total_sessions"],
        "average_score": summary["average_score"],
        "trend": summary["trend"],
        "streak_days": summary["streak_days"],
        "recent": [
            {"exercise": r["title"], "score": r["score"], "felt": r["self_rating"],
             "long_pauses": r.get("long_pauses"), "wpm": r.get("measured_wpm")}
            for r in records[-5:]
        ],
        "goals": [{"goal": g["text"], "current": g["current"], "met": g["met"]} for g in summary["goals"]],
        "plan": [{"exercise": e["title"], "why": e["reason"]} for e in plan["exercises"]],
    }


def answer(user_id: str, name: str, message: str, records: list[dict]) -> dict:
    text = message.strip()
    if not text:
        return {"reply": "Ask me anything about your practice — for example, “How am I doing?”",
                "action": None, "suggestions": DEFAULT_SUGGESTIONS,
                "intent": None, "confidence": 0.0, "source": "fallback"}

    intent, confidence = classifier.predict(text)
    settings, summary, plan = _context(user_id, records)

    if confidence >= CONFIDENCE_THRESHOLD:
        reply, action = _handle(intent, name, records, summary, plan)
        if reply:
            return {"reply": reply, "action": action, "suggestions": DEFAULT_SUGGESTIONS,
                    "intent": intent, "confidence": round(confidence, 2), "source": "classifier"}

    llm_reply = llm.ask(text, _first_name(name), _llm_context(summary, plan, records), summary["age_group"])
    if llm_reply:
        return {"reply": llm_reply, "action": None, "suggestions": DEFAULT_SUGGESTIONS,
                "intent": intent, "confidence": round(confidence, 2), "source": "llm"}
    return {"reply": FALLBACK, "action": None, "suggestions": DEFAULT_SUGGESTIONS,
            "intent": intent, "confidence": round(confidence, 2), "source": "fallback"}
