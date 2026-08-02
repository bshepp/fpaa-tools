#!/usr/bin/env python3
"""
Example 02: Send Blank Configuration

Streams a minimal "blank" per-chip configuration to all four FPAAs in one
SPI burst — the same reset/stream/settle flow as FPAAChain.configure_from_ahf,
but with generated frames instead of an AHF file.

NOTE: create_blank_config() is UNVERIFIED on PIKA hardware. Its byte sequence
comes from the legacy QuadApex ABK firmware. For a known-good bring-up test,
use example 03 with the bundled examples/4osc.ahf.

Usage:
    python3 02_blank_config.py
    python3 02_blank_config.py --simulate
"""

import sys
import argparse
import time

sys.path.insert(0, '..')

from fpaa import FPAAChain
from fpaa.config import create_blank_config


def main():
    parser = argparse.ArgumentParser(description='Send blank configuration to FPAAs')
    parser.add_argument('--simulate', '-s', action='store_true',
                        help='Run in simulation mode')
    args = parser.parse_args()

    print("=" * 50)
    print("FPAA Blank Configuration Test")
    print("=" * 50)
    print("\nNOTE: blank frames are legacy-ABK-derived and unverified on")
    print("PIKA hardware. Example 03 + 4osc.ahf is the known-good test.")

    with FPAAChain(simulate=args.simulate) as chain:
        num_chips = chain.MAX_CHIPS

        print(f"\nBuilding blank configurations for {num_chips} chips...")
        frames = []
        for i in range(num_chips):
            frame = create_blank_config(chip_id=i + 1, first_in_chain=(i == 0))
            frames.append(frame)
            print(f"  Chip {i + 1}: {len(frame)} bytes")

        burst = b"".join(frames)

        print(f"\nResetting chain and streaming {len(burst)} bytes in one burst...")
        chain.reset()
        chain.send_bytes(burst)
        time.sleep(chain.AUTONULL_S)

        print("\nFinal status:")
        print(f"  ERR_B   : {'HIGH (OK)' if chain.err_status else 'LOW (Error)'}")
        print(f"  ACTIVATE: {'HIGH' if chain.activate_status else 'LOW'}")

        if chain.err_status and chain.activate_status:
            print(f"\n{'=' * 50}")
            print("SUCCESS: All chips configured!")
            print(f"{'=' * 50}")
            print("\nThe FPAAs are now in a blank state, ready for")
            print("custom analog circuit configurations.")
            return 0

        print("\nWARNING: status pins unexpected after blank config.")
        print("Use examples/03_load_ahf.py with 4osc.ahf to verify the chain.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
