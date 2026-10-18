"""
Extra practice carried over from the stand-alone Component 4 prototype, re-tagged for the
integrated platform's age brackets (1-8) and therapy foci.

  words      picture-card rounds for ages 6-11 (brackets 1-3): a 10-step WORD LADDER
             (7 word levels: easy starts -> long tricky words, then 3 phrase stages:
             two-word phrases, short sentences, tongue twisters) + a Sri Lankan bonus set.
             The child says each word and a grown-up taps "Got it / Almost / Hard";
             items_clear / items_total is the round's goal completion.
  roleplay   real-life situations answered out loud - class talks, ordering food, phone calls,
             job interviews. The other person's lines are on screen, with example answers to
             peek at. Scored like conversation (free speech: no speed target).
  picture    extra scenes for teens and adults (canteen, cricket match, market, station),
             each with guiding questions and example sentences.
  pacing     "slow snail" passages for the youngest learners.

Every exercise uses the same keys as exercises.py (`min_bracket` / `max_bracket` keep it inside
the right age range). The word ladder is replayed like the other ladders (adaptive.word_state):
only the learner's current word level is offered, higher ones are shown locked.
"""
from __future__ import annotations

KIDS_MAX_BRACKET = 3   # ages 6-11
WORD_LEVEL_COUNT = 7   # single-word levels; the phrase stage follows
WORD_LADDER_SIZE = 10  # 7 word levels + 3 phrase stages

_VOWELS = "aeiou"
_SMOOTH = "mnslfwhy"
_STOPS = "pbtdkgc"
_CLUSTERS = ("spl", "spr", "str", "scr", "sp", "st", "sn", "sl", "sm", "sw", "sk",
             "tr", "dr", "pr", "br", "fr", "gr", "cr", "pl", "bl", "fl", "gl", "cl")

WORD_FOCUS = ["fluency", "speech_sounds", "maintenance"]
TALK_FOCUS = ["fluency", "maintenance"]
PICTURE_FOCUS = ["fluency", "speech_sounds", "maintenance"]


def word_tip(text: str) -> str:
    """A gentle-start tip from how the word begins."""
    word = text.lower().lstrip("'\"")
    if word.startswith(_CLUSTERS):
        return "Slide the sounds together slowly"
    if word[:1] in _VOWELS:
        return "Start softly with an easy breath"
    if word[:1] in _SMOOTH:
        return f"Stretch the first sound gently: {word[0] * 3}-{word[1:]}"
    if word[:1] in _STOPS:
        return "Light touch on the first sound"
    return "Say it slowly and smoothly"


def word_stage_label(word_level: int) -> str:
    """'Word Level 3' for 1-7, 'Phrase Stage 2' for the three phrase stages."""
    if word_level <= WORD_LEVEL_COUNT:
        return f"Word Level {word_level}"
    return f"Phrase Stage {word_level - WORD_LEVEL_COUNT}"


def _cards(items: list[tuple[str, int, str]]) -> list[dict]:
    return [{"text": t, "syllables": s, "emoji": e, "tip": word_tip(t)} for t, s, e in items]


# (word level, id suffix, name, description, difficulty, cards: (text, syllables, emoji))
_WORD_LADDER = [
    (1, "1", "Easy start", "Words that begin with an open vowel or a smooth sound - the easiest to start.", 1, [
        ("eye", 1, "👁️"), ("egg", 1, "🥚"), ("owl", 1, "🦉"), ("arm", 1, "💪"), ("moon", 1, "🌙"),
        ("me", 1, "🙋"), ("no", 1, "🙅"), ("more", 1, "➕"), ("sun", 1, "☀️"), ("fish", 1, "🐟"),
    ]),
    (2, "2", "Early sounds", "Short words with the first sounds children learn: b, m, d, h, p, t.", 1, [
        ("ball", 1, "⚽"), ("bee", 1, "🐝"), ("map", 1, "🗺️"), ("mum", 1, "👩"), ("dog", 1, "🐶"),
        ("hat", 1, "🎩"), ("pie", 1, "🥧"), ("top", 1, "🔝"), ("bed", 1, "🛏️"), ("two", 1, "2️⃣"),
    ]),
    (3, "3", "Two syllables", "Two-beat words made from early sounds. Keep the voice on between the beats.", 1, [
        ("baby", 2, "👶"), ("mummy", 2, "👩‍👧"), ("puppy", 2, "🐕"), ("happy", 2, "😄"), ("teddy", 2, "🧸"),
        ("water", 2, "💧"), ("window", 2, "🪟"), ("button", 2, "🔘"), ("honey", 2, "🍯"), ("tummy", 2, "😋"),
    ]),
    (4, "4", "Middle sounds", "Words with k, g and f sounds, including some two-syllable words.", 2, [
        ("cat", 1, "🐱"), ("cup", 1, "🥤"), ("cake", 1, "🎂"), ("goat", 1, "🐐"), ("fan", 1, "🪭"),
        ("kite", 1, "🪁"), ("coffee", 2, "☕"), ("cookie", 2, "🍪"), ("finger", 2, "👆"), ("garden", 2, "🌷"),
    ]),
    (5, "5", "Late sounds", "Words with the later sounds: s, z, sh, ch, j, l, r, th and v.", 2, [
        ("sock", 1, "🧦"), ("zoo", 1, "🦓"), ("shoe", 1, "👟"), ("chair", 1, "🪑"), ("jam", 1, "🫙"),
        ("lion", 2, "🦁"), ("rabbit", 2, "🐰"), ("thumb", 1, "👍"), ("van", 1, "🚐"), ("red", 1, "🔴"),
    ]),
    (6, "6", "Clusters", "Two consonants together at the start (sp, st, tr, bl...). Slide them slowly.", 3, [
        ("spoon", 1, "🥄"), ("star", 1, "⭐"), ("snake", 1, "🐍"), ("tree", 1, "🌳"), ("train", 1, "🚆"),
        ("frog", 1, "🐸"), ("blue", 1, "🔵"), ("plane", 1, "✈️"), ("flower", 2, "🌸"), ("sleep", 1, "😴"),
    ]),
    (7, "7", "Long and tricky", "Long words with three or more syllables. Say them beat by beat.", 3, [
        ("butterfly", 3, "🦋"), ("elephant", 3, "🐘"), ("umbrella", 3, "☂️"), ("banana", 3, "🍌"),
        ("tomato", 3, "🍅"), ("helicopter", 4, "🚁"), ("caterpillar", 4, "🐛"), ("strawberry", 3, "🍓"),
        ("ambulance", 3, "🚑"), ("hippopotamus", 5, "🦛"),
    ]),
    (8, "phrases", "Two-word phrases", "Join two words with one smooth breath.", 3, [
        ("big ball", 2, "⚽"), ("red car", 2, "🚗"), ("my dog", 2, "🐶"), ("hot sun", 2, "☀️"),
        ("blue sky", 2, "🌤️"), ("little fish", 3, "🐟"),
    ]),
    (9, "sentences", "Short sentences", "Short sentences. Keep the words flowing like one long word.", 3, [
        ("I see a cat.", 4, "🐱"), ("The sun is hot.", 4, "☀️"), ("My dog can run.", 4, "🐶"),
        ("The bird can fly.", 4, "🐦"), ("I like red apples.", 5, "🍎"), ("We go to school.", 4, "🏫"),
    ]),
    (10, "twisters", "Tongue twisters", "Fun tongue twisters. Slow is the secret - speed doesn't matter.", 3, [
        ("Red lorry, yellow lorry", 6, "🚚"), ("Big black bug", 3, "🐞"), ("She sells sea shells", 4, "🐚"),
        ("Fresh fried fish", 3, "🐟"), ("Six slippery snails", 5, "🐌"),
    ]),
]

WORD_EXERCISES: list[dict] = [
    {
        "id": f"words-{suffix}", "type": "words", "word_level": level, "difficulty": difficulty,
        "focus": WORD_FOCUS, "max_bracket": KIDS_MAX_BRACKET,
        "title": f"{word_stage_label(level)} - {name}", "description": description, "words": _cards(cards),
    }
    for level, suffix, name, description, difficulty, cards in _WORD_LADDER
] + [
    {
        "id": "words-sri-lanka", "type": "words", "word_level": None, "difficulty": 2,
        "focus": WORD_FOCUS, "max_bracket": KIDS_MAX_BRACKET,
        "title": "Bonus - Sri Lankan words",
        "description": "Words from home: fruit, food and animals from Sri Lanka. Open any time.",
        "words": _cards([
            ("mango", 2, "🥭"), ("rice", 1, "🍚"), ("tea", 1, "🍵"), ("coconut", 3, "🥥"), ("papaya", 3, "🍈"),
            ("tuk-tuk", 2, "🛺"), ("peacock", 2, "🦚"), ("elephant", 3, "🐘"), ("pineapple", 3, "🍍"),
        ]),
    },
]
WORD_LADDER_IDS = {ex["word_level"]: ex["id"] for ex in WORD_EXERCISES if ex["word_level"] is not None}


def _roleplay(ex_id: str, brackets: tuple[int, int], difficulty: int, title: str, situation: str,
              lines: list[str], examples: list[str]) -> dict:
    lo, hi = brackets
    return {
        "id": ex_id, "type": "roleplay", "difficulty": difficulty, "focus": TALK_FOCUS,
        "min_bracket": lo, "max_bracket": hi, "title": title, "description": situation,
        "situation": situation, "prompts": lines, "examples": examples,
    }


TEENS, OLDER_TEENS, ADULTS = (4, 6), (6, 6), (7, 8)

ROLEPLAY_EXERCISES: list[dict] = [
    # ---------------- teens (ages 12-17) ----------------
    _roleplay("teen-present-self", TEENS, 2, "Class talk - Introduce yourself",
              "It's the first day with a new class teacher. Stand up and introduce yourself for about one minute.",
              ["What is your name and which school did you come from?", "What do you like doing after school?",
               "Which subject do you enjoy most, and why?", "What is one thing you want to do this year?"],
              ["Good morning everyone, my name is Dinuli and I came from a school in Kandy.",
               "After school I like playing badminton and drawing.",
               "My favourite subject is science, because I like doing experiments.",
               "This year I want to join the debating team."]),
    _roleplay("teen-present-sport", TEENS, 2, "Class talk - My favourite sport (1 minute)",
              "Give a one-minute class presentation about your favourite sport.",
              ["Which sport is it, and how did you start?", "What are the basic rules?",
               "Who is a player you admire?", "Why should others try it?"],
              ["My favourite sport is cricket. I started playing with my father when I was seven.",
               "Each team bats and bowls, and the team with more runs wins.",
               "I admire Kumar Sangakkara because he was calm under pressure.",
               "Everyone should try it - it teaches teamwork and patience."]),
    _roleplay("teen-roleplay-teacher", TEENS, 3, "Role-play - Answering the teacher",
              "Your teacher asks you a question in front of the class. Answer clearly in two or three sentences.",
              ["Teacher: Can you explain what photosynthesis is?", "Teacher: Why do you think it's important?",
               "Teacher: Can you give an example from everyday life?"],
              ["Photosynthesis is how plants make food using sunlight, water and carbon dioxide.",
               "It's important because it gives us oxygen and food.",
               "For example, the paddy fields need sunlight to grow rice."]),
    _roleplay("teen-roleplay-food", TEENS, 3, "Role-play - Ordering kottu with friends",
              "You're at a kottu stall with friends and it's your turn to order for everyone.",
              ["Seller: What would you like?", "Seller: Chicken or vegetable? Spicy?",
               "Seller: Anything to drink?", "Seller: That's 2,400 rupees."],
              ["Can we have three chicken kottu and one vegetable kottu, please?",
               "Medium spicy for all of them, please.", "Four bottles of water, thank you.",
               "Here you are. Can we have the bill, please?"]),
    _roleplay("teen-roleplay-friend", TEENS, 3, "Role-play - Phone call to a friend",
              "Call a friend to plan going to the cinema this weekend.",
              ["Friend: Hello? Who's this?", "Friend: Which film do you want to see?",
               "Friend: What time should we meet?", "Friend: How are we getting there?"],
              ["Hi, it's Kavindu. Are you free on Saturday?", "Let's watch the new animated film.",
               "The show starts at four, so let's meet at half past three.", "We can take a tuk-tuk from my place."]),
    _roleplay("teen-roleplay-interview", OLDER_TEENS, 3, "Role-play - University admission interview",
              "You are being interviewed for a place on a university course. Answer each question calmly.",
              ["Interviewer: Why do you want to study this course?", "Interviewer: Tell us about a project you are proud of.",
               "Interviewer: How do you handle pressure before exams?", "Interviewer: Do you have any questions for us?"],
              ["I want to study engineering because I enjoy solving practical problems.",
               "I built a small solar lamp for our science exhibition.",
               "I make a timetable and take short breaks so I don't panic.",
               "Yes - are there chances to do research in the first year?"]),
    # ---------------- adults (18+) ----------------
    _roleplay("adult-roleplay-doctor", ADULTS, 2, "Role-play - Booking a doctor's appointment",
              "Phone a clinic to book an appointment with a doctor.",
              ["Receptionist: Good morning, City Medical Centre. How can I help?", "Receptionist: Which doctor would you like to see?",
               "Receptionist: Is Thursday at 5.30 suitable?", "Receptionist: Can I have your name and phone number?"],
              ["Good morning, I'd like to book an appointment, please.",
               "I'd like to see Dr. Fernando, the general physician.",
               "Thursday at 5.30 is fine, thank you.",
               "My name is Sunil Perera and my number is 077 123 4567."]),
    _roleplay("adult-roleplay-restaurant", ADULTS, 2, "Role-play - Ordering at a restaurant",
              "You're at a restaurant with a colleague. Order for both of you and ask about the bill.",
              ["Waiter: Are you ready to order?", "Waiter: Would you like rice and curry or fried rice?",
               "Waiter: Anything to drink?", "Waiter: Would you like the bill now?"],
              ["Yes, we're ready, thank you.", "Two rice and curry, please - one with fish and one vegetarian.",
               "Two lime juices, please.", "Yes please, and can I pay by card?"]),
    _roleplay("adult-roleplay-work-intro", ADULTS, 2, "Role-play - Introducing yourself at work",
              "It's your first day at a new office. Introduce yourself to your team at the morning meeting.",
              ["Manager: Everyone, this is our new team member.", "Colleague: What did you do before joining us?",
               "Colleague: What will you be working on?", "Manager: Anything else you'd like to share?"],
              ["Good morning, everyone. I'm Nadeesha and I've joined as an accountant.",
               "Before this, I worked at a bank in Colombo for three years.",
               "I'll be handling the monthly reports and supplier payments.",
               "I'm looking forward to working with you all."]),
    _roleplay("adult-interview-about", ADULTS, 3, "Job interview - Tell me about yourself",
              "A job interview for a role you'd like. Answer the interviewer's questions in full sentences.",
              ["Interviewer: Tell me about yourself.", "Interviewer: Why do you want this job?",
               "Interviewer: Where do you see yourself in five years?"],
              ["I'm a marketing graduate with two years of experience in digital campaigns.",
               "This role matches my skills, and I admire your company's work in tourism.",
               "In five years I'd like to be leading a small team."]),
    _roleplay("adult-interview-strengths", ADULTS, 3, "Job interview - Strengths and weaknesses",
              "The interviewer asks about your strengths and how you handle challenges.",
              ["Interviewer: What are your strengths?", "Interviewer: What is one weakness you're working on?",
               "Interviewer: Tell me about a difficult situation at work and what you did."],
              ["I'm organised, and I stay calm when deadlines are close.",
               "I used to avoid speaking in meetings, so I now prepare two points in advance.",
               "When a supplier delivered late, I rearranged the schedule and kept the client informed."]),
    _roleplay("adult-presentation", ADULTS, 3, "Work talk - A 2-minute project update",
              "Present a short update to your team about a project. Aim for about two minutes.",
              ["What is the project and why does it matter?", "What has been done so far?",
               "What problems came up and how were they solved?", "What happens next, and what do you need from the team?"],
              ["Today I'll update you on the new customer feedback system.",
               "We have collected 300 responses in the first month.",
               "Response rates were low at first, so we added SMS reminders.",
               "Next month we'll share a report, and I'd like two volunteers to review it."]),
    _roleplay("adult-meeting", ADULTS, 3, "Work talk - Speaking up in a meeting",
              "In a team meeting, the manager asks for opinions. Give your view and a suggestion.",
              ["Manager: Does anyone have concerns about the new schedule?", "Colleague: I think it will work fine.",
               "Manager: What would you suggest instead?"],
              ["I have one concern: the Friday deadline clashes with month-end closing.",
               "I agree it can work, but we may need one more day.",
               "Could we move the deadline to Monday and review progress on Thursday?"]),
]

PICTURE_EXERCISES: list[dict] = [
    {
        "id": "picture-teen-canteen", "type": "picture", "difficulty": 2, "focus": PICTURE_FOCUS,
        "min_bracket": 4, "max_bracket": 6,
        "title": "Picture Description - The School Canteen",
        "description": ("Describe what is happening in the school canteen at interval. Talk about the people, "
                        "what they are doing and what you think happens next."),
        "image_url": "/therapy/picture-teen-canteen.svg",
        "prompts": ["What are the students in the queue waiting for?", "What is each student at the table doing?",
                    "What happened to the boy near the front, and what should he do now?",
                    "What is the notice board about? Would you take part?"],
        "examples": ["Two students are waiting in the queue to buy fish buns and tea.",
                     "One girl at the table is laughing, another is reading a book, and a boy is drinking water.",
                     "A boy has spilled his drink on the floor, so he should tell the canteen aunty and clean it up.",
                     "The notice says the sports meet is on Friday at eight in the morning."],
    },
    {
        "id": "picture-teen-cricket", "type": "picture", "difficulty": 2, "focus": PICTURE_FOCUS,
        "min_bracket": 4, "max_bracket": 6,
        "title": "Picture Description - The Inter-House Cricket Match",
        "description": "Describe the cricket match like a sports commentator. Explain who is doing what and how the game is going.",
        "image_url": "/therapy/picture-teen-cricket.svg",
        "prompts": ["What is the batsman doing right now?", "Who else can you see on the field, and what are their jobs?",
                    "What does the scoreboard tell you? Is Blue House winning?",
                    "How are the students under the tree feeling? How do you know?"],
        "examples": ["The batsman is swinging his bat at the red ball.",
                     "The bowler has just bowled, the wicketkeeper is waiting behind the stumps, and the umpire is watching.",
                     "Blue House has scored 124 runs for 3 wickets after 18 overs, and they need 150 to win.",
                     "The students are cheering and holding a banner that says Go Blue House."],
    },
    {
        "id": "picture-adult-market", "type": "picture", "difficulty": 3, "focus": PICTURE_FOCUS, "min_bracket": 7,
        "title": "Picture Description - A Busy Market Street",
        "description": ("A detailed, busy scene. Describe it in an organised way - from left to right, or from the "
                        "street to the shops - then explain what problems people might be facing and why."),
        "image_url": "/therapy/picture-adult-market.svg",
        "prompts": ["Describe the scene in order, as if you were explaining it to someone on the phone.",
                    "What is the traffic policeman doing, and why is it needed here?",
                    "Why do you think the man on the right is running?",
                    "If you needed medicine and a new phone charger, where would you go and how would you get there?",
                    "What could be done to make this street safer or less crowded?"],
        "examples": ["This is a crowded market street in the morning, with shops on both sides and heavy traffic in the middle.",
                     "The traffic policeman is blowing his whistle and directing the vehicles, because the crossing is very busy.",
                     "The man is probably running to catch the 138 bus to Kottawa before it leaves.",
                     "A separate lane for buses and fewer vendors on the road would make it safer for pedestrians."],
    },
    {
        "id": "picture-adult-station", "type": "picture", "difficulty": 3, "focus": PICTURE_FOCUS, "min_bracket": 7,
        "title": "Picture Description - Railway Station at Rush Hour",
        "description": ("A complex scene with information to read and situations to explain. Describe what is "
                        "happening, use the details to make sensible guesses, and say what you would do."),
        "image_url": "/therapy/picture-adult-station.svg",
        "prompts": ["What time is it, and what does the departure board tell travellers?",
                    "Why do you think the man near the front is checking his watch?",
                    "Describe three different people on the platform and what they are doing.",
                    "If you were travelling to Badulla, what would you do now, and why?",
                    "How could the station make the delay less stressful for passengers?"],
        "examples": ["It is a quarter to six in the evening, and the board shows the Badulla train is delayed by twenty minutes.",
                     "He is probably worried because his train is late and he has somewhere important to be.",
                     "A mother is holding her child's hand, an elderly man is resting on a bench, and a vendor is selling peanuts.",
                     "I would buy my ticket now, find a seat, and call home to say I will be late."],
    },
]

KIDS_PACING: list[dict] = [
    {
        "id": "kids-pacing-boat", "type": "pacing", "difficulty": 1, "focus": ["fluency"], "max_bracket": KIDS_MAX_BRACKET,
        "title": "Slow Snail Pacing - The Little Boat",
        "description": "Read like a slow snail 🐌 - follow the yellow word and don't rush.",
        "target_wpm": 70,
        "passage": "A little boat sails on the sea. The wind is soft. A fish jumps up. Splash! The boat goes home.",
    },
    {
        "id": "kids-pacing-cat", "type": "pacing", "difficulty": 1, "focus": ["fluency"], "max_bracket": KIDS_MAX_BRACKET,
        "title": "Slow Snail Pacing - The Sleepy Cat",
        "description": "Read like a slow snail 🐌 - one word at a time, nice and soft.",
        "target_wpm": 65,
        "passage": "My cat is sleepy. She sits on the mat. She licks her paw. Then she naps in the sun. Shh!",
    },
    {
        "id": "kids-pacing-tuktuk", "type": "pacing", "difficulty": 1, "focus": ["fluency"], "max_bracket": KIDS_MAX_BRACKET,
        "title": "Slow Snail Pacing - The Tuk-Tuk Ride",
        "description": "A slow snail ride 🐌🛺 - follow the yellow word and keep your voice gentle.",
        "target_wpm": 75,
        "passage": ("We ride in a red tuk-tuk. It goes beep, beep! We see a big elephant. "
                    "We wave to the man. Then we go home for rice."),
    },
]

EXTRA_EXERCISES: list[dict] = WORD_EXERCISES + ROLEPLAY_EXERCISES + PICTURE_EXERCISES + KIDS_PACING
