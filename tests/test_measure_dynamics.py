import numpy as np, pytest
from fpaa.measure.dynamics import (
    crossing_intervals, return_map, symbol_divergence, first_divergence_index,
    power_spectrum, spectral_flatness)

def test_crossing_intervals_basic():
    t = np.array([0.0, 1.0, 3.0, 6.0])
    assert np.allclose(crossing_intervals(t), [1.0, 2.0, 3.0])

def test_crossing_intervals_rejects_short_and_nonmonotonic():
    with pytest.raises(ValueError): crossing_intervals([1.0])
    with pytest.raises(ValueError): crossing_intervals([0.0, 0.0, 1.0])

def test_return_map_pairs():
    x, y = return_map([1.0, 2.0, 3.0, 4.0])
    assert np.allclose(x, [1.0, 2.0, 3.0]) and np.allclose(y, [2.0, 3.0, 4.0])

def test_symbol_divergence_identical_is_zero():
    s = np.array([1, -1, 1, 1, -1])
    assert np.all(symbol_divergence(s, s) == 0)

def test_symbol_divergence_grows_after_split():
    a = np.array([1, 1, 1, 1, 1]); b = np.array([1, 1, -1, -1, -1])
    # agree at 0,1; differ at 2,3,4 -> cumulative 0,0,1,2,3
    assert np.array_equal(symbol_divergence(a, b), [0, 0, 1, 2, 3])

def test_first_divergence_index():
    assert first_divergence_index([1,1,1], [1,1,1]) == -1
    assert first_divergence_index([1,1,-1,1], [1,1,1,1]) == 2

def test_power_spectrum_peaks_at_tone():
    fs = 10000.0; n = 4096
    t = np.arange(n) / fs
    x = np.sin(2*np.pi*1000.0*t)
    f, p = power_spectrum(x, fs)
    assert f[np.argmax(p)] == pytest.approx(1000.0, abs=fs/n*2)
    assert len(f) == n//2 + 1

def test_spectral_flatness_tone_low_noise_high():
    fs = 10000.0; n = 4096
    t = np.arange(n) / fs
    tone = np.sin(2*np.pi*1000.0*t)
    _, pt = power_spectrum(tone, fs)
    flat_tone = spectral_flatness(pt)
    rng = np.random.default_rng(0)
    noise = rng.standard_normal(n)
    _, pn = power_spectrum(noise, fs)
    flat_noise = spectral_flatness(pn)
    assert flat_tone < 0.1          # a pure line is very peaky
    assert flat_noise > 0.4         # white noise is broadband
    assert flat_noise > 10 * flat_tone
