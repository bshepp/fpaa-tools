"""The driver must never pick the Pi 5 boot-EEPROM bus (spidev10)."""
import os

import pytest

from fpaa.driver import FPAAChain


def _nodes(monkeypatch, present):
    monkeypatch.setattr(os.path, "exists", lambda p: p in present)


def test_autodetect_returns_header_bus_when_present(monkeypatch):
    _nodes(monkeypatch, {"/dev/spidev0.0", "/dev/spidev10.0"})
    assert FPAAChain._autodetect_spi_bus(0) == 0


def test_autodetect_never_falls_back_to_bus_10(monkeypatch):
    # The Pi 5 failure case: SPI0 not enabled on the header, EEPROM bus visible.
    _nodes(monkeypatch, {"/dev/spidev10.0"})
    with pytest.raises(RuntimeError, match="spi0-0cs") as e:
        FPAAChain._autodetect_spi_bus(0)
    assert "boot EEPROM" in str(e.value)


def test_autodetect_raises_when_no_spidev_at_all(monkeypatch):
    _nodes(monkeypatch, set())
    with pytest.raises(RuntimeError, match="dtparam=spi=on"):
        FPAAChain._autodetect_spi_bus(0)


def test_explicit_bus_10_refused_on_pi5(monkeypatch):
    monkeypatch.setattr(FPAAChain, "_is_pi5", staticmethod(lambda: True))
    with pytest.raises(ValueError, match="boot-EEPROM"):
        FPAAChain._check_spi_bus(10)
    FPAAChain._check_spi_bus(0)                      # header bus is fine


def test_explicit_bus_10_allowed_off_pi5(monkeypatch):
    monkeypatch.setattr(FPAAChain, "_is_pi5", staticmethod(lambda: False))
    FPAAChain._check_spi_bus(10)                     # not our call on other boards


def test_simulation_mode_touches_no_bus():
    FPAAChain(simulate=True)                         # must not probe /dev at all
