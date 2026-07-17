"""Signal/statistics helpers for readback and the SR metric.

allan_deviation is the analyze_b2 estimator; snr_at and corr_coef are the
stochastic-resonance metrics; separation and timing_stats are reused by
NN/09 and config-timing work respectively.
"""
import numpy as np


def allan_deviation(periods_ns, taus_in_periods):
    """Allan deviation of fractional frequency (non-overlapping m-sample bins; tau in period counts)."""
    periods_ns = np.asarray(periods_ns, dtype=np.float64)
    y = 1.0 / periods_ns
    y = (y - y.mean()) / y.mean()
    out = {}
    for m in taus_in_periods:
        if len(y) < 3 * m:
            continue
        n = len(y) // m
        yb = y[: n * m].reshape(n, m).mean(axis=1)
        d = np.diff(yb)
        out[str(m)] = float(np.sqrt(0.5 * np.mean(d ** 2)))
    return out


def corr_coef(a, b):
    """Pearson correlation; 0.0 if either input has zero variance."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.std() == 0 or b.std() == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def snr_at(series, f, fs):
    """Spectral power at frequency f divided by median off-band power."""
    x = np.asarray(series, dtype=np.float64)
    x = x - x.mean()
    if not np.any(x):          # flat/dead capture: no tone, no meaningful SNR
        return 0.0
    n = len(x)
    spec = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(n, 1.0 / fs)
    k = int(np.argmin(np.abs(freqs - f)))
    mask = np.ones(len(spec), dtype=bool)
    mask[0] = False
    lo, hi = max(1, k - 2), min(len(spec), k + 3)
    mask[lo:hi] = False
    noise = np.median(spec[mask]) if mask.any() else 0.0
    if noise <= 0:
        return float("inf")
    return float(spec[k] / noise)


def separation(low, high):
    """Two-sided separation: difference of means in sum-of-stds units (std_low + std_high)."""
    low = np.asarray(low, dtype=np.float64)
    high = np.asarray(high, dtype=np.float64)
    denom = low.std() + high.std()
    if denom == 0:
        return float("inf") if high.mean() != low.mean() else 0.0
    return float((high.mean() - low.mean()) / denom)


def timing_stats(durations_ms):
    """Summary stats for a list of durations in ms (from a1 measure_timing)."""
    a = np.asarray(durations_ms, dtype=np.float64)
    return {
        "n": int(a.size),
        "min": float(a.min()),
        "mean": float(a.mean()),
        "median": float(np.median(a)),
        "p95": float(np.percentile(a, 95)),
        "max": float(a.max()),
    }
