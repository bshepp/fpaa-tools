import numpy as np
import pytest
from fpaa.measure.sync import (
    interp_phase, phase_locking_value, phase_diff_lyapunov, synchronization,
)


def test_interp_phase_midpoints():
    ph = interp_phase([0.0, 1.0, 2.0, 3.0], [0.5, 1.5, 2.5])
    np.testing.assert_allclose(ph, [np.pi / 2, 3 * np.pi / 2, 5 * np.pi / 2])


def test_interp_phase_rejects_non_increasing():
    with pytest.raises(ValueError):
        interp_phase([0.0, 1.0, 1.0], [0.5])


def test_interp_phase_needs_two_edges():
    with pytest.raises(ValueError):
        interp_phase([0.0], [0.0])


def test_plv_locked_including_constant_offset():
    a = np.linspace(0, 100 * np.pi, 1000)
    assert phase_locking_value(a, a) == pytest.approx(1.0)
    assert phase_locking_value(a, a + np.pi) == pytest.approx(1.0)  # constant offset = still locked


def test_plv_drifting_is_low():
    a = np.linspace(0, 100 * np.pi, 1000)
    b = a + np.linspace(0, 40 * np.pi, 1000)  # steadily growing phase difference
    assert phase_locking_value(a, b) < 0.2


def test_plv_shape_mismatch_raises():
    with pytest.raises(ValueError):
        phase_locking_value(np.zeros(3), np.zeros(4))


def test_lyapunov_recovers_exponential_decay():
    t = np.arange(0, 5, 0.005)
    psi = 0.5 * np.exp(-2.0 * t) + 1.3
    assert phase_diff_lyapunov(psi, dt=0.005) == pytest.approx(-2.0, abs=0.1)


def test_lyapunov_constant_is_zero():
    assert phase_diff_lyapunov(np.full(500, 0.7), dt=0.01) == 0.0


def test_synchronization_locked_sources():
    a = np.arange(0, 100, 0.5)   # crossings every 0.5 s (period 1.0 s)
    b = a + 0.1                  # constant time offset -> phase-locked
    assert synchronization(a, b) == pytest.approx(1.0, abs=0.02)
