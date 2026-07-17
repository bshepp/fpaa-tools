import numpy as np
import pytest


def make_transitions(freq_hz, duty=0.5, duration_s=1.0, t0_ns=0,
                     jitter_ns=0, seed=0):
    """Build an (N,2) int64 transition array [ts_ns, level] for a square wave.

    Starts with a rising edge (level 1) at t0_ns. Alternates 1,0,1,0...
    `duty` is the high fraction of each period. Optional Gaussian jitter (ns)
    is added to each edge timestamp (seeded).
    """
    period_ns = 1e9 / freq_hz
    high_ns = period_ns * duty
    rng = np.random.default_rng(seed)
    rows = []
    t = float(t0_ns)
    end = t0_ns + duration_s * 1e9
    level = 1
    while t < end:
        jit = rng.normal(0, jitter_ns) if jitter_ns else 0.0
        rows.append((int(t + jit), level))
        if level == 1:
            t += high_ns
        else:
            t += period_ns - high_ns
        level ^= 1
    return np.array(rows, dtype=np.int64).reshape(-1, 2)


class FakeBackend:
    """EdgeCaptureBackend returning a prebuilt EdgeSeries (for tests)."""
    name = "fake"

    def __init__(self, series):
        self._series = series

    def capture_edges(self, pins, duration_s):
        return self._series


@pytest.fixture
def transitions_1khz():
    return make_transitions(1000.0, duty=0.5, duration_s=0.1)
