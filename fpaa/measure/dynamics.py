"""Chaos-signature analysis for #4.2 analog dynamical systems.

Pure, host-testable helpers that turn a captured digital time series (a
comparator square wave sampled on the Pi GPIO) into chaos signatures. No
hardware imports.
"""
from __future__ import annotations
import numpy as np

def crossing_intervals(edge_times):
    t = np.asarray(edge_times, dtype=float)
    if t.ndim != 1 or t.size < 2:
        raise ValueError("need >= 2 edge times")
    d = np.diff(t)
    if np.any(d <= 0):
        raise ValueError("edge times must be strictly increasing")
    return d

def return_map(intervals):
    v = np.asarray(intervals, dtype=float)
    if v.size < 2:
        raise ValueError("need >= 2 intervals")
    return v[:-1], v[1:]

def symbol_divergence(seq_a, seq_b):
    a = np.asarray(seq_a); b = np.asarray(seq_b)
    n = min(a.size, b.size)
    if n == 0:
        raise ValueError("empty sequence")
    return np.cumsum((a[:n] != b[:n]).astype(int))

def first_divergence_index(seq_a, seq_b):
    a = np.asarray(seq_a); b = np.asarray(seq_b)
    n = min(a.size, b.size)
    ne = np.nonzero(a[:n] != b[:n])[0]
    return int(ne[0]) if ne.size else -1

def power_spectrum(signal, fs, detrend=True):
    """One-sided Hann-windowed power spectral density.

    Args:
        signal: time-domain samples
        fs: sampling frequency (Hz)
        detrend: subtract mean if True (default: True)

    Returns:
        (freqs, psd) where freqs is in Hz (len N//2+1) and psd is power
    """
    x = np.asarray(signal, dtype=float)
    if x.ndim != 1 or x.size < 2:
        raise ValueError("need >= 2 samples")
    if detrend:
        x = x - x.mean()
    n = x.size
    X = np.fft.rfft(x * np.hanning(n))
    psd = (np.abs(X) ** 2) / n
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    return freqs, psd

def spectral_flatness(psd, eps=1e-20):
    """Wiener spectral flatness: geometric-mean / arithmetic-mean.

    Args:
        psd: power spectral density (positive values)
        eps: floor threshold to exclude near-zero bins (default: 1e-20)

    Returns:
        flatness in (0,1]: ~1 broadband, ~0 tonal
    """
    p = np.asarray(psd, dtype=float)
    p = p[p > eps]
    if p.size == 0:
        raise ValueError("no positive PSD bins")
    return float(np.exp(np.mean(np.log(p))) / np.mean(p))
