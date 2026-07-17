"""Edge-capture backends and their shared output type.

Hardware libraries are imported lazily inside methods so this module imports
on a plain host with only numpy present.
"""
from dataclasses import dataclass
from typing import Dict, Protocol, Sequence, Tuple

import numpy as np

from .errors import BackendUnavailableError


@dataclass
class EdgeSeries:
    """Captured transitions for one or more pins.

    transitions[pin] is an (N,2) int64 array of rows [timestamp_ns, level],
    each row a genuine transition (level in {0,1}), in time order.
    """
    pins: Tuple[int, ...]
    duration_s: float
    backend: str
    transitions: Dict[int, np.ndarray]

    def pin(self, p: int) -> np.ndarray:
        return self.transitions[p]


class EdgeCaptureBackend(Protocol):
    name: str

    def capture_edges(self, pins: Sequence[int],
                      duration_s: float) -> EdgeSeries:
        ...


import time


class PollBackend:
    """Busy-poll edge capture via RPi.GPIO (consolidates a2/b0 pollers).

    ~305 kS/s single-pin; records a transition row whenever a pin's level
    changes. gpio_module is injectable for tests.
    """
    name = "poll"

    def __init__(self, gpio_module=None):
        self._gpio = gpio_module

    def _mod(self):
        if self._gpio is not None:
            return self._gpio
        try:
            import RPi.GPIO as G
        except ImportError as e:
            raise BackendUnavailableError("RPi.GPIO not importable") from e
        G.setmode(G.BCM)
        return G

    def capture_edges(self, pins, duration_s):
        G = self._mod()
        pins = list(pins)
        rows = {p: [] for p in pins}
        for p in pins:
            G.setup(p, G.IN)
        try:
            read = G.input
            perf = time.perf_counter_ns
            last = {p: read(p) for p in pins}
            deadline = perf() + int(duration_s * 1e9)
            while perf() < deadline:
                now = perf()
                for p in pins:
                    lv = read(p)
                    if lv != last[p]:
                        rows[p].append((now, lv))
                        last[p] = lv
        finally:
            # Release the lines so a later GpiodBackend (or reuse) can claim
            # them — RPi.GPIO otherwise holds them for the process lifetime,
            # which blocks gpiod with "Device or resource busy".
            G.cleanup(pins)
        trans = {p: np.array(rows[p], dtype=np.int64).reshape(-1, 2) for p in pins}
        return EdgeSeries(tuple(pins), duration_s, self.name, trans)


class GpiodBackend:
    """Kernel-timestamped BOTH-edge capture via libgpiod v2 (consolidates
    b1 capture_events / b2 / c0 measure_v). All pins in one request."""
    name = "gpiod"

    def __init__(self, chip_dev="/dev/gpiochip0", gpiod_module=None):
        self.chip_dev = chip_dev
        self._gpiod = gpiod_module

    def _mod(self):
        if self._gpiod is not None:
            return self._gpiod
        try:
            import gpiod
            return gpiod
        except ImportError as e:
            raise BackendUnavailableError("gpiod (libgpiod v2) not importable") from e

    def capture_edges(self, pins, duration_s):
        gpiod = self._mod()
        from gpiod.line import Edge
        from gpiod.edge_event import EdgeEvent
        pins = list(pins)
        settings = gpiod.LineSettings(edge_detection=Edge.BOTH)
        config = {p: settings for p in pins}
        rows = {p: [] for p in pins}
        with gpiod.request_lines(self.chip_dev, consumer="fpaa-measure",
                                 config=config) as req:
            t_end = time.monotonic() + duration_s
            while True:
                remaining = t_end - time.monotonic()
                if remaining <= 0:
                    break
                if req.wait_edge_events(timeout=min(0.5, remaining)):
                    for ev in req.read_edge_events():
                        lv = 1 if ev.event_type == EdgeEvent.Type.RISING_EDGE else 0
                        rows[ev.line_offset].append((ev.timestamp_ns, lv))
        trans = {p: np.array(rows[p], dtype=np.int64).reshape(-1, 2) for p in pins}
        return EdgeSeries(tuple(pins), duration_s, self.name, trans)
