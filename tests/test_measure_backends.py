import sys

import numpy as np
import pytest
from conftest import make_transitions
from fpaa.measure.backends import PollBackend, GpiodBackend, EdgeSeries
from fpaa.measure.errors import BackendUnavailableError


def test_make_transitions_shape():
    tr = make_transitions(1000.0, duty=0.5, duration_s=0.01)
    assert tr.ndim == 2 and tr.shape[1] == 2
    assert tr.dtype == np.int64
    # first transition is a rising edge
    assert tr[0, 1] == 1
    # levels strictly alternate
    assert set(np.unique(tr[:, 1])) <= {0, 1}
    assert np.all(np.diff(tr[:, 1]) != 0)
    # ~10 periods in 10 ms at 1 kHz -> ~20 transitions
    assert 18 <= len(tr) <= 22


class _FakeGPIO:
    """Minimal RPi.GPIO stand-in whose input() toggles every call."""
    BCM = "BCM"
    IN = "IN"

    def __init__(self):
        self._state = {}
        self.cleaned = None

    def setmode(self, m):
        pass

    def setup(self, pin, mode):
        self._state.setdefault(pin, 0)

    def input(self, pin):
        self._state[pin] ^= 1
        return self._state[pin]

    def cleanup(self, pins=None):
        self.cleaned = pins


def test_pollbackend_records_transitions():
    fake = _FakeGPIO()
    be = PollBackend(gpio_module=fake)
    s = be.capture_edges([16], duration_s=0.005)
    assert isinstance(s, EdgeSeries)
    tr = s.pin(16)
    assert tr.ndim == 2 and tr.shape[1] == 2
    # a toggling input yields many alternating transitions
    assert len(tr) > 10
    assert np.all(np.diff(tr[:, 1]) != 0)
    # the backend releases the lines it claimed (so gpiod can reuse them)
    assert fake.cleaned == [16]


def test_pollbackend_missing_lib_raises(monkeypatch):
    # Force the import to fail even on a Pi where RPi.GPIO exists:
    # a None entry in sys.modules makes `import RPi.GPIO` raise ImportError.
    monkeypatch.setitem(sys.modules, "RPi", None)
    monkeypatch.setitem(sys.modules, "RPi.GPIO", None)
    be = PollBackend()  # no injected module
    with pytest.raises(BackendUnavailableError):
        be.capture_edges([16], duration_s=0.001)


def test_gpiodbackend_missing_lib_raises(monkeypatch):
    monkeypatch.setitem(sys.modules, "gpiod", None)
    be = GpiodBackend()  # no injected module
    with pytest.raises(BackendUnavailableError):
        be.capture_edges([16], duration_s=0.001)
