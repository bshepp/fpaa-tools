"""Turn EdgeSeries transition arrays into physical quantities.

Consolidates measure_freq/measure_duty/measure_periods (b0), measure_frequency
(a2), and duty_from_events (b1) / measure_v (c0) into one transition-based API.
"""
from dataclasses import dataclass

import numpy as np

from .errors import NoEdgesError


@dataclass
class Freq:
    hz: float
    rising_edges: int


@dataclass
class Duty:
    duty: float       # high fraction over whole periods, 0..1
    freq_hz: float
    n_transitions: int


def _rising_ts(trans: np.ndarray) -> np.ndarray:
    if trans.size == 0:
        return np.empty(0, dtype=np.int64)
    return trans[trans[:, 1] == 1, 0]


def frequency(trans: np.ndarray, duration_s=None) -> Freq:
    """Frequency from rising-edge timestamps (period-based when >=2 rises)."""
    r = _rising_ts(trans)
    if len(r) >= 2:
        hz = (len(r) - 1) / ((r[-1] - r[0]) / 1e9)
    elif duration_s:
        hz = len(r) / duration_s
    else:
        hz = 0.0
    return Freq(hz=float(hz), rising_edges=int(len(r)))


def periods(trans: np.ndarray) -> np.ndarray:
    """Consecutive rising-to-rising periods, in nanoseconds (float64)."""
    r = _rising_ts(trans)
    return np.diff(r).astype(np.float64)


def duty(trans: np.ndarray) -> Duty:
    """Duty cycle and frequency over whole periods.

    High-time is counted only over periods that are closed by a subsequent
    rising edge, so the high-time and period-time sums span the same complete
    periods. This removes the N/(N-1) boundary bias that appears when a capture
    ends on a falling edge (a dangling high segment whose period never closes).
    """
    high_ns = 0.0
    total_ns = 0.0
    prev_rise = None
    last_rise = None
    pending_high = None   # high-time since the last rise, once its fall is seen
    n_periods = 0
    for ts, lv in trans:
        if lv == 1:  # rising edge closes the previous period
            if prev_rise is not None:
                total_ns += ts - prev_rise
                n_periods += 1
                if pending_high is not None:
                    high_ns += pending_high
            prev_rise = ts
            last_rise = ts
            pending_high = None
        else:  # falling edge
            if last_rise is not None:
                pending_high = ts - last_rise
                last_rise = None
    if total_ns <= 0:
        raise NoEdgesError("no complete high-low-high period in transitions")
    return Duty(duty=float(high_ns / total_ns),
                freq_hz=float(n_periods / (total_ns / 1e9)),
                n_transitions=int(len(trans)))
