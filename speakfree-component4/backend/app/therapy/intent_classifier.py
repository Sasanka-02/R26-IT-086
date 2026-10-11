"""
Assistant intent classifier — multinomial Naive Bayes on normalised words.

Trained at start-up on the labelled example questions below. For a new
message it returns the most likely intent and a confidence (posterior
probability). Low-confidence or out-of-domain messages are handed to the
language model (if configured) or answered with a "not sure" fallback,
instead of guessing.

Text pre-processing (so that different phrasings share features):
  1. lower-case and split into words
  2. synonym mapping    ("fast", "quick", "slow" -> "speed"; "stammer" -> "block")
  3. stop-word removal  ("what", "is", "my" carry no intent)
  4. light stemming     ("pausing" -> "paus", "scores" -> "score")

Model:
    P(intent | words) ∝ P(intent) · Π P(word | intent)
    P(word | intent)  = (count(word, intent) + α) / (total(intent) + α·|V|)   (additive smoothing)

Accuracy is measured with leave-one-out cross-validation over the
training examples and reported on the therapist evidence page.
"""

import math
import re
from collections import Counter

CONFIDENCE_THRESHOLD = 0.5
SMOOTHING_ALPHA = 0.2

STOP_WORDS = set(
    "a an the is am are was were i im i'm my me to do does did of for in on it its this that "
    "what how why when which can could should would you your be been with about and or so get "
    "at there here please just some any".split()
)

# Words that mean the same thing for this assistant share one feature.
SYNONYMS = {
    "speed": "fast quick quickly rapid rush rushing slow slower slowly pace wpm speed".split(),
    "block": (
        "block blocks blocking stuck stutter stuttering stammer stammering freeze freezing "
        "pause pauses pausing silence hesitate"
    ).split(),
    "volume": "quiet loud louder volume soft softly project mumble".split(),
    "score": "score scores mark marks points result results grade".split(),
    "level": "level levels unlock stage intermediate advanced beginner".split(),
    "anxious": (
        "nervous anxious anxiety scared afraid fear stress stressed frustrated worried hard difficult"
    ).split(),
    "practise": "practise practice practicing practising exercise exercises train".split(),
    "badge": "badge badges achievement achievements reward rewards trophy trophies".split(),
    "goal": "goal goals target targets objective".split(),
    "hello": "hello hi hey morning evening afternoon greetings".split(),
    "thanks": "thanks thank cheers appreciate grateful".split(),
    "private": "privacy private data recorded recording recordings upload uploaded stored audio safe".split(),
    "streak": "streak daily everyday row often".split(),
}
_SYNONYM_OF = {w: key for key, words in SYNONYMS.items() for w in words}

TRAINING_DATA: dict[str, list[str]] = {
    "greeting": [
        "hi", "hello", "hey there", "good morning", "hello assistant", "hi there",
        "good evening", "hey", "greetings", "hello again", "good afternoon",
    ],
    "thanks": [
        "thank you", "thanks a lot", "thanks", "cheers", "that helps thank you",
        "great thanks", "thank you so much", "i appreciate it", "ok thanks",
    ],
    "progress": [
        "how am i doing", "show my progress", "am i improving", "how did i do",
        "am i getting better", "how is my progress", "did i improve this week",
        "how have i been doing lately", "tell me about my progress", "am i doing well",
        "how is it going overall", "summary of my practice",
    ],
    "next": [
        "what should i practise next", "what should i do today", "recommend an exercise",
        "what is next", "which exercise should i do", "what should i practice",
        "give me a plan", "suggest something to practise", "what do you recommend",
        "what exercise now", "plan for today", "which one should i try",
    ],
    "level": [
        "what is my level", "what level am i", "how do i unlock the next level",
        "when do i reach advanced", "how to get to intermediate", "am i at the final stage",
        "what is my reading level", "how many more readings to level up", "level up",
        "when will i unlock the next stage",
    ],
    "goals": [
        "what are my goals", "did my therapist set goals", "am i meeting my goals",
        "what is my target", "my therapist goals", "goal progress", "have i reached my target",
        "what targets do i have",
    ],
    "badges": [
        "what badges do i have", "my achievements", "what rewards did i earn",
        "show my badges", "how do i get more badges", "which trophies have i won",
        "list my achievements",
    ],
    "score_explain": [
        "why did i get this score", "how is my score calculated", "explain my score",
        "what does the score mean", "why is my score low", "how do you score me",
        "how are the points worked out", "why did i get low marks", "what affects my score",
        "how is the result calculated",
    ],
    "tip_pause": [
        "tips for long pauses", "i get stuck on words", "how to stop blocking",
        "what to do when i stutter", "i keep pausing", "help with blocks",
        "how do i stop stammering", "i freeze when speaking", "i hesitate a lot",
        "words get stuck", "how to handle a block",
    ],
    "tip_volume": [
        "my voice is too quiet", "how to speak louder", "volume tips",
        "people say i am too soft", "how to project my voice", "i mumble",
        "the mic says i am quiet",
    ],
    "tip_speed": [
        "i speak too fast", "how to slow down", "my speech is too quick",
        "tips for speaking slower", "what speed should i read at", "words per minute",
        "i talk too fast", "i rush when reading", "how fast should i speak", "i read too slowly",
    ],
    "anxiety": [
        "i feel nervous", "i am anxious about speaking", "this is too hard",
        "i feel stressed", "speaking scares me", "i am frustrated", "i want to give up",
        "i am worried", "this is difficult", "i am afraid to talk",
    ],
    "explain_daf": [
        "what is daf", "explain delayed auditory feedback", "how does the delay exercise work",
        "why do i hear my voice late", "what is the delay for", "tell me about daf",
        "how does daf help",
    ],
    "explain_pacing": [
        "what is pacing", "how does the pacing exercise work", "why does the word highlight move",
        "explain pacing practice", "tell me about pacing", "what is the highlighted word for",
    ],
    "explain_picture": [
        "how does picture description work", "what do i say about the picture",
        "explain the picture exercise", "help with describing the image",
        "what should i describe in the image", "tell me about the picture task",
    ],
    "explain_reading": [
        "how does reading practice work", "explain the reading levels",
        "what are the reading exercises", "tell me about the reading passages",
        "how do the reading passages work", "what is reading practice",
    ],
    "privacy": [
        "is my voice recorded", "where is my data stored", "who can see my results",
        "is my audio uploaded", "privacy", "is this private", "is my data safe",
        "do you keep my recordings",
    ],
    "streak": [
        "what is my streak", "how many days in a row", "how often should i practise",
        "should i practise every day", "daily practice", "how many days have i practised",
    ],
}


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def tokenize(text: str) -> list[str]:
    tokens = []
    for word in re.findall(r"[a-z']+", text.lower()):
        if word in _SYNONYM_OF:
            tokens.append(_SYNONYM_OF[word])
        elif word not in STOP_WORDS:
            stem = _stem(word)
            tokens.append(_SYNONYM_OF.get(stem, stem))
    return tokens


class NaiveBayesIntentClassifier:
    def __init__(self, data: dict[str, list[str]]):
        self.fit(data)

    def fit(self, data: dict[str, list[str]]) -> None:
        self.intents = list(data)
        total = sum(len(v) for v in data.values())
        self.log_prior = {i: math.log(len(data[i]) / total) for i in self.intents}
        self.counts = {i: Counter(t for s in data[i] for t in tokenize(s)) for i in self.intents}
        self.totals = {i: sum(self.counts[i].values()) for i in self.intents}
        self.vocab = set().union(*self.counts.values())

    def predict(self, text: str) -> tuple[str, float]:
        tokens = [t for t in tokenize(text) if t in self.vocab]
        if not tokens:
            return "unknown", 0.0
        v = len(self.vocab)
        scores = {
            i: self.log_prior[i]
            + sum(
                math.log((self.counts[i][t] + SMOOTHING_ALPHA) / (self.totals[i] + SMOOTHING_ALPHA * v))
                for t in tokens
            )
            for i in self.intents
        }
        best = max(scores, key=scores.get)
        m = scores[best]
        norm = sum(math.exp(s - m) for s in scores.values())
        return best, 1 / norm


def leave_one_out_accuracy(data: dict[str, list[str]] = TRAINING_DATA) -> dict:
    correct = total = 0
    for intent, examples in data.items():
        for i, example in enumerate(examples):
            held_out = {k: (v[:i] + v[i + 1:] if k == intent else v) for k, v in data.items()}
            predicted, _ = NaiveBayesIntentClassifier(held_out).predict(example)
            correct += predicted == intent
            total += 1
    return {
        "examples": total,
        "intents": len(data),
        "accuracy": round(100 * correct / total, 1),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
    }


classifier = NaiveBayesIntentClassifier(TRAINING_DATA)
