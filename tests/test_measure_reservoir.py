import numpy as np
from fpaa.measure import reservoir as R
from fpaa.measure.calibrate import Calibration
from fpaa.measure.errors import NoEdgesError


def test_participation_ratio_identical_nodes_is_one():
    # all nodes the same signal -> 1 effective dimension
    col = np.random.RandomState(0).randn(500)
    states = np.column_stack([col, col, col, col])
    assert abs(R.participation_ratio(states) - 1.0) < 0.05


def test_participation_ratio_orthogonal_equal_variance_is_n():
    rng = np.random.RandomState(1)
    states = rng.randn(2000, 4)   # ~independent, equal variance
    assert R.participation_ratio(states) > 3.5   # near 4


def test_participation_ratio_bounded():
    rng = np.random.RandomState(2)
    states = rng.randn(1000, 5)
    pr = R.participation_ratio(states)
    assert 1.0 <= pr <= 5.0 + 1e-9


def test_pairwise_corr_identical_is_one():
    col = np.random.RandomState(3).randn(400)
    states = np.column_stack([col, col, col])
    s = R.pairwise_corr_summary(states)
    assert s["n_pairs"] == 3            # C(3,2)
    assert s["mean_abs"] > 0.99 and s["max_abs"] > 0.99


def test_pairwise_corr_independent_is_low():
    rng = np.random.RandomState(4)
    states = rng.randn(5000, 3)
    s = R.pairwise_corr_summary(states)
    assert s["mean_abs"] < 0.1


def test_responsiveness_high_when_driven_varies():
    rng = np.random.RandomState(5)
    driven = rng.randn(1000, 3) * np.array([5.0, 5.0, 0.01])  # nodes 0,1 move; 2 flat
    baseline = rng.randn(1000, 3) * 0.01                      # all near-flat at rest
    r = R.responsiveness(driven, baseline)
    assert r[0] > 10 and r[1] > 10       # responsive
    assert r[2] < 5                      # node 2 not responsive


def test_responsiveness_handles_zero_baseline():
    driven = np.ones((10, 2)) * np.array([1.0, 0.0])
    baseline = np.zeros((10, 2))
    r = R.responsiveness(driven, baseline)   # must not divide by zero / NaN
    assert np.all(np.isfinite(r))


def _square(period_ns, high_ns, n):
    """Build an EdgeSeries (M,2) [ts, level] for n periods of a square wave."""
    rows = []
    t = 0
    for _ in range(n):
        rows.append([t, 1]); rows.append([t + high_ns, 0])
        t += period_ns
    rows.append([t, 1])   # closing rise so the last period is complete
    return np.array(rows, dtype=np.int64)


def test_decode_state_maps_duty_to_voltage():
    # calibration duty = 0.5 + 0.1*V  ->  V = (duty-0.5)/0.1
    cal = Calibration(chip_id=1, duty_slope=0.1, duty_intercept=0.5)
    ch0 = _square(1000, 700, 20)   # duty 0.7 -> V = 2.0
    ch1 = _square(1000, 500, 20)   # duty 0.5 -> V = 0.0
    v = R.decode_state([ch0, ch1], [cal, cal])
    assert abs(v[0] - 2.0) < 1e-6
    assert abs(v[1] - 0.0) < 1e-6


def test_decode_state_nan_on_no_edges():
    cal = Calibration(chip_id=1, duty_slope=0.1, duty_intercept=0.5)
    empty = np.empty((0, 2), dtype=np.int64)
    v = R.decode_state([empty], [cal])
    assert np.isnan(v[0])
