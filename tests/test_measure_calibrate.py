import json
import numpy as np
from fpaa.measure.calibrate import (Calibration, calibrate_channel,
                                     load_calibration, save_calibration)


def test_voltage_inverts_c0_constants():
    cal = Calibration(chip_id=1, duty_slope=-0.16778, duty_intercept=0.5002)
    # C0: duty = intercept + slope*V  -> V = (duty - intercept)/slope
    v = -1.30
    duty = cal.duty_intercept + cal.duty_slope * v
    assert abs(cal.voltage(duty) - v) < 1e-6


def test_calibrate_channel_recovers_line():
    volts = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    duties = 0.5 + (-0.1) * volts
    slope, intercept = calibrate_channel(duties, volts)
    assert abs(slope - (-0.1)) < 1e-9
    assert abs(intercept - 0.5) < 1e-9


def test_roundtrip_json(tmp_path):
    cal = Calibration(chip_id=3, duty_slope=-0.15, duty_intercept=0.49,
                      comparator_offset_v=-0.019, date="2026-07-04")
    save_calibration(cal, tmp_path)
    back = load_calibration(3, tmp_path)
    assert back.duty_slope == -0.15
    assert back.comparator_offset_v == -0.019


def test_seed_chip1_loads_from_package():
    cal = load_calibration(1)  # default package calibration/ dir
    assert cal.chip_id == 1
    assert abs(cal.duty_slope - (-0.16778)) < 1e-9
