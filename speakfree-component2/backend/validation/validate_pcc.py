"""Validate the automated PCC against therapist judgements.

Two input modes:

1. Scoring sheets (recommended). One CSV per recording, downloaded from the
   Component 2 UI ("Therapist scoring sheet"). The therapist fills
   `therapist_result` for every target consonant with correct / distortion /
   substitution / omission (or C / D / S / O). A second therapist may fill
   `therapist2_result` on some sheets: their agreement is the benchmark the
   automated system is compared against.

       python -m validation.validate_pcc sheets/*.csv

2. Summary. One CSV with columns recording_id, automated_pcc, therapist_pcc
   (e.g. when the therapist did an independent narrow transcription).

       python -m validation.validate_pcc --summary results.csv

Reported statistics
-------------------
* Point-by-point consonant agreement (% and Cohen's kappa), as used for PCC
  reliability (Shriberg et al., 1997).
* Recording-level ICC(2,1), absolute agreement, single rater (Shrout & Fleiss,
  1979), interpreted with Koo & Li (2016): <0.50 poor, 0.50-0.75 moderate,
  0.75-0.90 good, >0.90 excellent. 95% CI by bootstrap.
* Bland-Altman bias and 95% limits of agreement, mean absolute error,
  Pearson and Spearman correlation.
* Severity-band agreement (Shriberg & Kwiatkowski, 1982 bands) with linearly
  weighted kappa.
"""
import argparse
import csv
import glob
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.metrics import cohen_kappa_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.pcc_scoring import SEVERITY_BANDS, severity_band  # noqa: E402

RESULT_CODES = {"c": "correct", "d": "distortion", "s": "substitution", "o": "omission"}
CATEGORIES = ("correct", "distortion", "substitution", "omission")
BAND_ORDER = [label for _, label in SEVERITY_BANDS]


def normalise(value: str):
    v = (value or "").strip().lower()
    if not v:
        return None
    v = RESULT_CODES.get(v, v)
    if v not in CATEGORIES:
        raise ValueError(f"Unknown result '{value}'. Use correct/distortion/substitution/omission or C/D/S/O.")
    return v


def pcc(results, count_distortions_correct=False):
    ok = {"correct", "distortion"} if count_distortions_correct else {"correct"}
    return 100.0 * sum(r in ok for r in results) / len(results) if results else None


def icc_2_1(a: np.ndarray, b: np.ndarray) -> float:
    """Two-way random effects, absolute agreement, single rater (Shrout & Fleiss ICC(2,1))."""
    x = np.column_stack([a, b])
    n, k = x.shape
    grand = x.mean()
    ms_rows = k * ((x.mean(axis=1) - grand) ** 2).sum() / (n - 1)
    ms_cols = n * ((x.mean(axis=0) - grand) ** 2).sum() / (k - 1)
    ss_err = ((x - x.mean(axis=1, keepdims=True) - x.mean(axis=0, keepdims=True) + grand) ** 2).sum()
    ms_err = ss_err / ((n - 1) * (k - 1))
    denom = ms_rows + (k - 1) * ms_err + k * (ms_cols - ms_err) / n
    return float((ms_rows - ms_err) / denom) if denom else float("nan")


def icc_bootstrap_ci(a, b, reps=2000, seed=0):
    rng = np.random.default_rng(seed)
    n = len(a)
    vals = []
    for _ in range(reps):
        idx = rng.integers(0, n, n)
        v = icc_2_1(a[idx], b[idx])
        if np.isfinite(v):
            vals.append(v)
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))) if vals else (None, None)


def koo_li(icc):
    if icc is None or not np.isfinite(icc):
        return "not computable"
    if icc < 0.5:
        return "poor"
    if icc < 0.75:
        return "moderate"
    if icc < 0.9:
        return "good"
    return "excellent"


def recording_level(auto: list, ther: list) -> dict:
    a, t = np.asarray(auto, float), np.asarray(ther, float)
    n = len(a)
    out = {"recordings": n}
    if n < 3:
        out["note"] = "At least 3 recordings are needed for recording-level statistics (30+ recommended)."
        return out
    diff = a - t
    icc = icc_2_1(a, t)
    lo, hi = icc_bootstrap_ci(a, t)
    bands_a = [BAND_ORDER.index(severity_band(v)) for v in a]
    bands_t = [BAND_ORDER.index(severity_band(v)) for v in t]
    band_kappa = (cohen_kappa_score(bands_a, bands_t, weights="linear")
                  if len(set(bands_a) | set(bands_t)) > 1 else None)
    out.update({
        "icc_2_1_absolute_agreement": round(icc, 3),
        "icc_95ci_bootstrap": [round(lo, 3), round(hi, 3)] if lo is not None else None,
        "icc_interpretation_koo_li_2016": koo_li(icc),
        "bland_altman_bias_auto_minus_therapist": round(float(diff.mean()), 2),
        "bland_altman_limits_of_agreement": [round(float(diff.mean() - 1.96 * diff.std(ddof=1)), 2),
                                             round(float(diff.mean() + 1.96 * diff.std(ddof=1)), 2)],
        "mean_absolute_error": round(float(np.abs(diff).mean()), 2),
        "pearson_r": round(float(stats.pearsonr(a, t)[0]), 3),
        "spearman_rho": round(float(stats.spearmanr(a, t)[0]), 3),
        "severity_band_exact_agreement_percent": round(100.0 * np.mean(np.equal(bands_a, bands_t)), 1),
        "severity_band_weighted_kappa": round(float(band_kappa), 3) if band_kappa is not None else None,
    })
    return out


def point_by_point(x: list, y: list) -> dict:
    binary_x = [r == "correct" for r in x]
    binary_y = [r == "correct" for r in y]
    agree = sum(p == q for p, q in zip(binary_x, binary_y))
    kappa = cohen_kappa_score(binary_x, binary_y) if len(set(binary_x) | set(binary_y)) > 1 else None
    confusion = Counter(zip(x, y))
    return {
        "consonants_compared": len(x),
        "agreement_percent_correct_vs_error": round(100.0 * agree / len(x), 2) if x else None,
        "cohen_kappa_correct_vs_error": round(float(kappa), 3) if kappa is not None else None,
        "agreement_percent_four_categories": round(100.0 * sum(p == q for p, q in zip(x, y)) / len(x), 2)
        if x else None,
        "confusion_rows_first_columns_second": {
            f"{p}->{q}": n for (p, q), n in sorted(confusion.items())
        },
    }


def from_sheets(paths: list[str]) -> dict:
    per_rec = defaultdict(lambda: {"auto": [], "t1": [], "t2_pairs": []})
    pooled_auto, pooled_t1, t1_pairs, t2_pairs = [], [], [], []
    for path in paths:
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                rec = row.get("recording_id") or Path(path).stem
                auto = normalise(row.get("automated_result"))
                t1 = normalise(row.get("therapist_result"))
                t2 = normalise(row.get("therapist2_result"))
                if auto is None or t1 is None:
                    continue
                per_rec[rec]["auto"].append(auto)
                per_rec[rec]["t1"].append(t1)
                pooled_auto.append(auto)
                pooled_t1.append(t1)
                if t2 is not None:
                    per_rec[rec]["t2_pairs"].append((t1, t2))
                    t1_pairs.append(t1)
                    t2_pairs.append(t2)
    if not pooled_auto:
        raise SystemExit("No rows with both automated_result and therapist_result were found.")

    recordings = []
    for rec, d in sorted(per_rec.items()):
        recordings.append({
            "recording_id": rec,
            "consonants": len(d["auto"]),
            "automated_pcc": round(pcc(d["auto"]), 2),
            "therapist_pcc": round(pcc(d["t1"]), 2),
            "automated_pcc_r": round(pcc(d["auto"], True), 2),
            "therapist_pcc_r": round(pcc(d["t1"], True), 2),
        })
    report = {
        "automated_vs_therapist_point_by_point": point_by_point(pooled_auto, pooled_t1),
        "automated_vs_therapist_pcc": recording_level(
            [r["automated_pcc"] for r in recordings], [r["therapist_pcc"] for r in recordings]),
        "automated_vs_therapist_pcc_r": recording_level(
            [r["automated_pcc_r"] for r in recordings], [r["therapist_pcc_r"] for r in recordings]),
        "recordings": recordings,
    }
    if t2_pairs:
        report["therapist_vs_therapist2_point_by_point_benchmark"] = point_by_point(t1_pairs, t2_pairs)
    return report


def from_summary(path: str) -> dict:
    auto, ther = [], []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("automated_pcc") and row.get("therapist_pcc"):
                auto.append(float(row["automated_pcc"]))
                ther.append(float(row["therapist_pcc"]))
    return {"automated_vs_therapist_pcc": recording_level(auto, ther)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sheets", nargs="*", help="Therapist scoring sheet CSV files (globs allowed)")
    parser.add_argument("--summary", help="CSV with recording_id, automated_pcc, therapist_pcc")
    parser.add_argument("--out", help="Write the report as JSON to this path")
    args = parser.parse_args(argv)
    if args.summary:
        report = from_summary(args.summary)
    else:
        paths = [p for pattern in args.sheets for p in glob.glob(pattern)]
        if not paths:
            parser.error("Give scoring sheet CSV files or --summary.")
        report = from_sheets(paths)
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
