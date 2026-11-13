"""
fpaa-tools
==========

Python interface for Anadigm AN231E04 FPAAs on the Okika OTC2310K04-PIKA
Raspberry Pi HAT (4 chips, daisy-chained over SPI).

Provides:
- Low-level SPI communication with the FPAA chain
- Primary configuration upload from .ahf files
- Runtime reconfiguration (parameter update without reset): diff two
  same-layout configurations with fpaa.reconfig and send the ~15-byte
  update frame via FPAAChain.send_update() — ~1 ms per update vs ~180 ms
  for a full reconfigure (validated on hardware)
- Measurement: edge capture, channel analysis, entropy, dynamics, sync
  (see fpaa.measure; prefer GpiodBackend for timing-sensitive work)
- Analog neural network primitives (capacity modeling; no bitstream synthesis)

On a Raspberry Pi 5, /boot/firmware/config.txt needs BOTH `dtparam=spi=on`
and `dtoverlay=spi0-0cs` — see docs/PIKA_HARDWARE.md.

MIT No Attribution.
"""

from .driver import FPAA, FPAAChain
from .config import (load_ahf_file, load_ahf_bytes, split_ahf_by_chip,
                     parse_bitstream, chip_frame, assemble_chain, write_ahf)
from .neural import AnalogNeuron, AnalogLayer
from .reconfig import (UpdateBlock, diff_frames, build_update_frame,
                       make_update_from_configs)
from . import measure

__version__ = "0.5.2"
__all__ = [
    "FPAA", "FPAAChain",
    "load_ahf_file", "load_ahf_bytes", "split_ahf_by_chip", "parse_bitstream",
    "chip_frame", "assemble_chain", "write_ahf",
    "AnalogNeuron", "AnalogLayer",
    "UpdateBlock", "diff_frames", "build_update_frame",
    "make_update_from_configs",
    "measure",
]

