"""Percentage of Consonants Correct (PCC) scoring for SpeakFree Component 2.

Clinical basis
--------------
PCC = correct target consonants / total target consonants x 100
    Shriberg & Kwiatkowski (1982), J Speech Hear Disord 47(3):256-270,
    DOI 10.1044/jshd.4703.256. Severity bands are from the same paper.
PCC-R (revised) scores distortions as correct; PVC (vowels) and PPC (all
phonemes) are the companion metrics.
    Shriberg et al. (1997), J Speech Lang Hear Res 40(4):708-722,
    DOI 10.1044/jslhr.4004.708.

Automation
----------
* Intended (target) phonemes: the words the speaker meant to say (a known
  stimulus text, or a transcript used as the gloss) looked up in the CMU
  Pronouncing Dictionary.
* Produced phonemes: IPA output of a phoneme recogniser.
* The two sequences are aligned with a phonetically weighted edit distance;
  each target consonant is then scored correct, distorted, substituted or
  omitted. Additions are reported but, as in PCC, not counted as errors.
* Casual-speech allophones (flapped /t,d/, glottal /t/, aspiration, dark /l/,
  syllabic consonants) are scored correct, following the PCC scoring rules.
  Non-English realisations of an English target (e.g. dentalised [s̪] for /s/)
  are scored as distortions.
"""
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Optional

CONSONANTS = frozenset(
    "B CH D DH F G HH JH K L M N NG P R S SH T TH V W Y Z ZH".split()
)
VOWELS = frozenset("AA AE AH AO AW AY EH ER EY IH IY OW OY UH UW".split())

ARPABET_TO_IPA = {
    "AA": "ɑ", "AE": "æ", "AH": "ʌ", "AO": "ɔ", "AW": "aʊ", "AY": "aɪ", "B": "b",
    "CH": "tʃ", "D": "d", "DH": "ð", "EH": "ɛ", "ER": "ɝ", "EY": "eɪ", "F": "f",
    "G": "ɡ", "HH": "h", "IH": "ɪ", "IY": "i", "JH": "dʒ", "K": "k", "L": "l",
    "M": "m", "N": "n", "NG": "ŋ", "OW": "oʊ", "OY": "ɔɪ", "P": "p", "R": "ɹ",
    "S": "s", "SH": "ʃ", "T": "t", "TH": "θ", "UH": "ʊ", "UW": "u", "V": "v",
    "W": "w", "Y": "j", "Z": "z", "ZH": "ʒ",
}

# Produced IPA -> accepted English target phonemes.
_EXACT = {
    "p": "P", "b": "B", "t": "T", "d": "D", "k": "K", "ɡ": "G", "g": "G", "m": "M",
    "n": "N", "ŋ": "NG", "f": "F", "v": "V", "θ": "TH", "ð": "DH", "s": "S", "z": "Z",
    "ʃ": "SH", "ʒ": "ZH", "h": "HH", "tʃ": "CH", "dʒ": "JH", "l": "L", "ɹ": "R",
    "w": "W", "j": "Y",
    "ə": "AH", "ɐ": "AH AA", "ᵻ": "IH AH", "ɪ": "IH", "i": "IY", "iː": "IY", "ɛ": "EH",
    "ɛː": "EH", "e": "EY EH", "eː": "EY", "eɪ": "EY", "æ": "AE", "a": "AA AE", "aː": "AA",
    "ɑ": "AA", "ɑː": "AA", "ɒ": "AA AO", "ɔ": "AO", "ɔː": "AO", "o": "OW AO", "oː": "OW",
    "oʊ": "OW", "əʊ": "OW", "ʊ": "UH", "u": "UW", "uː": "UW", "ʌ": "AH", "ɜ": "ER",
    "ɜː": "ER", "ɚ": "ER", "aɪ": "AY", "aʊ": "AW", "ɔɪ": "OY", "oɪ": "OY",
}
# Allophonic / casual-speech variants: scored correct (PCC rules).
_ALLOPHONES = {
    "ɾ": "T D", "ʔ": "T", "ɫ": "L", "n̩": "N", "l̩": "L", "pʰ": "P", "tʰ": "T",
    "kʰ": "K", "ph": "P", "th": "T", "kh": "K", "pː": "P", "tː": "T", "kː": "K",
    "bː": "B", "dː": "D", "ɡː": "G", "lː": "L", "tʃʰ": "CH", "tʃː": "CH", "dʒː": "JH",
    "tS": "CH", "dZ": "JH", "S": "SH",
}
# Non-English realisations of an English target: distortions.
_DISTORTIONS = {
    "s̪": "S", "s̪ː": "S", "t̪": "T", "t̪ː": "T", "r": "R", "ʁ": "R", "ɻ": "R", "ɽ": "R",
    "r̝": "R", "r̩": "R", "ʋ": "V W", "β": "B V", "ɸ": "F", "x": "K HH", "χ": "K HH",
    "ç": "HH SH", "ɣ": "G", "ɕ": "SH", "ʑ": "ZH", "tɕ": "CH", "dʑ": "JH", "ʂ": "SH",
    "ʐ": "ZH", "ʎ": "L Y", "ɲ": "N Y", "ɬ": "L S SH", "c": "K", "ɟ": "G", "ʈ": "T",
    "ɖ": "D", "ɳ": "N", "ɭ": "L", "ɴ": "NG", "q": "K", "ʝ": "Y", "ħ": "HH", "ʕ": "HH",
    "sʲ": "S", "tʲ": "T", "dʲ": "D", "nʲ": "N", "rʲ": "R", "mʲ": "M", "pʲ": "P",
    "kʲ": "K", "bʲ": "B", "vʲ": "V", "fʲ": "F", "ɡʲ": "G", "ɭʲ": "L", "tʃʲ": "CH",
    "dʒʲ": "JH", "ʒʲ": "ZH", "xʲ": "K HH",
}
# Recogniser tokens that stand for more than one English phoneme.
_MULTI = {
    "ts": ["t", "s"], "tsh": ["t", "s"], "ts.": ["t", "s"], "pf": ["p", "f"],
    "əl": ["ə", "l"], "ɑːɹ": ["ɑː", "ɹ"], "ɔːɹ": ["ɔː", "ɹ"], "oːɹ": ["oː", "ɹ"],
    "ɛɹ": ["ɛ", "ɹ"], "ɪɹ": ["ɪ", "ɹ"], "ʊɹ": ["ʊ", "ɹ"], "aɪɚ": ["aɪ", "ɚ"],
    "aɪə": ["aɪ", "ə"], "ju": ["j", "u"], "iə": ["i", "ə"], "ja": ["j", "a"],
    "eə": ["ɛ", "ə"], "ʊə": ["ʊ", "ə"],
}
# Reduced vowels accepted for any unstressed (stress 0) target vowel.
_REDUCED = frozenset({"ə", "ɐ", "ᵻ", "ɪ", "ʊ", "ɚ", "i"})
_VOWEL_CHARS = set("aeiouəɐɪʊɛɔæɑɒʌɜɚyøœɯɨʉɵᵻ")

# Shriberg & Kwiatkowski (1982) severity bands, defined on PCC.
SEVERITY_BANDS = (
    (85.0, "mild"),
    (65.0, "mild-moderate"),
    (50.0, "moderate-severe"),
    (0.0, "severe"),
)

# Dialect variants are scored correct under PCC rules. In non-rhotic accents
# (e.g. Sri Lankan, British English) postvocalic /r/ ("car", "shore") is not pronounced.
ACCEPT_NON_RHOTIC = os.getenv("SPEAKFREE_ACCEPT_NON_RHOTIC", "1") != "0"

ALLOPHONE_COST = 0.0
DISTORTION_COST = 0.25
VOWEL_SUB_COST = 0.6
CONSONANT_SUB_COST = 1.0
CROSS_CLASS_COST = 2.5
GAP_COST = 1.0

WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)*")


@dataclass(frozen=True)
class Produced:
    label: str
    accepted: frozenset
    distortion: bool
    cls: str  # "C" or "V"


@dataclass(frozen=True)
class Target:
    phone: str
    stress: str
    word_index: int
    position: str  # initial / medial / final
    cls: str
    postvocalic_r: bool = False


@lru_cache(maxsize=1)
def _cmudict() -> dict:
    import cmudict
    return cmudict.dict()


def tokenize_words(text: Optional[str]) -> list[str]:
    return WORD_RE.findall((text or "").lower().replace("’", "'"))


def pronounce(word: str) -> Optional[list[str]]:
    prons = _cmudict().get(word.lower())
    return prons[0] if prons else None


def _segment(token: str) -> list[Produced]:
    if token in _MULTI:
        return [seg for part in _MULTI[token] for seg in _segment(part)]
    for table, distortion in ((_EXACT, False), (_ALLOPHONES, False), (_DISTORTIONS, True)):
        if token in table:
            accepted = frozenset(table[token].split())
            cls = "V" if accepted <= VOWELS else "C"
            return [Produced(token, accepted, distortion, cls)]
    cls = "V" if any(ch in _VOWEL_CHARS for ch in token) else "C"
    return [Produced(token, frozenset(), False, cls)]


def segment_produced(tokens: Iterable[str]) -> list[Produced]:
    return [seg for tok in tokens if tok.strip() for seg in _segment(tok.strip())]


def _matches(t: Target, p: Produced) -> bool:
    if t.phone in p.accepted:
        return True
    return t.cls == "V" and t.stress == "0" and p.label in _REDUCED


def _sub_cost(t: Target, p: Produced) -> float:
    if _matches(t, p):
        return DISTORTION_COST if p.distortion else ALLOPHONE_COST
    if t.cls != p.cls:
        return CROSS_CLASS_COST
    return VOWEL_SUB_COST if t.cls == "V" else CONSONANT_SUB_COST


def align(targets: list[Target], produced: list[Produced]):
    """Weighted Levenshtein alignment. Returns (ops, additions).

    ops[i] is (kind, produced_or_None) for target i, kind in
    correct / distortion / substitution / omission.
    """
    n, m = len(targets), len(produced)
    cost = [[0.0] * (m + 1) for _ in range(n + 1)]
    back = [[0] * (m + 1) for _ in range(n + 1)]  # 0 diag, 1 up (omit), 2 left (add)
    for i in range(1, n + 1):
        cost[i][0], back[i][0] = i * GAP_COST, 1
    for j in range(1, m + 1):
        cost[0][j], back[0][j] = j * GAP_COST, 2
    for i in range(1, n + 1):
        t = targets[i - 1]
        row, prev = cost[i], cost[i - 1]
        for j in range(1, m + 1):
            diag = prev[j - 1] + _sub_cost(t, produced[j - 1])
            up = prev[j] + GAP_COST
            left = row[j - 1] + GAP_COST
            if diag <= up and diag <= left:
                row[j], back[i][j] = diag, 0
            elif up <= left:
                row[j], back[i][j] = up, 1
            else:
                row[j], back[i][j] = left, 2

    ops: list = [None] * n
    additions: list[Produced] = []
    i, j = n, m
    while i > 0 or j > 0:
        move = back[i][j]
        if move == 0:
            t, p = targets[i - 1], produced[j - 1]
            if _matches(t, p):
                ops[i - 1] = ("distortion" if p.distortion else "correct", p)
            else:
                ops[i - 1] = ("substitution", p)
            i, j = i - 1, j - 1
        elif move == 1:
            ops[i - 1] = ("omission", None)
            i -= 1
        else:
            additions.append(produced[j - 1])
            j -= 1
    additions.reverse()
    return ops, additions


def severity_band(pcc: float) -> str:
    for lower, label in SEVERITY_BANDS:
        if pcc >= lower:
            return label
    return "severe"


def _pct(num: int, den: int) -> Optional[float]:
    return round(100.0 * num / den, 2) if den else None


def _position(index: int, phones: list[str]) -> str:
    if index == 0:
        return "initial"
    return "final" if index == len(phones) - 1 else "medial"


def score_pcc(
    gloss_words: list[str],
    produced_tokens: list[str],
    unscored_word_indices: Iterable[int] = (),
    gloss_source: str = "target_text",
) -> dict:
    """Score produced phonemes against the intended words.

    Words in `unscored_word_indices` (unintelligible / low-confidence gloss)
    still take part in the alignment but are not counted, as PCC excludes
    words whose intended form is uncertain.
    """
    unscored = set(unscored_word_indices)
    targets: list[Target] = []
    words_info = []
    excluded = []
    for wi, word in enumerate(gloss_words):
        phones = pronounce(word)
        if not phones:
            excluded.append(word)
            words_info.append(None)
            continue
        bare = [re.sub(r"\d", "", ph) for ph in phones]
        start = len(targets)
        for k, (ph, raw) in enumerate(zip(bare, phones)):
            stress = raw[-1] if raw[-1].isdigit() else ""
            cls = "C" if ph in CONSONANTS else "V"
            postvocalic_r = (ph == "R" and k > 0 and bare[k - 1] in VOWELS
                             and (k == len(bare) - 1 or bare[k + 1] not in VOWELS))
            targets.append(Target(ph, stress, wi, _position(k, bare), cls, postvocalic_r))
        words_info.append((start, len(targets)))

    produced = segment_produced(produced_tokens)
    ops, additions = align(targets, produced) if targets else ([], produced)

    tallies = {"correct": 0, "distortion": 0, "substitution": 0, "omission": 0}
    vowels_total = vowels_correct = 0
    consonant_items = []
    word_details = []
    for wi, word in enumerate(gloss_words):
        span = words_info[wi]
        if span is None:
            word_details.append({"index": wi, "word": word, "scored": False,
                                 "reason": "not_in_pronouncing_dictionary"})
            continue
        scored = wi not in unscored
        produced_labels = []
        errors = []
        for ti in range(*span):
            t = targets[ti]
            kind, p = ops[ti]
            if kind == "omission" and t.postvocalic_r and ACCEPT_NON_RHOTIC:
                kind = "correct"
            produced_labels.append(p.label if p else "∅")
            if not scored:
                continue
            if t.cls == "C":
                tallies[kind] += 1
                item = {
                    "word_index": wi, "word": word, "position": t.position,
                    "target": t.phone, "target_ipa": ARPABET_TO_IPA[t.phone],
                    "produced_ipa": p.label if p else None, "automated_result": kind,
                }
                consonant_items.append(item)
                if kind != "correct":
                    errors.append(item)
            else:
                vowels_total += 1
                vowels_correct += kind in ("correct", "distortion")
        word_details.append({
            "index": wi, "word": word, "scored": scored,
            "reason": None if scored else "uncertain_gloss",
            "target_ipa": "".join(ARPABET_TO_IPA[targets[ti].phone] for ti in range(*span)),
            "produced_ipa": " ".join(produced_labels),
            "consonant_errors": [
                {k: e[k] for k in ("position", "target_ipa", "produced_ipa", "automated_result")}
                for e in errors
            ],
        })

    consonants_total = sum(tallies.values())
    pcc = _pct(tallies["correct"], consonants_total)
    pcc_r = _pct(tallies["correct"] + tallies["distortion"], consonants_total)
    phonemes_correct = tallies["correct"] + tallies["distortion"] + vowels_correct
    result = {
        "metric": "Percentage of Consonants Correct (PCC / PCC-R)",
        "references": [
            "Shriberg & Kwiatkowski (1982), J Speech Hear Disord 47(3):256-270, DOI 10.1044/jshd.4703.256",
            "Shriberg et al. (1997), J Speech Lang Hear Res 40(4):708-722, DOI 10.1044/jslhr.4004.708",
        ],
        "gloss_source": gloss_source,
        "pcc": pcc,
        "pcc_r": pcc_r,
        "pvc": _pct(vowels_correct, vowels_total),
        "ppc": _pct(phonemes_correct, consonants_total + vowels_total),
        "severity_band": severity_band(pcc) if pcc is not None else None,
        "severity_band_reference": "Shriberg & Kwiatkowski (1982) PCC bands: mild >=85, "
                                   "mild-moderate 65-<85, moderate-severe 50-<65, severe <50",
        "counts": {
            "target_consonants": consonants_total,
            "correct": tallies["correct"],
            "distortions": tallies["distortion"],
            "substitutions": tallies["substitution"],
            "omissions": tallies["omission"],
            "additions": len(additions),
            "target_vowels": vowels_total,
            "vowels_correct": vowels_correct,
            "words_in_gloss": len(gloss_words),
            "words_scored": sum(1 for w in word_details if w["scored"]),
        },
        "excluded_words": excluded,
        "word_details": word_details,
        "consonant_items": consonant_items,
        "produced_phonemes_ipa": [p.label for p in produced],
    }
    if not consonants_total:
        result["status"] = "no_scorable_consonants"
        result["message"] = ("No target consonants could be scored: the intended words were "
                             "empty, uncertain or not in the pronouncing dictionary.")
    else:
        result["status"] = "scored"
    return result


def word_intelligibility(target_text: Optional[str], transcript: Optional[str]) -> Optional[dict]:
    """Percentage of target words recognised in the ASR transcript (word-level alignment)."""
    target, heard = tokenize_words(target_text), tokenize_words(transcript)
    if not target or transcript is None:
        return None
    n, m = len(target), len(heard)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j - 1] + (target[i - 1] != heard[j - 1]),
                          d[i - 1][j] + 1, d[i][j - 1] + 1)
    i, j, correct = n, m, 0
    while i > 0 and j > 0:
        if d[i][j] == d[i - 1][j - 1] + (target[i - 1] != heard[j - 1]):
            correct += target[i - 1] == heard[j - 1]
            i, j = i - 1, j - 1
        elif d[i][j] == d[i - 1][j] + 1:
            i -= 1
        else:
            j -= 1
    return {
        "measure": "percent of target words correctly recognised by ASR",
        "target_word_count": n,
        "words_correct": correct,
        "word_intelligibility_percent": round(100.0 * correct / n, 2),
        "word_error_rate": round(d[n][m] / n, 4),
    }
