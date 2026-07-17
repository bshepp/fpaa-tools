import numpy as np
from fpaa.measure.analysis import (allan_deviation, separation, snr_at,
                                    corr_coef, timing_stats)


def test_corr_coef_zero_variance_is_zero():
    assert corr_coef(np.ones(100), np.arange(100)) == 0.0


def test_corr_coef_perfect():
    x = np.arange(100.0)
    assert abs(corr_coef(x, 2 * x + 1) - 1.0) < 1e-9


def test_snr_at_finds_tone():
    fs = 1000.0
    t = np.arange(5000) / fs
    x = np.sin(2 * np.pi * 50 * t) + 0.01 * np.random.default_rng(0).standard_normal(len(t))
    assert snr_at(x, 50.0, fs) > 100.0
    assert snr_at(x, 137.0, fs) < snr_at(x, 50.0, fs)


def test_separation_of_disjoint_groups():
    low = np.array([0.0, 0.1, -0.1])
    high = np.array([5.0, 5.1, 4.9])
    assert separation(low, high) > 10.0


def test_allan_shrinks_for_white_noise():
    rng = np.random.default_rng(1)
    periods = 1e6 + rng.normal(0, 1e3, 20000)  # ~1 ms periods, white jitter
    ad = allan_deviation(periods, [1, 10, 100])
    assert ad["10"] < ad["1"]  # white noise: adev falls with averaging


def test_timing_stats_keys():
    s = timing_stats([1.0, 2.0, 3.0, 4.0])
    assert s["n"] == 4 and s["min"] == 1.0 and s["max"] == 4.0
    assert abs(s["mean"] - 2.5) < 1e-9


def test_snr_at_flat_series_is_zero():
    assert snr_at(np.zeros(1000), 50.0, 1000.0) == 0.0
