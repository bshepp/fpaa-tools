"""Entropy / randomness statistics for TRNG characterization.

Bit sequences are numpy arrays of 0/1 (any nonzero counts as 1). Pure numpy +
stdlib math, host-testable. Extraction helpers (von Neumann, XOR-fold) and NIST-
style tests (monobit, runs) plus Shannon / min-entropy and autocorrelation.
"""
from math import erfc, sqrt

import numpy as np


def _bits(x):
    return (np.asarray(x).ravel() != 0).astype(np.int8)


def bias(bits):
    """Empirical P(1)."""
    b = _bits(bits)
    return float(b.mean()) if b.size else 0.0


def shannon_entropy(bits):
    """Per-bit Shannon entropy (bits/bit) from the empirical 0/1 frequencies."""
    p = bias(bits)
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return float(-p * np.log2(p) - (1 - p) * np.log2(1 - p))


def min_entropy(bits):
    """Per-bit min-entropy = -log2(max(p, 1-p)) from the empirical bias."""
    p = bias(bits)
    m = max(p, 1.0 - p)
    return float(-np.log2(m)) if 0.0 < m < 1.0 else 0.0


def monobit(bits):
    """NIST monobit frequency test. dict: n, ones, fraction, z, p_value."""
    b = _bits(bits)
    n = int(b.size)
    ones = int(b.sum())
    if n == 0:
        return {"n": 0, "ones": 0, "fraction": 0.0, "z": 0.0, "p_value": 0.0}
    z = abs(2 * ones - n) / sqrt(n)
    return {"n": n, "ones": ones, "fraction": ones / n,
            "z": float(z), "p_value": float(erfc(z / sqrt(2)))}


def runs_test(bits):
    """NIST runs test. dict: n, runs, expected, z, p_value (needs monobit prereq)."""
    b = _bits(bits)
    n = int(b.size)
    if n < 2:
        return {"n": n, "runs": None, "p_value": 0.0, "note": "too short"}
    pi = float(b.mean())
    if abs(pi - 0.5) >= 2.0 / sqrt(n):
        return {"n": n, "runs": None, "p_value": 0.0, "note": "monobit prereq failed"}
    runs = 1 + int(np.count_nonzero(b[1:] != b[:-1]))
    expected = 2.0 * n * pi * (1.0 - pi)
    z = abs(runs - expected) / (2.0 * sqrt(2.0 * n) * pi * (1.0 - pi))
    return {"n": n, "runs": runs, "expected": expected,
            "z": float(z), "p_value": float(erfc(z / sqrt(2)))}


def autocorrelation(bits, maxlag=32):
    """Normalized autocorrelation at lags 0..maxlag (list; lag 0 == 1.0)."""
    b = _bits(bits).astype(np.float64)
    b = b - b.mean()
    v = float(np.dot(b, b))
    if v == 0.0:
        return [0.0] * (maxlag + 1)
    return [1.0] + [float(np.dot(b[:-k], b[k:]) / v) for k in range(1, maxlag + 1)]


def von_neumann(bits):
    """Von Neumann debiasing: (0,1)->0, (1,0)->1, (0,0)/(1,1)->discard.
    Removes bias from independent bits (at the cost of ~75%+ of them)."""
    b = _bits(bits)
    n = b.size - (b.size % 2)
    if n == 0:
        return np.empty(0, dtype=np.int8)
    pairs = b[:n].reshape(-1, 2)
    unequal = pairs[:, 0] != pairs[:, 1]
    return pairs[unequal, 0].astype(np.int8)


def xor_fold(bits, k):
    """XOR non-overlapping groups of k bits into one output bit each."""
    if k < 1:
        raise ValueError("k must be >= 1")
    b = _bits(bits)
    n = b.size - (b.size % k)
    if n == 0:
        return np.empty(0, dtype=np.int8)
    return np.bitwise_xor.reduce(b[:n].reshape(-1, k), axis=1).astype(np.int8)


def xor_streams(*streams):
    """XOR N aligned bit streams elementwise into one (truncates to shortest).

    Combines independent physical sources -- a classic non-crypto combiner: by
    the piling-up lemma the per-bit bias goes bias -> bias**N and independent
    periodic components decorrelate. Requires >= 1 stream; returns int8 0/1.
    """
    if not streams:
        raise ValueError("need at least one stream")
    arrs = [_bits(s) for s in streams]
    n = min(a.size for a in arrs)
    if n == 0:
        return np.empty(0, dtype=np.int8)
    stacked = np.stack([a[:n] for a in arrs])
    return np.bitwise_xor.reduce(stacked, axis=0).astype(np.int8)


def pack_bytes(bits):
    """Pack a 0/1 bit array into bytes (drops a trailing partial byte)."""
    b = _bits(bits)
    n = b.size - (b.size % 8)
    if n == 0:
        return b""
    return np.packbits(b[:n]).tobytes()
