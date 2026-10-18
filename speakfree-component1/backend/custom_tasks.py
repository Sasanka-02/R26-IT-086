"""
Custom screening content: the 2 pictures + 2 scenario videos per age bracket in static/tasks/.

Each entry replaces the starter text of that task id (task_bank.py) with text that matches the
uploaded picture / video, so the prompt fits what the child sees and the picture keywords
(content coverage) score what is really in the image. The third starter picture and scenario of
every bracket are switched off, so the screening picks one of the two custom ones per session
(task_service.py: least-attempted first, random among ties).

Seed data only:
  * new databases  – seed.py applies it while inserting the task library
  * existing ones  – run `python tools/apply_custom_tasks.py` once (clinician-edited tasks are skipped)
"""
from __future__ import annotations

WATCH_YOUNG = "Watch the video. Then tell me your answer in your own words. You can watch it again first."
WATCH = "Watch the video, then answer in your own words. You can watch it again before you record."

CUSTOM_TASKS: dict[str, dict] = {
    # ------------------------------------------------------------------ Bracket 1 (6–7)
    "b1-pic-1": {"title": "Flying Kites", "content_text": "Children flying colourful kites in a sunny field",
                 "keywords": ["kite", "children", "fly", "sky", "wind", "grass", "string", "happy", "red", "blue"]},
    "b1-pic-2": {"title": "Playing with Balls", "content_text": "Children laughing and throwing colourful balls",
                 "keywords": ["ball", "children", "throw", "catch", "play", "laugh", "green", "red", "yellow", "happy"]},
    "b1-scn-1": {"title": "Arriving at School", "instructions": WATCH_YOUNG,
                 "content_text": "Watch the children arrive at school. What do they do when they come in? "
                                 "What do you do when you get to school in the morning?"},
    "b1-scn-2": {"title": "Kind Friends and Lunchtime", "instructions": WATCH_YOUNG,
                 "content_text": "Watch the video. How did the children help their friend? "
                                 "What do you do before you eat your lunch?"},
    # ------------------------------------------------------------------ Bracket 2 (8–9)
    "b2-pic-1": {"title": "At the Playground",
                 "content_text": "A busy playground: children on the slide, see-saw and swings, running, and a dog",
                 "keywords": ["slide", "swing", "run", "dog", "children", "play", "sand", "fish", "seesaw", "park"]},
    "b2-pic-2": {"title": "In the Kitchen",
                 "content_text": "A busy family kitchen: dad washing dishes, mum at the fridge, children at the table and a cat eating",
                 "keywords": ["kitchen", "dad", "mum", "wash", "dishes", "fridge", "cat", "table", "fruit", "bread"]},
    "b2-scn-1": {"title": "Walking to the School Bus", "instructions": WATCH_YOUNG,
                 "content_text": "Watch the two children on their way to school. What do you think they are talking about? "
                                 "How do you get to school, and what do you see on the way?"},
    "b2-scn-2": {"title": "A Day in Class", "instructions": WATCH_YOUNG,
                 "content_text": "Watch the classroom. How do you think the children feel? "
                                 "What would you tell a new friend on their first day in your class?"},
    # ------------------------------------------------------------------ Bracket 3 (10–11)
    "b3-pic-1": {"title": "The Polluted Stream",
                 "content_text": "A sad water drop beside a stream full of rubbish, where the fish and the frog look unwell",
                 "keywords": ["water", "river", "rubbish", "plastic", "fish", "frog", "sad", "pollution", "because", "clean"]},
    "b3-pic-2": {"title": "Village Life",
                 "content_text": "A village morning: a woman carrying a water pot, a boy running, a family by a fire, cows and huts",
                 "keywords": ["village", "woman", "pot", "water", "carry", "boy", "fire", "cow", "house", "tree"]},
    "b3-scn-1": {"title": "My Morning Routine", "instructions": WATCH,
                 "content_text": "Watch the boy start his day. What does he do first? "
                                 "Tell me about your own morning routine, step by step, and why it is important."},
    "b3-scn-2": {"title": "The Race", "instructions": WATCH,
                 "content_text": "Watch the race. Why did Henry fall and get tired so quickly? What advice was he given? "
                                 "What would you tell a friend before a race?"},
    # ------------------------------------------------------------------ Bracket 4 (12–13)
    "b4-pic-1": {"title": "The Street Market", "content_text": "A crowded street market with stalls of fruit and vegetables",
                 "keywords": ["market", "vegetables", "fruit", "seller", "buy", "sell", "crowd", "stall", "busy", "shopping"]},
    "b4-pic-2": {"title": "Beach Clean-up Day", "content_text": "Volunteers collecting rubbish from a beach into large bags",
                 "keywords": ["beach", "rubbish", "plastic", "clean", "volunteer", "bag", "gloves", "sea", "pollution", "collect"]},
    "b4-scn-1": {"title": "Looking at the Stars", "instructions": WATCH,
                 "content_text": "Watch the two friends looking at the night sky. What do they wonder about? "
                                 "If you could travel to the stars, what would you want to find out, and why?"},
    "b4-scn-2": {"title": "The Big Adventure", "instructions": WATCH,
                 "content_text": "Watch the friends and the fox run off together. Where do you think they are going? "
                                 "Make up the rest of their adventure - what happens next?"},
    # ------------------------------------------------------------------ Bracket 5 (14–15)
    "b5-pic-1": {"title": "The School Canteen",
                 "content_text": "A school canteen counter with healthy food, fruit and signs such as 'Eat well, learn more'",
                 "keywords": ["canteen", "food", "healthy", "fruit", "vegetables", "apple", "orange", "banana", "tray", "lunch"]},
    "b5-pic-2": {"title": "The Finish Line",
                 "content_text": "A runner crossing the finish line of a race while officials time and watch",
                 "keywords": ["race", "finish", "runner", "win", "time", "cheer", "crowd", "flags", "clock", "athlete"]},
    "b5-scn-1": {"title": "Screen Time or Nature?", "instructions": WATCH,
                 "content_text": "The video starts with a phone showing many hours of screen time, then shows beautiful places in "
                                 "nature. What is its message? Should young people spend less time on screens? Give your reasons."},
    "b5-scn-2": {"title": "The Urgent Phone Call", "instructions": WATCH,
                 "content_text": "A caller says they have lost their money and phone and urgently need money sent to a number. "
                                 "What should the girl do? How can you tell if a call like this might be a scam?"},
    # ------------------------------------------------------------------ Bracket 6 (16–17)
    "b6-pic-1": {"title": "A Day by the Lake",
                 "content_text": "Families camping, fishing and kayaking at a mountain lake",
                 "keywords": ["lake", "mountain", "camping", "tent", "fishing", "kayak", "family", "nature", "forest", "environment"]},
    "b6-pic-2": {"title": "Living on a Rubbish Dump",
                 "content_text": "Children among the waste at a large rubbish dump",
                 "keywords": ["rubbish", "waste", "children", "poverty", "pollution", "dump", "plastic", "health", "smoke", "society"]},
    "b6-scn-1": {"title": "When an Argument Turns into a Fight", "instructions": WATCH,
                 "content_text": "Two young men argue and then start fighting. What could have caused it? If you saw two friends "
                                 "fighting, what would you do? How can conflicts be solved without violence?"},
    "b6-scn-2": {"title": "Long Days of Study", "instructions": WATCH,
                 "content_text": "Students walk to an evening class after a long day. Is it a good idea to have classes late into "
                                 "the evening? Give a short persuasive argument for or against."},
    # ------------------------------------------------------------------ Bracket 7 (18–20; also adults 21+)
    "b7-pic-1": {"title": "Interpreting Data - Salary vs Profit",
                 "instructions": "Analyse the charts. Compare the two, describe the trends and explain what they suggest.",
                 "content_text": "Two bar charts: a worker's salary stays at $100 every month, while the owner's profit "
                                 "grows from $0 to $10,000 by December",
                 "keywords": ["salary", "profit", "month", "increase", "same", "chart", "owner", "worker", "unfair", "december"]},
    "b7-pic-2": {"title": "Explaining a Diagram - Computer Network",
                 "instructions": "Explain the diagram. Describe how the parts connect and what each one does.",
                 "content_text": "A computer network: internet, firewall, routers, switch, hub, server, wireless access point and devices",
                 "keywords": ["internet", "firewall", "router", "switch", "server", "network", "wireless", "laptop", "connect", "data"]},
    "b7-scn-1": {"title": "Living in the Digital Age", "instructions": WATCH,
                 "content_text": "The video describes how technology and social media connect people around the world. Do you "
                                 "agree that social media is a 'virtual playground'? Discuss the benefits and the risks."},
    "b7-scn-2": {"title": "Conflict at Work", "instructions": WATCH,
                 "content_text": "Watch what happens between the customer and the cook at this busy restaurant. What do you think "
                                 "went wrong? How should staff deal with an unhappy customer?"},
}

# The third starter picture and scenario of every screening bracket (replaced by the custom pair).
DISABLED_TASKS: set[str] = {f"b{b}-{kind}-3" for b in range(1, 8) for kind in ("pic", "scn")}


def apply_custom(row: dict) -> dict:
    """A seed row with the custom text applied and its active flag set (used for new databases)."""
    out = {**row, **CUSTOM_TASKS.get(row["id"], {})}
    out["is_active"] = row["id"] not in DISABLED_TASKS
    return out
