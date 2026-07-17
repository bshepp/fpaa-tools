"""Channel — bundles (chip_id, gpio_pin, backend, calibration) and exposes
physical reads, replacing the (GPIO, pin, window_s) threading in the scripts."""
from .readers import frequency, duty, periods
from .errors import CalibrationMissingError


class Channel:
    def __init__(self, chip_id, gpio_pin, backend, calibration=None):
        self.chip_id = chip_id
        self.gpio_pin = gpio_pin
        self.backend = backend
        self.calibration = calibration

    def capture(self, duration_s):
        return self.backend.capture_edges([self.gpio_pin], duration_s)

    def frequency(self, duration_s):
        s = self.capture(duration_s)
        return frequency(s.pin(self.gpio_pin), duration_s)

    def periods(self, duration_s):
        s = self.capture(duration_s)
        return periods(s.pin(self.gpio_pin))

    def voltage(self, duration_s):
        if self.calibration is None:
            raise CalibrationMissingError(
                f"chip {self.chip_id} pin {self.gpio_pin} has no calibration")
        s = self.capture(duration_s)
        d = duty(s.pin(self.gpio_pin))
        return self.calibration.voltage(d.duty)
