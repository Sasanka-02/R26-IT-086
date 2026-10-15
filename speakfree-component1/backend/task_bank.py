"""
Dynamic Task Engine – age-appropriate prompts for the clinical tasks:
  Picture Description · Scenario Description · Pre-defined Questions
  (+ Audio Recording / reading aloud, still supported by the API)

The reading passages are original texts written for SpeakFree. Word counts follow the
proposal (e.g. Bracket 3 = 40–50 words). `keywords` on picture tasks are used to
compute content coverage (how many expected elements the speaker mentioned).

A picture "visual" is either:
  {"kind": "emoji", "emojis": [...], "caption": "..."}     -> rendered as an illustrated scene
  {"kind": "chart", "title": ..., "unit": ..., "data": [...]} -> rendered as a bar chart
Real images: put <task_id>.png/.jpg/.webp in backend/static/tasks/ and re-run `python seed.py`
(or upload one in the clinician Task Library).

This module is SEED DATA ONLY. seed.py copies it into the assessment_tasks table; the API
reads tasks from the database (task_service.py) and never imports this file at runtime.
"""

TASK_BANK: dict[int, dict] = {
    # ------------------------------------------------------------------ Bracket 1 (6–8)
    1: {
        "reading": {
            "id": "b1-read-1",
            "title": "Short Phonetic Sentences",
            "instructions": "Read each short sentence out loud, slowly and clearly.",
            "text": "The cat sat down. I see a red kite. Sam can run fast. Pat the big dog. The sun is hot.",
            "max_seconds": 45,
        },
        "picture": {
            "id": "b1-pic-1",
            "title": "Flying a Kite",
            "instructions": "Look at the picture. Tell me what is happening.",
            "visual": {"kind": "emoji", "emojis": ["☀️", "🪁", "👧", "🌳", "🌼"], "caption": "A girl flying a kite in the park"},
            "image_url": None,
            "keywords": ["girl", "kite", "fly", "sky", "tree", "sun", "park", "wind"],
            "max_seconds": 60,
        },
        "scenario": {
            "id": "b1-scn-1",
            "title": "Recess Time",
            "instructions": "Listen to the question and answer in your own words.",
            "prompt": "It is recess time at school! Would you like to play on the swings or play a ball game with your friends? Tell me what you would choose and why.",
            "max_seconds": 60,
        },
    },
    # ------------------------------------------------------------------ Bracket 2 (8–10)
    2: {
        "reading": {
            "id": "b2-read-1",
            "title": "Consonant Blend Sentences",
            "instructions": "Read the sentences aloud. Take your time with the blended sounds (bl, fr, str, sl).",
            "text": (
                "The black frog sprang from the stream, and it splashed onto the green grass. "
                "Fred grabbed his blue sled, but the snow was too slushy to slide. "
                "Brenda planted three bright flowers, so the spring garden looked fresh."
            ),
            "max_seconds": 60,
        },
        "picture": {
            "id": "b2-pic-1",
            "title": "At the Playground",
            "instructions": "Describe everything you can see. Who is there and what are they doing?",
            "visual": {"kind": "emoji", "emojis": ["🛝", "⚽", "👦", "👧", "🐕", "🌳", "🏃"], "caption": "Children playing at a busy playground"},
            "image_url": None,
            "keywords": ["slide", "ball", "boy", "girl", "dog", "tree", "run", "play", "kick", "swing"],
            "max_seconds": 75,
        },
        "scenario": {
            "id": "b2-scn-1",
            "title": "The Lost Pencil",
            "instructions": "Explain what you would do, step by step.",
            "prompt": "You are about to start a test in class and you cannot find your pencil anywhere. What would you do? Explain the steps you would take.",
            "max_seconds": 75,
        },
    },
    # ------------------------------------------------------------------ Bracket 3 (10–12)
    3: {
        "reading": {
            "id": "b3-read-1",
            "title": "Saturday in the Garden",
            "instructions": "Read the paragraph aloud at your normal speaking speed.",
            "text": (
                "Every Saturday, Nimal helps his grandmother in her small vegetable garden. "
                "They water the beans, pull out the weeds, and pick the ripe red tomatoes. "
                "When the sun gets too hot, they rest under the old mango tree and share "
                "a cold glass of fresh lime juice."
            ),
            "max_seconds": 75,
        },
        "picture": {
            "id": "b3-pic-1",
            "title": "The Boiling Pot",
            "instructions": "Explain what is happening, why it is happening, and what might happen next.",
            "visual": {"kind": "emoji", "emojis": ["👨‍🍳", "🍲", "🔥", "💨", "👧", "🥕"], "caption": "A pot boiling over on the stove while dad is distracted"},
            "image_url": None,
            "keywords": ["pot", "boil", "fire", "stove", "steam", "hot", "cook", "spill", "careful", "because"],
            "max_seconds": 90,
        },
        "scenario": {
            "id": "b3-scn-1",
            "title": "Planning a Party",
            "instructions": "Talk through your plan in as much detail as you can.",
            "prompt": "Your best friend's birthday is next week and you want to plan a surprise party. How would you organise it? Who would you invite, and how would you keep it a secret?",
            "max_seconds": 90,
        },
    },
    # ------------------------------------------------------------------ Bracket 4 (12–14)
    4: {
        "reading": {
            "id": "b4-read-1",
            "title": "How Rain Is Made",
            "instructions": "Read this informational passage aloud clearly.",
            "text": (
                "Rain is an important part of the water cycle. When the sun heats rivers, lakes, "
                "and oceans, some of the water turns into an invisible gas called water vapour. "
                "This vapour rises into the sky, where the air is much cooler. As it cools, the "
                "vapour changes back into tiny droplets that gather together to form clouds. When "
                "the droplets become too heavy, they fall to the ground as rain, filling the "
                "rivers once again."
            ),
            "max_seconds": 90,
        },
        "picture": {
            "id": "b4-pic-1",
            "title": "The Street Market",
            "instructions": "Describe the setting. What are people buying and selling? What sounds and smells might be there?",
            "visual": {"kind": "emoji", "emojis": ["🧺", "🍌", "🥭", "🐟", "🛒", "🧑‍🌾", "👩", "🚲", "⛱️"], "caption": "A busy morning street market"},
            "image_url": None,
            "keywords": ["market", "fruit", "fish", "seller", "buy", "sell", "basket", "crowd", "bicycle", "umbrella"],
            "max_seconds": 90,
        },
        "scenario": {
            "id": "b4-scn-1",
            "title": "The Group Project Problem",
            "instructions": "Explain how you would handle the situation.",
            "prompt": "You are working on a group project and one member has not done their part. The deadline is in two days. What would you do, and how would you talk to them about it?",
            "max_seconds": 90,
        },
    },
    # ------------------------------------------------------------------ Bracket 5 (14–16)
    5: {
        "reading": {
            "id": "b5-read-1",
            "title": "The Lighthouse Keeper (Clinical Passage)",
            "instructions": "Read aloud at a comfortable pace. This passage contains most English speech sounds.",
            "text": (
                "On the rocky shore stands an old white lighthouse. For thirty years, a quiet keeper "
                "named Joseph climbed its winding stairs each evening to check the great lamp. "
                "He watched fishing boats rush back through the thick grey fog, and he measured "
                "the changing wind with simple tools. Visitors often asked whether he felt lonely. "
                "He would smile and say that the sea was never silent, the gulls were cheerful "
                "company, and every ship that reached the harbour safely was a friend he had "
                "helped. Even now, the beam still sweeps across the dark water every night."
            ),
            "max_seconds": 105,
        },
        "picture": {
            "id": "b5-pic-1",
            "title": "School Sports Day",
            "instructions": "Describe the scene, the people, how they might be feeling, and what is going on between them.",
            "visual": {"kind": "emoji", "emojis": ["🏟️", "🏃‍♀️", "🏃", "🥇", "📣", "👨‍👩‍👧", "🧃", "😢", "🎉"], "caption": "Sports day: a race finish, cheering families, and one disappointed runner"},
            "image_url": None,
            "keywords": ["race", "win", "medal", "cheer", "parents", "teacher", "sad", "happy", "team", "finish"],
            "max_seconds": 105,
        },
        "scenario": {
            "id": "b5-scn-1",
            "title": "Social Media Impact",
            "instructions": "Give your opinion and support it with reasons and examples.",
            "prompt": "Some people say social media brings teenagers closer together, while others say it makes them feel more alone. What do you think? Give reasons and examples.",
            "max_seconds": 120,
        },
    },
    # ------------------------------------------------------------------ Bracket 6 (16–18)
    6: {
        "reading": {
            "id": "b6-read-1",
            "title": "Coral Reefs Under Pressure",
            "instructions": "Read this academic passage aloud with natural phrasing.",
            "text": (
                "Coral reefs cover less than one percent of the ocean floor, yet they support "
                "roughly a quarter of all known marine species. Each reef is built by colonies of "
                "tiny animals called polyps, which form a partnership with microscopic algae. "
                "The algae provide energy through photosynthesis, while the coral offers shelter. "
                "However, when ocean temperatures rise even slightly, this relationship breaks "
                "down. The coral expels the algae, loses its colour, and becomes vulnerable to "
                "disease. Scientists describe this process as bleaching. Protecting reefs therefore "
                "requires both local action, such as reducing pollution, and global commitments "
                "to limit the emissions that warm our seas."
            ),
            "max_seconds": 120,
        },
        "picture": {
            "id": "b6-pic-1",
            "title": "Two Rivers",
            "instructions": "Compare the two sides of the picture. Discuss causes, consequences and possible solutions.",
            "visual": {"kind": "emoji", "emojis": ["🏭", "🛢️", "🗑️", "🐟", "↔️", "🌱", "🌊", "🐠", "🚣"], "caption": "A polluted industrial river compared with a clean, protected river"},
            "image_url": None,
            "keywords": ["pollution", "factory", "waste", "fish", "clean", "river", "environment", "protect", "plants", "community"],
            "max_seconds": 120,
        },
        "scenario": {
            "id": "b6-scn-1",
            "title": "Persuasive Speech – School Policy",
            "instructions": "Speak as if you are addressing the school board. Try to persuade them.",
            "prompt": "Your school is considering banning mobile phones for the entire school day. Prepare a short persuasive speech either supporting or opposing this policy.",
            "max_seconds": 120,
        },
    },
    # ------------------------------------------------------------------ Bracket 7 (18–20)
    7: {
        "reading": {
            "id": "b7-read-1",
            "title": "The Harbour Address (Tonal Modulation)",
            "instructions": "Read with expression: vary your tone for questions, quotations and emphasis.",
            "text": (
                "Friends, colleagues, and honoured guests: we gather tonight not to celebrate a "
                "single victory, but to remember a long and patient journey. When this harbour "
                "was first proposed, many asked, \"Who would ever sail here?\" The water was "
                "shallow, the roads were poor, and the budget was painfully small. And yet, "
                "season after season, ordinary people chose to believe. Fishermen repaired their "
                "boats, engineers redrew their plans, and families opened small shops along the "
                "shore. Today, ships arrive from distant ports every morning! So let us ask "
                "ourselves a different question: what might we build next, if we trust one "
                "another as completely as we did then? The answer, I suspect, depends not on "
                "fortune, but on the quiet courage we carry home tonight."
            ),
            "max_seconds": 150,
        },
        "picture": {
            "id": "b7-pic-1",
            "title": "Interpreting Data – Screen Time vs Sleep",
            "instructions": "Analyse the chart. Describe the trend, suggest an explanation, and note any limitations of the data.",
            "visual": {
                "kind": "chart",
                "title": "Average nightly sleep by daily screen time (survey of 400 students)",
                "unit": "hours of sleep",
                "data": [
                    {"label": "< 1 h", "value": 8.1},
                    {"label": "1–2 h", "value": 7.6},
                    {"label": "2–4 h", "value": 7.0},
                    {"label": "4–6 h", "value": 6.4},
                    {"label": "> 6 h", "value": 5.8},
                ],
            },
            "image_url": None,
            "keywords": ["sleep", "screen", "time", "decrease", "trend", "correlation", "hours", "students", "cause", "survey"],
            "max_seconds": 150,
        },
        "scenario": {
            "id": "b7-scn-1",
            "title": "Workplace Conflict",
            "instructions": "Respond as you would in a real professional setting.",
            "prompt": "You are a team lead. Two colleagues disagree strongly about how to finish a project, and the conflict is delaying the work. Explain how you would hold a meeting to resolve the conflict professionally.",
            "max_seconds": 150,
        },
    },
}


# ---------------------------------------------------------------------------------------------
# Scenario illustrations (rendered like picture visuals so every task card has an image)
SCENARIO_VISUALS: dict[int, dict] = {
    1: {"kind": "emoji", "emojis": ["🏫", "🛝", "⚽", "👧", "👦"], "caption": "Recess time in the school playground"},
    2: {"kind": "emoji", "emojis": ["📝", "✏️", "❓", "🎒", "👩‍🏫"], "caption": "A test is about to start – where is the pencil?"},
    3: {"kind": "emoji", "emojis": ["🎂", "🎈", "🎁", "🤫", "👫"], "caption": "Planning a surprise birthday party"},
    4: {"kind": "emoji", "emojis": ["📚", "💻", "⏰", "😟", "👥"], "caption": "A group project with a deadline in two days"},
    5: {"kind": "emoji", "emojis": ["📱", "💬", "❤️", "😔", "👥"], "caption": "Social media: closer together or more alone?"},
    6: {"kind": "emoji", "emojis": ["🏫", "📱", "🚫", "🎤", "👩‍⚖️"], "caption": "Speaking to the school board about a phone ban"},
    7: {"kind": "emoji", "emojis": ["💼", "🗣️", "⚡", "🤝", "📊"], "caption": "Resolving a conflict between two colleagues"},
}

# Pre-defined questions: one short spontaneous-speech answer is recorded per question.
QUESTION_BANK: dict[int, list[tuple[str, int]]] = {
    1: [
        ("What is your name, and how old are you?", 30),
        ("What is your favourite animal? Why do you like it?", 40),
        ("What did you eat for breakfast today?", 40),
    ],
    2: [
        ("Tell me about your best friend. What do you like to do together?", 45),
        ("What is your favourite subject at school, and why?", 45),
        ("Describe what you did last weekend.", 45),
    ],
    3: [
        ("What is your favourite book, film or TV show? Tell me what happens in it.", 60),
        ("If you could visit any place in the world, where would you go and why?", 60),
        ("Explain how to make your favourite snack, step by step.", 60),
    ],
    4: [
        ("Describe a hobby you enjoy and how you got started.", 60),
        ("What is one rule at school you would change, and why?", 60),
        ("Tell me about a time you helped someone.", 60),
    ],
    5: [
        ("What career are you interested in, and what attracts you to it?", 75),
        ("Describe a challenge you faced and how you overcame it.", 75),
        ("What makes a good friend? Give an example.", 75),
    ],
    6: [
        ("Describe a news story or social issue you care about and explain why.", 90),
        ("What are the advantages and disadvantages of online learning?", 90),
        ("Where do you see yourself in five years, and how will you get there?", 90),
    ],
    7: [
        ("Introduce yourself as you would at a job interview.", 90),
        ("Describe a project you are proud of and the role you played in it.", 90),
        ("Explain a complex topic you know well as if you were teaching a beginner.", 90),
    ],
}

for _bracket, _tasks in TASK_BANK.items():
    _tasks["scenario"]["visual"] = SCENARIO_VISUALS[_bracket]
    _tasks["questions"] = {
        "id": f"b{_bracket}-qs",
        "title": "Pre-defined Questions",
        "instructions": "Read each question, then press record and answer it in your own words. Speak naturally – there are no wrong answers.",
        "items": [
            {"id": f"b{_bracket}-q-{i}", "prompt": prompt, "max_seconds": seconds}
            for i, (prompt, seconds) in enumerate(QUESTION_BANK[_bracket], start=1)
        ],
    }


# ---------------------------------------------------------------------------------------------
# Extra rotation content: +2 picture, +2 scenario and +2 question tasks per bracket, so a patient
# who repeats the screening gets tasks they have not attempted yet. Same bracket rules as above.
def _pic(tid, title, instructions, emojis, caption, keywords, seconds):
    return {"id": tid, "title": title, "instructions": instructions,
            "visual": {"kind": "emoji", "emojis": emojis, "caption": caption},
            "image_url": None, "keywords": keywords, "max_seconds": seconds}


def _scn(tid, title, instructions, prompt, emojis, caption, seconds):
    return {"id": tid, "title": title, "instructions": instructions, "prompt": prompt,
            "visual": {"kind": "emoji", "emojis": emojis, "caption": caption}, "max_seconds": seconds}


EXTRA_TASKS: dict[int, dict[str, list]] = {
    # ------------------------------------------------------------------ Bracket 1 (6–8): single actions, daily choices
    1: {
        "picture": [
            _pic("b1-pic-2", "Bath Time for the Dog", "Look at the picture. Tell me what is happening.",
                 ["🐕", "🛁", "🫧", "🧒", "🧽"], "A boy giving his dog a bubbly bath",
                 ["dog", "bath", "wash", "bubble", "boy", "water", "soap", "wet"], 60),
            _pic("b1-pic-3", "At the Beach", "Look at the picture. Tell me what you can see.",
                 ["🏖️", "🏰", "👧", "🪣", "🌊", "🦀"], "A girl building a sandcastle at the beach",
                 ["beach", "sand", "castle", "girl", "bucket", "sea", "crab", "build"], 60),
        ],
        "scenario": [
            _scn("b1-scn-2", "Snack Time", "Listen to the question and answer in your own words.",
                 "It is snack time! Would you like an apple or a banana? Tell me which one you would pick and why.",
                 ["🍎", "🍌", "🧒", "🍽️"], "Choosing a snack", 60),
            _scn("b1-scn-3", "Rainy Day", "Listen to the question and answer in your own words.",
                 "It is raining outside and you cannot go to the park. What game would you play inside instead? Tell me why.",
                 ["🌧️", "🏠", "🧩", "🧸"], "A rainy day at home", 60),
        ],
        "questions": [("What is your favourite colour, and what things are that colour?", 30),
                      ("Who do you live with at home?", 30)],
    },
    # ------------------------------------------------------------------ Bracket 2 (8–10): multi-subject scenes
    2: {
        "picture": [
            _pic("b2-pic-2", "The Classroom", "Describe everything you can see. Who is there and what are they doing?",
                 ["👩‍🏫", "📚", "✏️", "👦", "👧", "🖍️", "🌍"], "A busy classroom during an art lesson",
                 ["teacher", "class", "book", "pencil", "draw", "children", "desk", "paint", "globe", "write"], 75),
            _pic("b2-pic-3", "Farm Morning", "Describe everything you can see. Who is there and what are they doing?",
                 ["🚜", "🐄", "🐔", "🧑‍🌾", "🌾", "🐖", "🌅"], "A farmer feeding animals in the morning",
                 ["farm", "tractor", "cow", "chicken", "farmer", "pig", "feed", "morning", "field", "egg"], 75),
        ],
        "scenario": [
            _scn("b2-scn-2", "The Spilled Paint", "Explain what you would do, step by step.",
                 "During art class your friend accidentally spills paint on your drawing. What would you say and what would you do next?",
                 ["🎨", "💦", "😮", "👫"], "Paint spilled on a drawing", 75),
            _scn("b2-scn-3", "The New Student", "Explain what you would do, step by step.",
                 "A new student joins your class and sits alone at lunch. What could you do to help them feel welcome?",
                 ["🎒", "🍱", "🙂", "👋"], "A new student at lunch time", 75),
        ],
        "questions": [("What is the best game you like to play with your friends? How do you play it?", 45),
                      ("Tell me about a pet or an animal you like.", 45)],
    },
    # ------------------------------------------------------------------ Bracket 3 (10–12): cause and effect, social reasoning
    3: {
        "picture": [
            _pic("b3-pic-2", "The Broken Window", "Explain what is happening, why it is happening, and what might happen next.",
                 ["⚾", "🪟", "💥", "😲", "🏠", "🧑"], "A ball has just broken a neighbour's window",
                 ["ball", "window", "break", "glass", "neighbour", "throw", "sorry", "because", "angry", "pay"], 90),
            _pic("b3-pic-3", "The Melting Ice Cream", "Explain what is happening, why it is happening, and what might happen next.",
                 ["🍦", "☀️", "💧", "😢", "🧒", "🐕"], "A child's ice cream melting in the hot sun",
                 ["ice", "cream", "melt", "sun", "hot", "drip", "dog", "sad", "because", "fast"], 90),
        ],
        "scenario": [
            _scn("b3-scn-2", "The Lost Wallet", "Talk through what you would do in as much detail as you can.",
                 "On your way home from school you find a wallet with money and a school ID card inside. What would you do, and why?",
                 ["👛", "💵", "🪪", "🤔"], "Finding a lost wallet", 90),
            _scn("b3-scn-3", "The School Trip", "Talk through your plan in as much detail as you can.",
                 "Your class can choose between a trip to the zoo or a trip to a science museum. Which would you vote for? Convince your classmates.",
                 ["🦁", "🔬", "🚌", "🗳️"], "Voting for a school trip", 90),
        ],
        "questions": [("What would you do with a whole free day and no homework?", 60),
                      ("Describe your best friend without saying their name.", 60)],
    },
    # ------------------------------------------------------------------ Bracket 4 (12–14): environmental scenes, dilemmas
    4: {
        "picture": [
            _pic("b4-pic-2", "Beach Clean-up Day", "Describe the setting, what people are doing, and why it matters.",
                 ["🏖️", "🗑️", "🧤", "🥤", "🐢", "👫", "♻️"], "Volunteers cleaning plastic from a beach",
                 ["beach", "plastic", "rubbish", "clean", "volunteer", "turtle", "recycle", "gloves", "ocean", "pollution"], 90),
            _pic("b4-pic-3", "The Train Station", "Describe the setting. Who is there, where might they be going, and how do they feel?",
                 ["🚉", "🚆", "🧳", "⏰", "👨‍👩‍👧", "📢"], "A crowded train station at rush hour",
                 ["train", "station", "platform", "luggage", "late", "crowd", "travel", "clock", "announcement", "family"], 90),
        ],
        "scenario": [
            _scn("b4-scn-2", "Screen Time Rules", "Explain how you would handle the situation.",
                 "Your parents want to limit your phone use to one hour a day. Do you think this is fair? How would you discuss it with them?",
                 ["📱", "⏳", "👪", "💬"], "Talking about screen-time rules", 90),
            _scn("b4-scn-3", "The Shortcut", "Explain how you would handle the situation.",
                 "Your friends want to take a shortcut home through a building site that has a 'No Entry' sign. What would you do and say?",
                 ["🚧", "⚠️", "👥", "🤔"], "A risky shortcut home", 90),
        ],
        "questions": [("If you could invent something to help people, what would it be?", 60),
                      ("What is a skill you would like to learn, and why?", 60)],
    },
    # ------------------------------------------------------------------ Bracket 5 (14–16): complex social scenes, critical thinking
    5: {
        "picture": [
            _pic("b5-pic-2", "The Science Fair", "Describe the scene, the people, how they might be feeling, and what is going on between them.",
                 ["🔬", "🏆", "🧪", "😟", "😀", "👩‍🔬", "📋"], "Students presenting projects while judges take notes",
                 ["science", "project", "judge", "nervous", "present", "prize", "experiment", "proud", "poster", "competition"], 105),
            _pic("b5-pic-3", "The Hospital Waiting Room", "Describe the scene, the people, and how they might be feeling.",
                 ["🏥", "🪑", "🤕", "👵", "👩‍⚕️", "⏰", "📱"], "Patients and families waiting to see a doctor",
                 ["hospital", "wait", "doctor", "nurse", "worried", "patient", "family", "injury", "time", "calm"], 105),
        ],
        "scenario": [
            _scn("b5-scn-2", "Group Chat Conflict", "Give your opinion and support it with reasons and examples.",
                 "Someone in your class group chat is posting jokes that are hurting another student. What would you do, and what could the class do?",
                 ["💬", "😞", "🛑", "🤝"], "Unkind messages in a group chat", 120),
            _scn("b5-scn-3", "School Uniforms", "Give your opinion and support it with reasons and examples.",
                 "Some people believe school uniforms make students equal, while others say they limit self-expression. What do you think, and why?",
                 ["👔", "👕", "⚖️", "🏫"], "The school-uniform debate", 120),
        ],
        "questions": [("Tell me about a book, film or game that changed the way you think.", 75),
                      ("If you could change one thing about your town, what would it be?", 75)],
    },
    # ------------------------------------------------------------------ Bracket 6 (16–18): societal themes, persuasion
    6: {
        "picture": [
            _pic("b6-pic-2", "City Traffic", "Discuss the causes, consequences and possible solutions shown in the picture.",
                 ["🚗", "🚕", "🚌", "🌫️", "🚲", "🚇", "🏙️"], "A congested, smoggy city street next to a quiet bike lane",
                 ["traffic", "pollution", "car", "bus", "bicycle", "transport", "congestion", "emissions", "city", "solution"], 120),
            _pic("b6-pic-3", "The Job Fair", "Describe the scene and discuss what it shows about young people and work.",
                 ["💼", "🧑‍🎓", "🤝", "📄", "🏢", "💻"], "Students meeting employers at a career fair",
                 ["career", "job", "employer", "interview", "skills", "graduate", "experience", "future", "resume", "network"], 120),
        ],
        "scenario": [
            _scn("b6-scn-2", "Persuasive Speech – Four-Day School Week", "Speak as if you are addressing the school board. Try to persuade them.",
                 "Your school is considering moving to a four-day school week with longer days. Prepare a short persuasive speech for or against it.",
                 ["📅", "🏫", "🎤", "⚖️"], "Debating a four-day school week", 120),
            _scn("b6-scn-3", "Volunteering Requirement", "Present a balanced argument and give your conclusion.",
                 "Should every student have to complete 40 hours of community volunteering before finishing school? Argue your position.",
                 ["🤝", "🌱", "⏱️", "🎓"], "Compulsory volunteering", 120),
        ],
        "questions": [("Describe a time you had to make a difficult decision. What did you choose?", 90),
                      ("What does success mean to you?", 90)],
    },
    # ------------------------------------------------------------------ Bracket 7 (18–20): professional, data analysis, workplace
    7: {
        "picture": [
            {
                "id": "b7-pic-2",
                "title": "Interpreting Data – Commute Mode by Age",
                "instructions": "Analyse the chart. Describe the trend, suggest an explanation, and note any limitations.",
                "visual": {
                    "kind": "chart",
                    "title": "Share commuting by public transport, by age group (survey of 1,200 adults)",
                    "unit": "% using public transport",
                    "data": [
                        {"label": "18–24", "value": 62},
                        {"label": "25–34", "value": 48},
                        {"label": "35–49", "value": 35},
                        {"label": "50–64", "value": 29},
                        {"label": "65+", "value": 33},
                    ],
                },
                "image_url": None,
                "keywords": ["public", "transport", "age", "decrease", "young", "trend", "car", "survey", "percentage", "older"],
                "max_seconds": 150,
            },
            _pic("b7-pic-3", "The Open-Plan Office", "Describe the workplace and evaluate its advantages and disadvantages for employees.",
                 ["🏢", "💻", "🎧", "☕", "🗣️", "📈"], "A busy open-plan office during a deadline",
                 ["office", "open", "noise", "collaboration", "focus", "deadline", "team", "privacy", "productivity", "headphones"], 150),
        ],
        "scenario": [
            _scn("b7-scn-2", "Giving Difficult Feedback", "Respond as you would in a real professional setting.",
                 "You manage a friendly, hard-working team member whose recent reports contain serious errors. How would you give them feedback?",
                 ["📝", "🗣️", "🤝", "📉"], "A difficult feedback conversation", 150),
            _scn("b7-scn-3", "The Customer Complaint", "Respond as you would in a real professional setting.",
                 "An angry customer calls because their order arrived late and damaged. Explain how you would handle the call from start to finish.",
                 ["📞", "📦", "😠", "✅"], "Handling a customer complaint", 150),
        ],
        "questions": [("Describe your ideal job and the skills it would need.", 90),
                      ("Tell me about a time you worked in a team. What was your role?", 90)],
    },
}

QUESTIONS_INSTRUCTIONS = TASK_BANK[1]["questions"]["instructions"]


def seed_rows() -> list[dict]:
    """
    Flatten TASK_BANK + EXTRA_TASKS into rows for the assessment_tasks table (used by seed.py).
    task_bank.py is seed data only – the API reads tasks from the database.
    """
    rows: list[dict] = []

    def add(bracket: int, task_type: str, t: dict, content: str, keywords=None, visual=None):
        rows.append({
            "id": t["id"], "age_bracket": bracket, "task_type": task_type, "title": t["title"],
            "instructions": t["instructions"], "content_text": content, "keywords": list(keywords or []),
            "visual_json": visual, "max_seconds": int(t["max_seconds"]),
        })

    for bracket, tasks in TASK_BANK.items():
        extra = EXTRA_TASKS[bracket]
        add(bracket, "reading", tasks["reading"], tasks["reading"]["text"])
        for p in [tasks["picture"], *extra["picture"]]:
            add(bracket, "picture", p, p["visual"].get("caption") or p["visual"].get("title", ""), p["keywords"], p["visual"])
        for s in [tasks["scenario"], *extra["scenario"]]:
            add(bracket, "scenario", s, s["prompt"], visual=s["visual"])
        questions = [*tasks["questions"]["items"]]
        start = len(questions) + 1
        questions += [{"id": f"b{bracket}-q-{i}", "prompt": p, "max_seconds": sec}
                      for i, (p, sec) in enumerate(extra["questions"], start=start)]
        for q in questions:
            n = q["id"].rsplit("-", 1)[1]
            add(bracket, "questions",
                {"id": q["id"], "title": f"Question {n}", "instructions": QUESTIONS_INSTRUCTIONS, "max_seconds": q["max_seconds"]},
                q["prompt"])
    return rows
