import fpaa
from fpaa import measure


def test_version_bumped():
    assert fpaa.__version__ == "0.5.2"


def test_public_surface_present():
    for name in ["EdgeSeries", "Channel", "PollBackend", "GpiodBackend",
                 "frequency", "duty", "periods", "snr_at", "corr_coef",
                 "allan_deviation", "Calibration", "load_calibration"]:
        assert hasattr(measure, name), name
