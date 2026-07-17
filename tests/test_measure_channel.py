import numpy as np
import pytest
from conftest import make_transitions, FakeBackend
from fpaa.measure.backends import EdgeSeries
from fpaa.measure.channel import Channel
from fpaa.measure.calibrate import Calibration
from fpaa.measure.errors import CalibrationMissingError


def _series(pin, freq, duty=0.5, duration=0.2):
    tr = make_transitions(freq, duty=duty, duration_s=duration)
    return EdgeSeries(pins=(pin,), duration_s=duration, backend="fake",
                      transitions={pin: tr})


def test_channel_frequency():
    ch = Channel(chip_id=1, gpio_pin=16, backend=FakeBackend(_series(16, 1000.0)))
    assert abs(ch.frequency(0.2).hz - 1000.0) < 2.0


def test_channel_voltage_uses_calibration():
    cal = Calibration(chip_id=1, duty_slope=-0.16778, duty_intercept=0.5002)
    v = -1.30
    duty = cal.duty_intercept + cal.duty_slope * v
    ch = Channel(1, 16, FakeBackend(_series(16, 1000.0, duty=duty)), calibration=cal)
    assert abs(ch.voltage(0.2) - v) < 0.02


def test_channel_voltage_without_calibration_raises():
    ch = Channel(1, 16, FakeBackend(_series(16, 1000.0)))
    with pytest.raises(CalibrationMissingError):
        ch.voltage(0.2)
