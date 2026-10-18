"""
Noise-robustness evaluation of Component 1 (evidence for the thesis / viva).

    python training/eval_noise_robustness.py --torgo-dir <path>/dataset/torgo            # full run
    python training/eval_noise_robustness.py --torgo-dir <path>/dataset/torgo --quick    # ~5 minutes
    python training/eval_noise_robustness.py --torgo-dir <path>/dataset/torgo --vad-only # VAD only, fast

A fixed, seeded sample of TORGO sentences from healthy and dysarthric speakers is mixed with noise
at several signal-to-noise ratios (SNR). Every version runs through the REAL Component 1 front end:

    preprocess()  (noise reduction ON / OFF, the configured VAD)  ->  Whisper confidence ASR (Eq. 1-3)

Reported per noise type and SNR:
  * WER against the TORGO prompt             - does the ASR still understand the speech?
  * C_overall (Eq. 3) for each group         - how far does the biomarker drift with noise?
  * AUC of (100 - C_overall), dysarthric vs healthy, with a bootstrap 95 % CI
                                             - does the biomarker still separate the groups?
  * speech detected (VAD found speech at all)
  * VAD frame F1 for Silero vs the energy VAD against a clean-audio reference
    (frames where both VADs agree on the clean recording; disagreeing frames are not scored)

Outputs go to training/results/noise_robustness_<timestamp>/:
  per_utterance.csv, vad.csv, summary.json, summary.md (tables for the thesis), *.png plots

TORGO is used for EVALUATION ONLY (nothing is trained). Audio is read from the dataset folder and
is never copied into the app. Noise: white, pink and babble are generated from a fixed seed (babble
= 6 overlapping TORGO talkers who are not in the evaluation sample); --noise-dir adds real noise
recordings (e.g. MUSAN / DEMAND .wav files) as type "file".
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import warnings
import zlib
from datetime import datetime
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from audio_preprocessing import SAMPLE_RATE, energy_vad, preprocess, silero_vad  # noqa: E402
from config import settings  # noqa: E402

FRAME = 0.01  # VAD scoring resolution (10 ms)


# --------------------------------------------------------------------------- audio + text
def load_wav(path: Path) -> np.ndarray:
    import librosa
    import soundfile as sf

    y, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if sr != SAMPLE_RATE:
        y = librosa.resample(y, orig_sr=sr, target_sr=SAMPLE_RATE)
    return y.astype(np.float32)


def normalise(text: str) -> list[str]:
    return re.sub(r"[^a-z' ]+", " ", str(text).lower()).split()


def wer(reference: str, hypothesis: str) -> float:
    """Word error rate = (substitutions + deletions + insertions) / reference words."""
    ref, hyp = normalise(reference), normalise(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    d = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        prev, d[0] = d[0], i
        for j, h in enumerate(hyp, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (r != h))
    return d[len(hyp)] / len(ref)


# --------------------------------------------------------------------------- noise
def white_noise(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.normal(0, 1, n).astype(np.float32)


def pink_noise(n: int, rng: np.random.Generator) -> np.ndarray:
    spectrum = np.fft.rfft(rng.normal(0, 1, n))
    f = np.arange(spectrum.size)
    f[0] = 1
    return np.fft.irfft(spectrum / np.sqrt(f), n).astype(np.float32)


def babble_noise(n: int, rng: np.random.Generator, pool: list[np.ndarray], talkers: int = 6) -> np.ndarray:
    out = np.zeros(n, np.float32)
    for k in rng.choice(len(pool), size=min(talkers, len(pool)), replace=False):
        clip = pool[k] / (np.sqrt(np.mean(pool[k] ** 2)) + 1e-9)
        clip = np.tile(clip, int(np.ceil(n / clip.size)) + 1)
        start = int(rng.integers(0, clip.size - n))
        out += clip[start:start + n]
    return out


def file_noise(n: int, rng: np.random.Generator, files: list[np.ndarray]) -> np.ndarray:
    clip = files[int(rng.integers(0, len(files)))]
    clip = np.tile(clip, int(np.ceil(n / clip.size)) + 1)
    start = int(rng.integers(0, clip.size - n))
    return clip[start:start + n].astype(np.float32)


def mix(clean: np.ndarray, noise: np.ndarray, snr_db: float) -> np.ndarray:
    """Scale the noise to the requested SNR (speech power / noise power), then avoid clipping."""
    p_s = float(np.mean(clean ** 2)) + 1e-12
    p_n = float(np.mean(noise ** 2)) + 1e-12
    noisy = clean + noise * np.sqrt(p_s / (p_n * 10 ** (snr_db / 10)))
    peak = float(np.max(np.abs(noisy)))
    return (noisy / peak * 0.95 if peak > 1 else noisy).astype(np.float32)


# --------------------------------------------------------------------------- sampling
def sample_utterances(meta, audio_dir: Path, per_group: int, min_words: int, seed: int):
    """Seeded, speaker-balanced sample per group (healthy / dysarthria) + a babble pool of other healthy talkers."""
    rng = np.random.default_rng(seed)
    meta = meta[meta["transcription"].astype(str).str.split().str.len() >= min_words]
    meta = meta[[(audio_dir / p).is_file() for p in meta["audio_path"]]]
    picked = []
    for status, group in meta.groupby("speech_status"):
        speakers = sorted(group["speaker_id"].unique())
        queues = {s: list(rng.permutation(group[group["speaker_id"] == s].index)) for s in speakers}
        chosen = []
        while len(chosen) < per_group and any(queues.values()):
            for s in speakers:
                if queues[s] and len(chosen) < per_group:
                    chosen.append(queues[s].pop())
        picked.append(meta.loc[chosen])
    import pandas as pd

    sample = pd.concat(picked)
    rest = meta[(meta["speech_status"] == "healthy") & ~meta.index.isin(sample.index)]
    babble = rest.sample(n=min(40, len(rest)), random_state=seed)
    return sample, babble


# --------------------------------------------------------------------------- VAD scoring
def to_frames(intervals: list[tuple[float, float]], n_frames: int) -> np.ndarray:
    mask = np.zeros(n_frames, bool)
    for s, e in intervals:
        mask[int(s / FRAME):int(np.ceil(e / FRAME))] = True
    return mask


def vad_f1(pred: np.ndarray, ref: np.ndarray, scored: np.ndarray) -> float:
    p, r = pred[scored], ref[scored]
    tp = int(np.sum(p & r))
    fp, fn = int(np.sum(p & ~r)), int(np.sum(~p & r))
    return 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 1.0


# --------------------------------------------------------------------------- statistics
def auc_with_ci(labels: np.ndarray, scores: np.ndarray, seed: int, boots: int = 500) -> tuple[float | None, float | None, float | None]:
    from sklearn.metrics import roc_auc_score

    if len(set(labels)) < 2:
        return None, None, None
    auc = float(roc_auc_score(labels, scores))
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(boots):
        idx = rng.integers(0, len(labels), len(labels))
        if len(set(labels[idx])) == 2:
            samples.append(roc_auc_score(labels[idx], scores[idx]))
    lo, hi = np.percentile(samples, [2.5, 97.5])
    return round(auc, 3), round(float(lo), 3), round(float(hi), 3)


# --------------------------------------------------------------------------- main
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--torgo-dir", required=True, help="folder with TORGO metadata.csv and audio/")
    ap.add_argument("--per-group", type=int, default=30, help="utterances per group (healthy / dysarthria)")
    ap.add_argument("--min-words", type=int, default=3, help="only sentences with at least this many words")
    ap.add_argument("--snrs", default="clean,20,10,5,0", help="comma list; 'clean' = no added noise")
    ap.add_argument("--noise", default="babble,white", help="comma list of white, pink, babble, file")
    ap.add_argument("--noise-dir", help="folder of real noise .wav files (enables --noise file)")
    ap.add_argument("--whisper-model", default=settings.whisper_model)
    ap.add_argument("--vad", default=settings.vad_backend, choices=["silero", "energy"], help="VAD used before Whisper")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true", help="8 per group, babble only, SNR clean/10/0")
    ap.add_argument("--vad-only", action="store_true", help="skip Whisper: VAD comparison only")
    ap.add_argument("--out", default=str(BACKEND / "training" / "results"))
    args = ap.parse_args()
    if args.quick:
        args.per_group, args.noise, args.snrs = 8, "babble", "clean,10,0"
    return args


def main() -> None:
    import pandas as pd

    args = parse_args()
    torgo = Path(args.torgo_dir)
    audio_dir = torgo / "audio"
    snrs = [None if s.strip() == "clean" else float(s) for s in args.snrs.split(",")]
    noise_types = [n.strip() for n in args.noise.split(",")]
    out = Path(args.out) / f"noise_robustness_{datetime.now():%Y%m%d_%H%M%S}"
    out.mkdir(parents=True, exist_ok=True)

    meta = pd.read_csv(torgo / "metadata.csv")
    sample, babble_rows = sample_utterances(meta, audio_dir, args.per_group, args.min_words, args.seed)
    print(f"Sample: {len(sample)} utterances from {sample['speaker_id'].nunique()} speakers "
          f"({sample['speech_status'].value_counts().to_dict()})")
    clean_audio = {i: load_wav(audio_dir / r.audio_path) for i, r in sample.iterrows()}
    babble_pool = [load_wav(audio_dir / p) for p in babble_rows["audio_path"]]
    noise_files = [load_wav(p) for p in sorted(Path(args.noise_dir).glob("*.wav"))] if args.noise_dir else []
    if "file" in noise_types and not noise_files:
        sys.exit("--noise file needs --noise-dir with .wav files")

    def make_noise(kind: str, n: int, key: str) -> np.ndarray:
        rng = np.random.default_rng(zlib.crc32(f"{args.seed}:{key}".encode()))
        return {"white": lambda: white_noise(n, rng), "pink": lambda: pink_noise(n, rng),
                "babble": lambda: babble_noise(n, rng, babble_pool), "file": lambda: file_noise(n, rng, noise_files)}[kind]()

    conditions = [("clean", None)] + [(k, s) for k in noise_types for s in snrs if s is not None]
    conditions = conditions if None in snrs else conditions[1:]

    # ---- VAD comparison (fast, no Whisper) ----
    vad_rows = []
    for i, r in sample.iterrows():
        y = clean_audio[i]
        n_frames = int(np.ceil(y.size / SAMPLE_RATE / FRAME)) + 1
        ref_s, ref_e = to_frames(silero_vad(y)[0], n_frames), to_frames(energy_vad(y)[0], n_frames)
        scored = ref_s == ref_e  # consensus reference: frames both VADs agree on in the clean recording
        for kind, snr in conditions:
            a = y if snr is None else mix(y, make_noise(kind, y.size, f"{i}:{kind}:{snr}"), snr)
            for name, fn in (("silero", silero_vad), ("energy", energy_vad)):
                pred = to_frames(fn(a)[0], n_frames)
                vad_rows.append({"utt": i, "group": r.speech_status, "noise": kind, "snr": "clean" if snr is None else snr,
                                 "vad": name, "f1": round(vad_f1(pred, ref_s, scored), 4), "speech_found": bool(pred.any())})
    vad = pd.DataFrame(vad_rows)
    vad.to_csv(out / "vad.csv", index=False)
    vad_summary = (vad.groupby(["noise", "snr", "vad"], sort=False)
                   .agg(f1=("f1", "mean"), speech_found=("speech_found", "mean")).round(3).reset_index())
    print("\nVAD frame F1 (consensus clean reference):\n" + vad_summary.to_string(index=False))

    summary: dict = {
        "config": {"dataset": "TORGO (evaluation only)", "utterances": len(sample), "speakers": int(sample["speaker_id"].nunique()),
                   "per_group": args.per_group, "min_words": args.min_words, "snrs_db": args.snrs, "noise": noise_types,
                   "whisper_model": args.whisper_model, "vad": args.vad, "seed": args.seed,
                   "dysfluency_threshold": settings.dysfluency_threshold, "run_at": datetime.now().isoformat(timespec="seconds")},
        "vad": vad_summary.to_dict(orient="records"),
    }

    # ---- Whisper confidence ASR (Eq. 1-3) with noise reduction on / off ----
    rows = []
    if not args.vad_only:
        from asr_service import WhisperConfidenceASR

        asr = WhisperConfidenceASR(args.whisper_model, settings.whisper_device, settings.verbatim_prompt,
                                   settings.dysfluency_threshold, settings.no_speech_threshold, settings.max_words_per_sec)
        total = len(sample) * len(conditions) * 2
        done, t0 = 0, time.perf_counter()
        for i, r in sample.iterrows():
            y = clean_audio[i]
            for kind, snr in conditions:
                a = y if snr is None else mix(y, make_noise(kind, y.size, f"{i}:{kind}:{snr}"), snr)
                for nr in (True, False):
                    pre = preprocess(a, enable_noise_reduction=nr, vad_backend=args.vad)
                    row = {"utt": i, "speaker": r.speaker_id, "group": r.speech_status, "reference": r.transcription,
                           "noise": kind, "snr": "clean" if snr is None else snr, "noise_reduction": nr,
                           "speech_detected": bool(pre.speech_intervals)}
                    if pre.speech_intervals and pre.clean_audio.size >= 0.3 * SAMPLE_RATE:
                        tr = asr.transcribe(pre.clean_audio, time_offset=pre.trim_offset_sec, sample_rate=SAMPLE_RATE)
                        flags = [w.is_dysfluency_candidate for w in tr.words]
                        row |= {"hypothesis": tr.transcript, "wer": round(min(wer(r.transcription, tr.transcript), 2.0), 4),
                                "confidence": round(tr.overall_confidence_percent, 2),
                                "dysfluency_ratio": round(float(np.mean(flags)), 4) if flags else None}
                    else:  # the app would ask the user to record again
                        row |= {"hypothesis": "", "wer": 1.0, "confidence": 0.0, "dysfluency_ratio": None}
                    rows.append(row)
                    done += 1
                    if done % 20 == 0 or done == total:
                        eta = (time.perf_counter() - t0) / done * (total - done)
                        print(f"  {done}/{total} transcriptions · ~{eta / 60:.1f} min left", flush=True)

        res = pd.DataFrame(rows)
        res.to_csv(out / "per_utterance.csv", index=False)
        table = []
        for (kind, snr, nr), g in res.groupby(["noise", "snr", "noise_reduction"], sort=False):
            healthy, dys = g[g.group == "healthy"], g[g.group == "dysarthria"]
            auc, lo, hi = auc_with_ci((g.group == "dysarthria").to_numpy().astype(int),
                                      (100 - g.confidence).to_numpy(), args.seed)
            table.append({"noise": kind, "snr": snr, "noise_reduction": bool(nr),
                          "speech_detected": round(g.speech_detected.mean(), 3),
                          "wer_healthy": round(healthy.wer.mean(), 3), "wer_dysarthria": round(dys.wer.mean(), 3),
                          "conf_healthy": round(healthy.confidence.mean(), 1), "conf_dysarthria": round(dys.confidence.mean(), 1),
                          "auc": auc, "auc_ci95": [lo, hi]})
        summary["asr"] = table
        asr_df = pd.DataFrame(table)
        print("\nWhisper confidence ASR:\n" + asr_df.to_string(index=False))
        plot(asr_df, vad_summary, out)
    else:
        plot(None, vad_summary, out)

    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    write_markdown(summary, out)
    print(f"\nResults saved to {out}")


# --------------------------------------------------------------------------- reporting
def snr_axis(values) -> tuple[list[str], list[float]]:
    """'clean' is drawn at the right-hand end (highest SNR)."""
    labels = [str(v) for v in values]
    xs = [40.0 if v == "clean" else float(v) for v in values]
    return labels, xs


def plot(asr_df, vad_summary, out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def per_noise(df, fn, title, ylabel, name, ylim=None):
        fig, ax = plt.subplots(figsize=(6.4, 4))
        for kind in [k for k in df["noise"].unique() if k != "clean"] or ["clean"]:
            part = pd_concat_clean(df, kind)
            fn(ax, part, kind)
        ax.set_title(title)
        ax.set_xlabel("SNR (dB)  ·  rightmost point = clean")
        ax.set_ylabel(ylabel)
        if ylim:
            ax.set_ylim(*ylim)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out / name, dpi=150)
        plt.close(fig)

    def pd_concat_clean(df, kind):
        import pandas as pd

        return pd.concat([df[df["noise"] == "clean"], df[df["noise"] == kind]]) if kind != "clean" else df

    def draw_vad(ax, part, kind):
        for v in ("silero", "energy"):
            p = part[part.vad == v]
            _, xs = snr_axis(p.snr)
            order = np.argsort(xs)
            ax.plot(np.array(xs)[order], p.f1.to_numpy()[order], marker="o", label=f"{v} · {kind}")

    per_noise(vad_summary, draw_vad, "Voice activity detection in noise", "frame F1", "vad_f1_vs_snr.png", (0, 1.02))
    if asr_df is None:
        return

    def draw(metric_pairs):
        def fn(ax, part, kind):
            for nr in (True, False):
                p = part[part.noise_reduction == nr]
                _, xs = snr_axis(p.snr)
                order = np.argsort(xs)
                for col, lbl in metric_pairs:
                    ax.plot(np.array(xs)[order], p[col].to_numpy()[order], marker="o",
                            linestyle="-" if nr else "--", label=f"{lbl} · NR {'on' if nr else 'off'} · {kind}")
        return fn

    per_noise(asr_df, draw([("wer_healthy", "healthy"), ("wer_dysarthria", "dysarthria")]),
              "Word error rate vs noise", "WER", "wer_vs_snr.png")
    per_noise(asr_df, draw([("conf_healthy", "healthy"), ("conf_dysarthria", "dysarthria")]),
              "ASR confidence C_overall (Eq. 3) vs noise", "C_overall (%)", "confidence_vs_snr.png", (0, 100))
    per_noise(asr_df, draw([("auc", "AUC dysarthria vs healthy")]),
              "Biomarker separation vs noise", "AUC", "auc_vs_snr.png", (0.4, 1.0))


def write_markdown(summary: dict, out: Path) -> None:
    c = summary["config"]
    lines = [
        "# Component 1 – noise-robustness evaluation", "",
        f"TORGO (evaluation only) · {c['utterances']} utterances from {c['speakers']} speakers "
        f"({c['per_group']} healthy + {c['per_group']} dysarthric, sentences of ≥ {c['min_words']} words) · "
        f"noise {', '.join(c['noise'])} · SNR {c['snrs_db']} dB · Whisper `{c['whisper_model']}` · VAD `{c['vad']}` · seed {c['seed']}.",
        "", "## Voice activity detection (frame F1 vs a consensus clean reference)", "",
        "| Noise | SNR (dB) | VAD | F1 | Speech found |", "|---|---|---|---|---|",
    ]
    lines += [f"| {v['noise']} | {v['snr']} | {v['vad']} | {v['f1']:.3f} | {v['speech_found']:.0%} |" for v in summary["vad"]]
    if summary.get("asr"):
        lines += ["", "## Whisper confidence ASR (Eq. 1–3)", "",
                  "AUC = how well (100 − C_overall) separates dysarthric from healthy speech (0.5 = chance, 1 = perfect).", "",
                  "| Noise | SNR (dB) | Noise reduction | Speech detected | WER healthy | WER dysarthric | C_overall healthy | C_overall dysarthric | AUC [95 % CI] |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for a in summary["asr"]:
            ci = f"[{a['auc_ci95'][0]}, {a['auc_ci95'][1]}]" if a["auc"] is not None else ""
            lines.append(f"| {a['noise']} | {a['snr']} | {'on' if a['noise_reduction'] else 'off'} | {a['speech_detected']:.0%} | "
                         f"{a['wer_healthy']:.3f} | {a['wer_dysarthria']:.3f} | {a['conf_healthy']} | {a['conf_dysarthria']} | "
                         f"{a['auc']} {ci} |")
    lines += ["", "Plots: `vad_f1_vs_snr.png`, `wer_vs_snr.png`, `confidence_vs_snr.png`, `auc_vs_snr.png`. "
              "Per-utterance data: `per_utterance.csv`, `vad.csv`."]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
