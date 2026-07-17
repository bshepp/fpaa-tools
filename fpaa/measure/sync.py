"""Phase & synchronization metrics for sign-crossing (comparator) readouts.

Pure numpy. A continuous-time comparator on an oscillator's state emits one edge
per half cycle, so N crossing times define phase 0, pi, 2pi, ... . These helpers
turn crossing times into phase and quantify phase locking between two oscillators
(Teramae-Tanaka / Nagai-Nakao common-noise-synchronization metrics).
"""
import numpy as np


def interp_phase(edge_times, grid):
    """Monotonic phase (radians) on `grid` from sign-crossing `edge_times`.

    Phase advances pi per crossing; values are linearly interpolated and clamped
    to the endpoints outside the observed span.
    """
    edge_times = np.asarray(edge_times, dtype=float)
    grid = np.asarray(grid, dtype=float)
    if edge_times.size < 2:
        raise ValueError("need >= 2 edges to define phase")
    if np.any(np.diff(edge_times) <= 0):
        raise ValueError("edge_times must be strictly increasing")
    phase_at_edges = np.arange(edge_times.size) * np.pi
    return np.interp(grid, edge_times, phase_at_edges)


def phase_locking_value(phase_a, phase_b):
    """|<exp(i*(phase_a - phase_b))>| in [0,1]; 1 = constant phase difference."""
    phase_a = np.asarray(phase_a, dtype=float)
    phase_b = np.asarray(phase_b, dtype=float)
    if phase_a.shape != phase_b.shape:
        raise ValueError("phase arrays must have the same shape")
    if phase_a.size == 0:
        raise ValueError("empty phase array")
    return float(np.abs(np.mean(np.exp(1j * (phase_a - phase_b)))))


def phase_diff_lyapunov(psi, dt):
    """Contraction rate of a phase-difference series toward its asymptote.

    Fits log|psi - psi[-1]| ~ lambda * t over the leading 80% of samples.
    Negative => the phase difference is contracting (synchronizing). Returns 0.0
    for a flat series.
    """
    psi = np.asarray(psi, dtype=float)
    if psi.size < 3:
        raise ValueError("need >= 3 samples")
    dev = np.abs(psi - psi[-1])
    n = psi.size
    lead = slice(0, max(2, int(n * 0.8)))
    d = dev[lead]
    mask = d > 1e-9 * (dev.max() + 1e-30)
    if mask.sum() < 2:
        return 0.0
    t = (np.arange(n)[lead])[mask] * dt
    slope = np.polyfit(t, np.log(d[mask]), 1)[0]
    return float(slope)


def synchronization(edge_a, edge_b, n=4096):
    """PLV between two sign-crossing edge trains over their overlapping span."""
    edge_a = np.asarray(edge_a, dtype=float)
    edge_b = np.asarray(edge_b, dtype=float)
    lo = max(edge_a[0], edge_b[0])
    hi = min(edge_a[-1], edge_b[-1])
    if hi <= lo:
        raise ValueError("no overlapping time span")
    grid = np.linspace(lo, hi, n)
    return phase_locking_value(interp_phase(edge_a, grid), interp_phase(edge_b, grid))
