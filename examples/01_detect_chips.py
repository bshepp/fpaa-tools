#!/usr/bin/env python3
"""
Example 01: Detect FPAA Chips

First test to verify hardware connectivity.
Detects how many AN231E04 chips are present in the chain.

Usage:
    python3 01_detect_chips.py
    
    # Simulation mode (no hardware):
    python3 01_detect_chips.py --simulate
"""

import sys
import argparse

# Add parent directory to path for imports
sys.path.insert(0, '..')

from fpaa import FPAAChain


def main():
    parser = argparse.ArgumentParser(description='Detect FPAA chips on PIKA HAT')
    parser.add_argument('--simulate', '-s', action='store_true',
                        help='Run in simulation mode without hardware')
    parser.add_argument('--spi-speed', type=int, default=1_000_000,
                        help='SPI clock speed in Hz (default: 1MHz)')
    args = parser.parse_args()
    
    print("=" * 50)
    print("FPAA Chip Detection - OTC2310K04-PIKA HAT")
    print("=" * 50)
    
    try:
        with FPAAChain(
            spi_speed_hz=args.spi_speed,
            simulate=args.simulate
        ) as chain:
            print(f"\nChain initialized: {chain}")
            
            # Check initial status
            print(f"\nInitial status:")
            print(f"  ERRb pin: {'HIGH (OK)' if chain.err_status else 'LOW (Error)'}")
            print(f"  ACTIVATE pin: {'HIGH (Active)' if chain.activate_status else 'LOW (Inactive)'}")
            
            # Perform hard reset
            print(f"\nPerforming hard reset...")
            chain.hard_reset()
            
            # Detect chips
            print(f"\nDetecting chips...")
            num_chips = chain.detect_chips()
            
            print(f"\n{'=' * 50}")
            print(f"RESULT: {num_chips} AN231E04 chip(s) detected")
            print(f"{'=' * 50}")
            
            if num_chips == 4:
                print("\n✓ All 4 chips detected - hardware is working correctly!")
            elif num_chips > 0:
                print(f"\n⚠ Only {num_chips}/4 chips detected - check connections")
            else:
                print("\n✗ No chips detected!")
                print("  Check:")
                print("  - HAT is properly seated on GPIO header")
                print("  - Power supply is connected (if using external)")
                print("  - SPI is enabled on Raspberry Pi")
            
            # Print detailed status
            print("\nDetailed chip status:")
            for status in chain.get_status():
                print(f"  Chip {status.chip_id}: configured={status.configured}")
                
    except Exception as e:
        print(f"\n✗ Error: {e}")
        if "spidev" in str(e).lower():
            print("\nHint: Make sure SPI is enabled:")
            print("  sudo raspi-config -> Interface Options -> SPI -> Enable")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

