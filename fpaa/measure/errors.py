"""Typed, self-describing errors for fpaa.measure (AI-first: an agent can
branch on the exact failure)."""


class MeasureError(Exception):
    """Base class for all fpaa.measure errors."""


class BackendUnavailableError(MeasureError):
    """A GPIO backend's underlying library (RPi.GPIO / gpiod) is not importable."""


class NoEdgesError(MeasureError):
    """No usable transitions were captured (dead channel or too-short window)."""


class LowSwingError(MeasureError):
    """Signal swing is below the clean-counting threshold for this channel."""


class CalibrationMissingError(MeasureError):
    """A voltage read was requested on a channel with no calibration."""
