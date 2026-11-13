"""fpaa.measure — read-only, AI-first readback for the AN231E04 PIKA rig.

Pure-logic modules (readers, analysis, calibrate, channel) import with only
numpy present; GPIO backends import their hardware libs lazily.
"""
from .errors import (MeasureError, BackendUnavailableError, NoEdgesError,
                     LowSwingError, CalibrationMissingError)
from .backends import EdgeSeries, EdgeCaptureBackend, PollBackend, GpiodBackend
from .readers import (Freq, Duty, PeriodStats, frequency, duty, periods,
                      period_stats)
from .analysis import (allan_deviation, separation, snr_at, corr_coef,
                       timing_stats, ldi_dewarp)
from .calibrate import (Calibration, calibrate_channel, load_calibration,
                        save_calibration)
from .channel import Channel
from . import entropy
from . import reservoir

__all__ = [
    "MeasureError", "BackendUnavailableError", "NoEdgesError",
    "LowSwingError", "CalibrationMissingError",
    "EdgeSeries", "EdgeCaptureBackend", "PollBackend", "GpiodBackend",
    "Freq", "Duty", "PeriodStats", "frequency", "duty", "periods",
    "period_stats", "ldi_dewarp",
    "allan_deviation", "separation", "snr_at", "corr_coef", "timing_stats",
    "Calibration", "calibrate_channel", "load_calibration", "save_calibration",
    "Channel", "entropy", "reservoir",
]
