import numpy as np

from app.services.feature_extractor import _librosa_acoustic_features, _fluency_metrics


def test_librosa_acoustic_features_shape():
    sample_rate = 16000
    t = np.linspace(0, 2, sample_rate * 2, endpoint=False)
    tone = 0.1 * np.sin(2 * np.pi * 220 * t).astype(np.float32)

    features = _librosa_acoustic_features(tone, sample_rate)

    assert "zero_crossing_rate_mean" in features
    assert "energy_mean" in features
    assert "tempo_bpm" in features
    assert features["zero_crossing_rate_mean"] >= 0


def test_fluency_metrics_no_words():
    metrics = _fluency_metrics(words=[], duration_seconds=5.0, low_conf_count=0, total_words=0)
    assert metrics["words_per_minute"] == 0
    assert metrics["estimated_dysfluency_density"] == 0


def test_fluency_metrics_with_words():
    words = [{"word": "hi"}, {"word": "there"}]
    metrics = _fluency_metrics(words=words, duration_seconds=6.0, low_conf_count=1, total_words=2)
    assert metrics["words_per_minute"] == 20.0
    assert metrics["estimated_dysfluency_density"] == 0.5
