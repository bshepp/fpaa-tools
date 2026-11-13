"""period_stats / ldi_dewarp: the estimator traps they exist to avoid.

Each test reproduces, on synthetic edges, a way a bench result was once wrong.
"""
import math

import numpy as np

from conftest import make_transitions
from fpaa.measure import ldi_dewarp, period_stats


def _from_periods(per_ns):
    """(N,2) transitions with the given rising-to-rising periods, 50% duty."""
    rows, t = [], 0
    for p in per_ns:
        rows += [(t, 1), (t + int(p) // 2, 0)]
        t += int(p)
    rows.append((t, 1))
    return np.array(rows, dtype=np.int64)


def test_clean_square_wave():
    st = period_stats(make_transitions(1000.0, duration_s=0.5))
    assert abs(st.f_mean_hz - 1000.0) < 0.01
    assert abs(st.f_median_hz - 1000.0) < 0.01
    assert st.contamination == 0.0 and st.level_repeats == 0
    assert st.cv_raw < 1e-6 and st.jitter_mad < 1e-6
    assert st.n_clean == st.n_periods > 400


def test_too_few_periods_is_nan_not_a_number():
    st = period_stats(make_transitions(1000.0, duration_s=0.004))
    assert st.n_periods < 8 and math.isnan(st.f_mean_hz)
    assert math.isnan(period_stats(np.empty((0, 2), dtype=np.int64)).f_mean_hz)


def test_chatter_wrecks_raw_cv_but_not_robust_estimators():
    # ~4% spurious ~0.02T periods: the mechanism behind the bogus "27% jitter".
    rng = np.random.default_rng(0)
    per = list(170_000 + rng.normal(0, 170, 2000))      # true jitter 0.1%
    for i in rng.choice(len(per), 80, replace=False):
        per[i] = 3_500                                  # chatter period
    st = period_stats(_from_periods(per))
    assert st.cv_raw > 0.15                             # the old metric: "jitter"
    assert st.jitter_mad < 0.003 and st.cv_clean < 0.003  # the oscillator: quiet
    assert 0.03 < st.frac_short < 0.05 and st.frac_long == 0.0
    assert abs(1 / st.f_mean_hz - 170e-6) / 170e-6 < 1e-3


def test_dropped_edges_show_up_as_long_periods():
    per = [100_000] * 500
    for i in range(10, 500, 50):
        per[i] = 200_000                                # one dropped rise+fall pair
    st = period_stats(_from_periods(per))
    assert st.frac_long == 10 / 500 and st.frac_short == 0.0
    assert abs(st.f_mean_hz - 10_000) < 1e-6            # clean mean is unaffected
    assert st.f_raw_hz < 9_900                          # raw mean is dragged down


def test_level_repeats_counted():
    tr = make_transitions(1000.0, duration_s=0.05)
    tr = np.delete(tr, 11, axis=0)                      # drop one falling edge
    assert period_stats(tr).level_repeats == 1


def test_median_snaps_to_clock_grid_but_mean_does_not():
    # SC oscillator, true period 8.5 clocks of 20 us: periods dither 8 <-> 9
    # clocks. With a 60/40 split the median reads exactly 160 us (wrong); the
    # mean recovers the true average. This is how "-7.6%" got inflated.
    rng = np.random.default_rng(1)
    per = np.where(rng.random(4000) < 0.6, 160_000, 180_000)
    st = period_stats(_from_periods(per))
    assert st.f_median_hz == 1 / 160e-6                 # snapped, bit-identical
    assert abs(1 / st.f_mean_hz - per.mean() * 1e-9) < 1e-12
    assert st.jitter_mad == 0.0                         # quantisation, not quiet
    assert st.cv_clean > 0.05                           # ...the dither is visible here


def test_ldi_dewarp():
    # Round trip against the LDI relation 2*sin(w_meas*T/2) = w_eff*T.
    f_clk, f_eff = 50_000.0, 6000.0
    f_meas = math.asin(math.pi * f_eff / f_clk) * f_clk / math.pi
    assert f_meas > f_eff                               # sampling warps UP
    assert abs(ldi_dewarp(f_meas, f_clk) - f_eff) < 1e-6
    # negligible at high oversampling, NaN past the fold
    assert abs(ldi_dewarp(6000.0, 16e6) - 6000.0) < 0.01
    assert math.isnan(ldi_dewarp(30_000.0, 50_000.0))
