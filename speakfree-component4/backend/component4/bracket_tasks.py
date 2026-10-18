"""
The 24 age-bracket exercises: 8 clinical brackets x 3 task types.

    reading        a passage at the bracket's target speed (exact word-count range per bracket)
    picture        describe an original SVG scene (public/stimuli/images) with 3-4 guiding questions
    conversation   spontaneous speech: a situation + 3-4 prompt questions, answered aloud
                   (same recording flow as picture description - there is no fixed text)

All passages and pictures are original and use everyday Sri Lankan contexts where natural.
READING_WORD_RANGES is checked by the tests, so the counts below are exact.
"""
from __future__ import annotations

from .brackets import BRACKETS

TASK_TYPES = ("reading", "picture", "conversation")
ALL_FOCI = ["fluency", "speech_sounds", "maintenance", "motor_speech"]
IMAGE_DIR = "/stimuli/images"

# Bracket -> (min, max) words in the reading passage. Bracket 1 counts words per sentence, bracket 2 counts sentences.
READING_WORD_RANGES = {3: (40, 50), 4: (60, 80), 5: (80, 100), 6: (100, 120), 7: (120, 150), 8: (150, 180)}
BRACKET1_WORDS_PER_SENTENCE = (3, 4)
BRACKET2_SENTENCES = (2, 3)
CONSONANT_BLENDS = ("bl", "br", "cl", "cr", "dr", "fl", "fr", "gl", "gr", "pl", "pr", "sl", "sm", "sn", "sp", "st", "sw", "tr")

_CONTENT: dict[int, dict] = {
    1: {
        "reading": {
            "title": "Mum Has a Map",
            "description": "Very short sentences with easy sounds. Point to each word and say it slowly.",
            "passage": "Mum has a map. The dog can run. Dad got a hat. Sam can hop. Pat the cat. The sun is hot. Ben has a bus.",
        },
        "picture": {
            "title": "Flying a Kite",
            "description": "Look at the picture. Tell me what the girl is doing.",
            "image": "b1-kite.svg",
            "prompts": ["What is the girl doing?", "What colour is the kite?", "Where is she?", "Is it windy or calm?"],
        },
        "conversation": {
            "title": "Recess Game Choice",
            "description": "Think about it, then answer out loud in your own words.",
            "situation": "It is recess time at school! You can play hopscotch, catch or skipping rope with your friends.",
            "prompts": ["Which game will you choose?", "Why do you like that game?", "Who will you play with?",
                        "What will you do if it starts to rain?"],
        },
    },
    2: {
        "reading": {
            "title": "Fred and the Blue Kite",
            "description": "Long sentences joined with 'and', 'but' and 'yet'. Listen for the blends: br, gr, bl, st, sw, sl, fr, sp, tr.",
            "passage": ("Brave Fred grabbed his blue kite, and he ran fast across the green grass. The strong breeze "
                        "swept it up, but the string slipped from his hand. Fred frowned at first, yet he soon spotted "
                        "it stuck in a tree near the stream."),
        },
        "picture": {
            "title": "The Busy Playground",
            "description": "Many children are doing different things. Tell me about as many of them as you can.",
            "image": "b2-playground.svg",
            "prompts": ["How many children can you see?", "What is each child doing?",
                        "Which game would you like to join?", "What is the teacher doing?"],
        },
        "conversation": {
            "title": "The Lost Pencil",
            "description": "Solve the problem out loud. There are no wrong answers.",
            "situation": "Your spelling test starts in five minutes, but you cannot find your pencil anywhere in your bag.",
            "prompts": ["How do you feel?", "Where will you look first?", "Who could you ask for help?",
                        "What can you do so it doesn't happen again?"],
        },
    },
    3: {
        "reading": {
            "title": "The Vesak Lantern",
            "description": "A short paragraph. Use the commas as small breathing points.",
            "passage": ("Every Vesak, Nimal and his grandfather build a lantern together. They cut thin bamboo sticks, "
                        "tie them into a star, and cover the frame with bright coloured paper. When the sun sets, they "
                        "hang it near the gate. The candle glows softly, and the whole street shines."),
        },
        "picture": {
            "title": "The Boiling Pot",
            "description": "Something is about to happen in this kitchen. Explain what is happening and why.",
            "image": "b3-boiling-pot.svg",
            "prompts": ["What is happening to the pot?", "Why is the water bubbling over?",
                        "What could happen next?", "What should the boy do to stay safe?"],
        },
        "conversation": {
            "title": "Planning a Class Party",
            "description": "Talk through your plan as if you were explaining it to your class.",
            "situation": "Your best friend is moving to another school next week. Your class wants to plan a surprise farewell party.",
            "prompts": ["What food and games would you choose?", "How will you keep it a surprise?",
                        "How can you make sure everyone feels included?", "What would you say to your friend?"],
        },
    },
    4: {
        "reading": {
            "title": "How Tea Reaches Your Cup",
            "description": "An information passage. Pause briefly at each full stop and keep a steady pace.",
            "passage": ("Sri Lanka is one of the largest tea exporters in the world. Tea grows best on cool, misty "
                        "hills, where workers pick only the top two leaves and a bud. The fresh leaves are carried to "
                        "a nearby factory. There they are dried, rolled and left to change colour in warm air. "
                        "Finally, the leaves are sorted by size, packed and shipped to many countries, where people "
                        "enjoy a hot cup every morning."),
        },
        "picture": {
            "title": "At the Pola (Street Market)",
            "description": "Describe the market scene - the people, the stalls and what is going on around them.",
            "image": "b4-pola.svg",
            "prompts": ["What is being sold at the different stalls?", "What are the people doing?",
                        "What do you notice about the street and the tuk-tuk?", "How is this market different from a supermarket?"],
        },
        "conversation": {
            "title": "The Group Project Problem",
            "description": "Think about what you would do and explain your reasons.",
            "situation": ("Your group has a science project due on Friday. One member has not done any of their part "
                          "and does not reply to messages. If the project is incomplete, the whole group loses marks."),
            "prompts": ["What would you do first?", "How would you talk to the member who has not helped?",
                        "Should you tell the teacher? Why or why not?", "What would be the fairest solution?"],
        },
    },
    5: {
        "reading": {
            "title": "Uncle Chaminda the Fisherman",
            "description": "A clinical-style passage with a wide mix of speech sounds. Read it as you would tell a story.",
            "passage": ("My uncle Chaminda is a cheerful fisherman who lives in a small village near the southern "
                        "coast. Although he is nearly sixty, he still rises before dawn, checks his nets and pushes "
                        "his bright yellow boat into the waves. He says the sea teaches patience: some mornings bring "
                        "plenty of fish, while others bring nothing but wind and rain. In the evening, he sits on the "
                        "veranda with a cup of ginger tea, shares stories with the neighbours and laughs loudly at his "
                        "own jokes."),
        },
        "picture": {
            "title": "Sports Day",
            "description": "A lot is happening at the school sports day. Describe the scene and what people might be feeling.",
            "image": "b5-sports-day.svg",
            "prompts": ["What is happening in the race?", "Why has one runner stopped to help another?",
                        "How might the crowd, the winner and the fallen runner be feeling?", "What does this scene say about good sportsmanship?"],
        },
        "conversation": {
            "title": "Should You Share That Post?",
            "description": "Give your opinion and support it with reasons.",
            "situation": ("A post in your class group chat says that school will be closed tomorrow because of a storm. "
                          "It has no source, but hundreds of people have already shared it."),
            "prompts": ["Would you share it? Why or why not?", "How could you check whether it is true?",
                        "What harm can false posts cause?", "What advice would you give a younger student about social media?"],
        },
    },
    6: {
        "reading": {
            "title": "Cities and the Heat Island Effect",
            "description": "Academic prose. Group the words into meaningful phrases and pause between ideas.",
            "passage": ("Cities are often several degrees warmer than the surrounding countryside, a pattern scientists "
                        "call the urban heat island effect. Concrete, asphalt and glass absorb sunlight during the day "
                        "and release that heat slowly at night, while traffic and air conditioners add even more "
                        "warmth. In tropical cities such as Colombo, this extra heat can affect sleep, health and "
                        "energy use. Researchers suggest several practical responses: planting street trees, "
                        "protecting wetlands, using lighter roofing materials and designing buildings that allow air "
                        "to flow freely. These measures not only lower temperatures but also improve air quality, "
                        "reduce flooding and create shaded public spaces where communities can gather comfortably."),
        },
        "picture": {
            "title": "A Tale of Two Rivers",
            "description": "Compare the two rivers and explain what the picture says about people and the environment.",
            "image": "b6-two-rivers.svg",
            "prompts": ["How are the two rivers different?", "What has caused the difference?",
                        "Who is affected by the polluted river?", "What could the community do to protect it?"],
        },
        "conversation": {
            "title": "Persuade the Principal",
            "description": "Give a short persuasive speech. State your view, give reasons and finish strongly.",
            "situation": "Your school is considering a rule that bans mobile phones for the whole school day, including breaks.",
            "prompts": ["Do you support or oppose the rule?", "What are your two strongest reasons?",
                        "What would someone on the other side say, and how would you answer them?", "How would you conclude your speech?"],
        },
    },
    7: {
        "reading": {
            "title": "Welcome to Your Internship",
            "description": "A professional welcome speech. Change your tone where the text asks a question, gets excited or quotes someone.",
            "passage": ("Good morning, everyone, and welcome to your first day at Lanka Digital Solutions. Over the next "
                        "twelve weeks, you will work alongside experienced developers, designers and project managers "
                        "on real projects for real clients. You might be wondering, \"Will I really be trusted with "
                        "important work?\" The answer is yes! Each of you has been assigned a mentor who will meet you "
                        "every Monday to review your progress and answer your questions. Please remember three simple "
                        "rules: arrive on time, ask for help early and keep your work organised. Our director often "
                        "says, \"Mistakes are lessons, not failures.\" We truly believe that. By the end of this "
                        "programme, you will have a portfolio you can be proud of. Are you ready to begin? Wonderful! "
                        "Let's get started."),
            "tone_hints": [
                {"phrase": "Will I really be trusted with important work?", "tone": "questioning",
                 "hint": "Read this with a questioning tone - let your voice rise at the end."},
                {"phrase": "The answer is yes!", "tone": "excited", "hint": "Read this with an excited, confident tone."},
                {"phrase": "Mistakes are lessons, not failures.", "tone": "quoting",
                 "hint": "This is a quote - read it in a calm, slightly slower voice."},
                {"phrase": "Are you ready to begin?", "tone": "questioning", "hint": "Questioning tone - voice rises."},
                {"phrase": "Wonderful!", "tone": "excited", "hint": "Excited tone - bright and energetic."},
            ],
        },
        "picture": {
            "title": "Reading the Sales Chart",
            "description": "Interpret the chart: describe the trend, compare the months and explain what might cause the pattern.",
            "image": "b7-chart.svg",
            "prompts": ["What do the bars and the line show?", "Which month had the highest sales, and why might that be?",
                        "How are temperature and iced-drink sales related?", "What would you advise the café owner for next year?"],
        },
        "conversation": {
            "title": "Credit Where It's Due",
            "description": "Explain how you would handle this workplace situation professionally.",
            "situation": ("At your part-time job, a colleague presented your idea for a new delivery schedule to the "
                          "manager as if it were their own. The manager praised them in front of the team."),
            "prompts": ["How would you feel, and how would you stay calm?", "What would you say to your colleague?",
                        "Would you speak to the manager? How?", "How could you prevent this in future?"],
        },
    },
    8: {
        "reading": {
            "title": "Digital Bus Tickets Announced",
            "description": "A news report. Read it like a news presenter: clear, steady and confident.",
            "passage": ("COLOMBO - Passengers on several major bus routes will soon be able to pay their fares using a "
                        "mobile phone, the transport authority announced on Tuesday. The new digital ticketing system, "
                        "which will first be tested on routes between Colombo, Kandy and Galle, allows commuters to "
                        "scan a QR code when boarding and receive an electronic receipt instantly. Officials said the "
                        "change aims to reduce delays caused by cash handling, improve record keeping and give "
                        "operators more accurate information about passenger numbers. Cash payments will continue to "
                        "be accepted during the trial period, which is expected to last six months. Some passenger "
                        "groups welcomed the announcement but raised concerns about elderly travellers and people "
                        "without smartphones. In response, the authority confirmed that prepaid travel cards will also "
                        "be sold at main bus stands. A final decision on expanding the system nationwide will be made "
                        "after a public review early next year."),
        },
        "picture": {
            "title": "The Monday Team Meeting",
            "description": "Describe this office meeting in detail: who is there, what is happening and what the mood seems to be.",
            "image": "b8-office-meeting.svg",
            "prompts": ["What is the purpose of this meeting, judging by the screen?", "What is each person doing?",
                        "Is everyone engaged? What tells you that?", "If you were leading the meeting, what would you do next?"],
        },
        "conversation": {
            "title": "Job Interview and Booking a Call",
            "description": "Two everyday speaking situations. Answer each part as if it were real.",
            "situation": ("Part 1: You are at a job interview for a position you really want. "
                          "Part 2: Later, you phone a dental clinic to book an appointment for next week."),
            "prompts": ["Interview: Tell me a little about yourself.", "Interview: Why do you want this job, and what makes you a good fit?",
                        "Phone call: Greet the receptionist, give your name and explain why you are calling.",
                        "Phone call: Ask for a suitable day and time, then confirm the details politely."],
        },
    },
}


def _difficulty(bracket: int) -> int:
    """1-3 scale shared with the other exercises (bandit difficulty fit)."""
    return 1 if bracket <= 3 else 2 if bracket <= 6 else 3


def _build() -> list[dict]:
    out: list[dict] = []
    for bracket, tasks in _CONTENT.items():
        ages = BRACKETS[bracket]["label"]
        for task_type in TASK_TYPES:
            c = tasks[task_type]
            ex = {
                "id": f"b{bracket}-{task_type}", "type": task_type, "task_type": task_type, "bracket": bracket,
                "difficulty": _difficulty(bracket), "focus": list(ALL_FOCI),
                "title": c["title"], "description": c["description"], "bracket_label": ages,
            }
            if task_type == "reading":
                ex["passage"] = c["passage"]
                ex["target_wpm"] = BRACKETS[bracket]["target_wpm"]
                if c.get("tone_hints"):
                    ex["tone_hints"] = c["tone_hints"]
            elif task_type == "picture":
                ex["image_url"] = f"{IMAGE_DIR}/{c['image']}"
                ex["prompts"] = c["prompts"]
            else:
                ex["situation"] = c["situation"]
                ex["prompts"] = c["prompts"]
            out.append(ex)
    return out


BRACKET_EXERCISES: list[dict] = _build()

# ------------------------------------------------------------------------------- advanced picture description
# One harder scene per bracket: more people, more going on, more reasoning. It is extra practice for that
# bracket only (min_bracket = max_bracket) and unlocks once the bracket's own picture task has been done.
_ADVANCED_PICTURES: dict[int, dict] = {
    1: {"title": "The Birthday Party", "image": "b1-birthday-adv.svg",
        "description": "Lots of things are happening at this party. Tell me about each person and the dog.",
        "prompts": ["What is the boy doing?", "What is the girl holding?", "What does the dog want?",
                    "What do you think happens after the candles go out?"]},
    2: {"title": "Oops! The Paint Spill", "image": "b2-classroom-spill-adv.svg",
        "description": "Something went wrong in the art class. Explain what happened and how everyone is helping.",
        "prompts": ["What happened to the paint?", "What is the girl running to do?",
                    "Where is the cat going, and what is it leaving behind?", "How can the class clean up and stop it happening again?"]},
    3: {"title": "The Flooded Road", "image": "b3-flooded-road-adv.svg",
        "description": "Look for the causes and the effects in this rainy street scene.",
        "prompts": ["Why has the road flooded?", "What problem does the tuk-tuk driver have, and who is helping?",
                    "What is blocking the drain, and how did it get there?", "What could the neighbourhood do before the next big rain?"]},
    4: {"title": "The Vesak Dansala", "image": "b4-vesak-dansala-adv.svg",
        "description": "Describe this Vesak night scene in order, from the lanterns to the people in the queue.",
        "prompts": ["What is a dansala, and what is being served here?", "What jobs are the volunteers and the child doing?",
                    "Why do you think people give free food at Vesak?", "How would you organise the queue if it got very long?"]},
    5: {"title": "The Science Fair", "image": "b5-science-fair-adv.svg",
        "description": "Describe the science fair - the projects, the people and how each of them might be feeling.",
        "prompts": ["What is the student explaining to the judges?", "Why might the student on the right look nervous?",
                    "What has happened at the volcano project?", "Which project would you give first prize to, and why?"]},
    6: {"title": "The Beach Clean-up", "image": "b6-beach-cleanup-adv.svg",
        "description": "Describe the clean-up and explain what this scene says about people and the ocean.",
        "prompts": ["What are the volunteers doing, and why?", "What has happened to the turtle?",
                    "What is the tourist doing, and what does it show?", "What long-term changes would reduce plastic on beaches?"]},
    7: {"title": "Rainfall and the Reservoir", "image": "b7-rainfall-graph-adv.svg",
        "description": "Interpret the two measures on this chart and explain how they are connected.",
        "prompts": ["Which months had the most and the least rain?", "How does the reservoir level change, and why is there a delay?",
                    "What happens to the reservoir from July, and what might cause that?", "What would you advise a water board based on this chart?"]},
    8: {"title": "The Hospital Waiting Area", "image": "b8-hospital-adv.svg",
        "description": "Describe this busy outpatient clinic in an organised way, then say how it could run more smoothly.",
        "prompts": ["What is happening at the reception desk and on the number display?", "Who needs help, and what kind of help?",
                    "How might the mother and the child be feeling?", "What two changes would improve this waiting area?"]},
}


def _build_advanced() -> list[dict]:
    out = []
    for bracket, c in _ADVANCED_PICTURES.items():
        out.append({
            "id": f"b{bracket}-picture-advanced", "type": "picture", "level": "advanced",
            "difficulty": min(3, _difficulty(bracket) + 1), "focus": list(ALL_FOCI),
            "min_bracket": bracket, "max_bracket": bracket, "unlock_after": f"b{bracket}-picture",
            "bracket_label": BRACKETS[bracket]["label"],
            "title": f"Advanced Picture - {c['title']}", "description": c["description"],
            "image_url": f"{IMAGE_DIR}/{c['image']}", "prompts": c["prompts"],
        })
    return out


ADVANCED_PICTURE_EXERCISES: list[dict] = _build_advanced()


def bracket_exercises(bracket: int) -> list[dict]:
    """The three core tasks (reading, picture, conversation) of one bracket."""
    return [e for e in BRACKET_EXERCISES if e["bracket"] == bracket]


def word_count(text: str) -> int:
    return len(text.split())
