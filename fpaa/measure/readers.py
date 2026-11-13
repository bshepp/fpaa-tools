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


@dataclass
class PeriodStats:
    """Robust rising-to-rising period statistics, with readout-fault accounting.

    "Clean" periods are those within [0.5, 1.5] x the median. Shorter ones are
    comparator chatter (extra edges); longer ones are dropped edges. Both are
    READOUT faults and are reported as fractions instead of being absorbed
    into a spread figure.
    """
    n_periods: int = 0                 # all rising-to-rising periods
    n_clean: int = 0
    f_mean_hz: float = float("nan")    # 1 / mean(clean)   -- use this for frequency
    f_median_hz: float = float("nan")  # 1 / median(clean) -- snaps on clocked sources
    f_raw_hz: float = float("nan")     # 1 / mean(all)
    cv_raw: float = float("nan")       # std/mean over ALL periods (fragile)
    cv_clean: float = float("nan")     # std/mean over clean periods
    jitter_mad: float = float("nan")   # 1.4826*MAD/median over clean periods
    frac_short: float = float("nan")
    frac_long: float = float("nan")
    min_over_med: float = float("nan")
    level_repeats: int = 0             # consecutive same-level events (dropped edges)

    @property
    def contamination(self) -> float:
        return self.frac_short + self.frac_long


def period_stats(trans: np.ndarray, min_periods: int = 8) -> PeriodStats:
    """Robust period statistics from an (N,2) [timestamp_ns, level] array.

    Two estimator traps this exists to avoid (both cost real bench results):

    * ``std/mean`` over all periods is defenceless against spurious edges: a
      few percent of chatter periods reads as tens of percent "jitter". Use
      ``jitter_mad`` (or ``cv_clean``) and check ``contamination``.
    * On a clocked (switched-capacitor) source the period is an integer number
      of clock cycles, so the MEDIAN snaps to that grid and reports a
      bit-identical, wrong frequency. ``f_mean_hz`` averages the dither and
      does not snap. Note ``jitter_mad`` is 0 when >50% of periods share one
      grid value -- that is quantisation, not a quiet oscillator.

    Fields stay NaN when fewer than ``min_periods`` periods (or clean periods)
    are available.
    """
    st = PeriodStats()
    if trans.ndim != 2 or trans.shape[0] < 2:
        return st
    st.level_repeats = int(np.count_nonzero(np.diff(trans[:, 1]) == 0))
    per = periods(trans) / 1e9
    st.n_periods = int(per.size)
    if per.size < min_periods:
        return st
    med = float(np.median(per))
    if not np.isfinite(med) or med <= 0:
        return st
    st.frac_short = float(np.mean(per < 0.5 * med))
    st.frac_long = float(np.mean(per > 1.5 * med))
    st.min_over_med = float(per.min() / med)
    st.f_raw_hz = float(1.0 / per.mean())
    st.cv_raw = float(per.std() / per.mean())
    clean = per[(per > 0.5 * med) & (per < 1.5 * med)]
    st.n_clean = int(clean.size)
    if clean.size >= min_periods:
        cmed = float(np.median(clean))
        st.f_mean_hz = float(1.0 / clean.mean())
        st.f_median_hz = 1.0 / cmed
        st.cv_clean = float(clean.std() / clean.mean())
        st.jitter_mad = float(np.median(np.abs(clean - cmed))) * 1.4826 / cmed
    return st


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
