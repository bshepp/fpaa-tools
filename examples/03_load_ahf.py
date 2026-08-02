#!/usr/bin/env python3
"""
Example 03: Load Configuration from AHF File

Streams a circuit designed in AnadigmDesigner2 / DynAMx Design Lab onto
the four AN231E04 FPAAs in the PIKA chain in a single SPI burst, exactly
as the official Okika spitest.py reference does.

For first-light bring-up on the Pi 5, use the bundled known-good
4-oscillator configuration (from Okika's MIT-0 pikapy reference):

    python3 03_load_ahf.py 4osc.ahf

Expected hardware result: ACTIVATE goes high after ~60 ms (auto-null
delay), and the four FPAA outputs produce sine waves at 80 / 150 / 277 /
493 kHz.
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fpaa import FPAAChain, load_ahf_bytes, split_ahf_by_chip


def main() -> int:
    parser = argparse.ArgumentParser(description='Load AHF configuration onto the chain')
    parser.add_argument('ahf_file', type=str, help='Path to .ahf file')
    parser.add_argument('--simulate', '-s', action='store_true',
                        help='Run in simulation mode (no hardware)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show per-chip frame breakdown')
    parser.add_argument('--spi-hz', type=int, default=32_000_000,
                        help='SPI clock speed in Hz (default 32 MHz, matches spitest.py)')
    args = parser.parse_args()

    ahf_path = Path(args.ahf_file)
    if not ahf_path.exists():
        print(f"Error: file not found: {ahf_path}")
        return 1

    print("=" * 60)
    print("FPAA Primary Configuration from AHF")
    print("=" * 60)
    print(f"AHF: {ahf_path}")

    raw = load_ahf_bytes(str(ahf_path))
    print(f"Total bytes: {len(raw)}")

    if args.verbose:
        per_chip = split_ahf_by_chip(raw)
        print(f"Per-chip frames found: {len(per_chip)}")
        for cfg in per_chip:
            print(f"  chip_id=0x{cfg.chip_id:02X}  "
                  f"frame_bytes={cfg.total_bytes}  "
                  f"data_blocks={len(cfg.blocks)}")

    with FPAAChain(simulate=args.simulate, spi_speed_hz=args.spi_hz) as chain:
        print(f"\nChain: {chain}")
        print("Streaming AHF in a single SPI burst...")
        ok = chain.configure_from_ahf(str(ahf_path))

        status = chain.get_chain_status()
        print(f"\nPost-config pin state:")
        print(f"  ERR_B    : {'HIGH (no error)' if status.err_b_high else 'LOW (ERROR)'}")
        print(f"  ACTIVATE : {'HIGH (configured)' if status.activate_high else 'LOW (not configured)'}")
        print(f"  CFGFLG_B : {'HIGH' if status.cfgflg_b_high else 'LOW (flag asserted)'}")

        if ok:
            print("\nSUCCESS: chain primary-configured.")
            return 0
        else:
            print("\nFAILURE: ACTIVATE did not go high or ERR_B is asserted.")
            return 1


if __name__ == '__main__':
    sys.exit(main())
