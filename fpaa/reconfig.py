"""
Runtime reconfiguration (parameter update without reset) for the AN231E04.

Frame format (verified against AD2-generated ApiCode.c — the
an_BuildReconfigDataBlock / an_ClearApexReconfigData reference — and
consistent with the primary-configuration block format in config.py):

    0xD5                     sync
    <address1>               chip address from primary configuration
    <control>                Apex control byte; 0x80 = EndExecute
    then, per data block:
      byteNum | 0x80 [| 0x40]  start byte address; bit7 always set,
                               bit6 set when another block follows
      bank                     bank address
      count                    byte count (0 encodes 256)
      data[count]
      0x2A                     check byte (inverse sync)

Per the ABK reference firmware, an update should be followed by at least
one dummy byte to clock the configuration state machine through.

The typical workflow avoids knowing any parameter->address math: generate
two full configurations with AD2 that differ only in the parameter of
interest, then diff_frames() the per-chip primary frames and send the
resulting update. (AD2's CAMCode.c documents the per-CAM math if direct
computation is ever needed.)
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass

from .config import FPAAConfig, ConfigBlock

SYNC = 0xD5
CHECK = 0x2A  # ~0xD5 & 0xFF

# Apex control byte flags (ApiCode.h an_ApexControlByte)
CTRL_END_EXECUTE = 0x80
CTRL_PULLUPS = 0x40
CTRL_RESET_ALL = 0x20
CTRL_SAFD = 0x10
CTRL_UPDATE_CLOCKS = 0x01
CTRL_SOFT_RESET = 0x07


@dataclass
class UpdateBlock:
    """One SRAM block write: bank, start byte, data."""
    byte_address: int   # raw start byte number (without flag bits)
    bank_address: int
    data: bytes


def diff_frames(frame_a: FPAAConfig, frame_b: FPAAConfig) -> List[UpdateBlock]:
    """
    Block-level diff of two same-layout primary configuration frames.

    Returns the blocks of frame_b whose data differs from frame_a's
    corresponding block (matched by bank + byte address + length).
    Raises if the frames' block structures don't line up — the two
    configurations must come from the same circuit layout.
    """
    a_blocks = {(b.bank_address, b.byte_address & 0x3F, len(b.data)): b.data
                for b in frame_a.blocks}
    updates: List[UpdateBlock] = []
    for blk in frame_b.blocks:
        key = (blk.bank_address, blk.byte_address & 0x3F, len(blk.data))
        if key not in a_blocks:
            raise ValueError(
                f"block structure mismatch at bank={blk.bank_address} "
                f"byte=0x{blk.byte_address:02X} len={len(blk.data)} — "
                "frames are not the same circuit layout")
        if a_blocks[key] != blk.data:
            updates.append(UpdateBlock(
                byte_address=blk.byte_address & 0x3F,
                bank_address=blk.bank_address,
                data=blk.data,
            ))
    return updates


def build_update_frame(chip_address: int,
                       blocks: List[UpdateBlock],
                       control: int = CTRL_END_EXECUTE) -> bytes:
    """
    Build a reconfiguration frame for one chip.

    Mirrors an_ClearApexReconfigData + an_BuildReconfigDataBlock: header
    D5/addr/control, then each block with bit7 set on its address byte and
    bit6 ("update to follow") set on every block except the last.
    """
    if not blocks:
        return b""
    out = bytearray([SYNC, chip_address & 0xFF, control & 0xFF])
    for i, blk in enumerate(blocks):
        addr = (blk.byte_address & 0x3F) | 0x80
        if i < len(blocks) - 1:
            addr |= 0x40
        count = len(blk.data)
        if not 1 <= count <= 256:
            raise ValueError(f"block data length {count} out of range")
        out.append(addr)
        out.append(blk.bank_address & 0xFF)
        out.append(0 if count == 256 else count)
        out.extend(blk.data)
        out.append(CHECK)
    return bytes(out)


def make_update_from_configs(frame_a: FPAAConfig,
                             frame_b: FPAAConfig,
                             chip_address: Optional[int] = None,
                             control: int = CTRL_END_EXECUTE) -> bytes:
    """Diff two same-layout frames and build the A->B update frame."""
    blocks = diff_frames(frame_a, frame_b)
    addr = chip_address if chip_address is not None else frame_b.chip_id
    return build_update_frame(addr, blocks, control=control)
