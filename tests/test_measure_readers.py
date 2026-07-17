import numpy as np
import pytest
from conftest import make_transitions
from fpaa.measure.readers import frequency, duty, periods
from fpaa.measure.errors import NoEdgesError


def _legacy_duty_from_events(evs):
    """Inlined copy of b1_amplitude_readback.duty_from_events (the readback
    path being consolidated), used only to prove value parity here."""
    high_ns = 0
    total_ns = 0
    last_rise = None
    prev_rise = None
    for kind, ts in evs:
        if kind == 1:
            if prev_rise is not None:
                total_ns += ts - prev_rise
            prev_rise = ts
            last_rise = ts
        else:
            if last_rise is not None:
                high_ns += ts - last_rise
                last_rise = None
    return high_ns / total_ns


def test_duty_matches_legacy_duty_from_events():
    # Fixture ending on a closing rising edge (whole complete periods): the
    # legacy algorithm and the fixed duty() agree exactly here, and both recover
    # the true 40% duty. rise,fall,rise,fall,rise = 2 complete periods.
    tr = np.array([[0, 1], [400, 0], [1000, 1], [1400, 0], [2000, 1]], dtype=np.int64)
    evs = [(int(lv), int(ts)) for ts, lv in tr]
    assert abs(duty(tr).duty - _legacy_duty_from_events(evs)) < 1e-9
    assert abs(duty(tr).duty - 0.4) < 1e-9


def test_duty_unbiased_when_series_ends_on_fall():
    # Regression for the N/(N-1) bias: 5 high pulses ending on a falling edge
    # (dangling high). duty() must recover the true 40% (the legacy code would
    # report ~0.5 here because it counts the dangling high segment).
    rows = []
    for k in range(5):
        rows.append([k * 1000, 1])
        rows.append([k * 1000 + 400, 0])
    tr = np.array(rows, dtype=np.int64)  # ends on fall at 4400
    assert abs(duty(tr).duty - 0.4) < 1e-9


def test_frequency_recovers_1khz():
    tr = make_transitions(1000.0, duty=0.5, duration_s=0.5)
    f = frequency(tr, 0.5)
    assert abs(f.hz - 1000.0) < 1.0
    assert f.rising_edges >= 400


def test_duty_recovers_30_percent():
    tr = make_transitions(500.0, duty=0.30, duration_s=0.2)
    d = duty(tr)
    assert abs(d.duty - 0.30) < 0.02
    assert abs(d.freq_hz - 500.0) < 2.0


def test_periods_are_one_millisecond():
    tr = make_transitions(1000.0, duty=0.5, duration_s=0.2)
    p = periods(tr)
    assert len(p) >= 150
    assert abs(np.median(p) - 1e6) < 1e3  # 1 ms in ns


def test_duty_raises_on_empty():
    with pytest.raises(NoEdgesError):
        duty(np.empty((0, 2), dtype=np.int64))
