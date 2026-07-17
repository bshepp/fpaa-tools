"""Per-die duty<->voltage calibration, promoted from c0's hardcoded constants
and b1's per-die comparator offsets into a stored, repeatable model."""
import json
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

from .errors import CalibrationMissingError

_PKG_CAL_DIR = Path(__file__).parent / "calibration"


@dataclass
class Calibration:
    chip_id: int
    duty_slope: float          # duty = duty_intercept + duty_slope * V
    duty_intercept: float
    comparator_offset_v: float = 0.0
    clean_swing_v: float = 2.2
    overcount_below_v: float = 1.4
    dead_below_v: float = 0.6
    date: str = ""

    def voltage(self, duty: float) -> float:
        return (duty - self.duty_intercept) / self.duty_slope

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


def calibrate_channel(duties, voltages):
    """Least-squares fit duty = intercept + slope*V. Returns (slope, intercept)."""
    v = np.asarray(voltages, dtype=np.float64)
    d = np.asarray(duties, dtype=np.float64)
    slope, intercept = np.polyfit(v, d, 1)
    return float(slope), float(intercept)


def save_calibration(cal: Calibration, dir_path=None):
    dir_path = Path(dir_path) if dir_path else _PKG_CAL_DIR
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / f"chip{cal.chip_id}.json"
    path.write_text(json.dumps(cal.to_dict(), indent=2))
    return path


def load_calibration(chip_id: int, dir_path=None) -> Calibration:
    dir_path = Path(dir_path) if dir_path else _PKG_CAL_DIR
    path = dir_path / f"chip{chip_id}.json"
    if not path.exists():
        raise CalibrationMissingError(f"no calibration for chip {chip_id} at {path}")
    return Calibration.from_dict(json.loads(path.read_text()))
