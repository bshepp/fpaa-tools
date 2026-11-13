import pytest

from fpaa.config import (assemble_chain, chip_frame, load_ahf_bytes,
                         write_ahf)

# Minimal per-chip export: 5 NULL preamble + one frame. The data deliberately
# contains a stray 0xD5 -- the byte that makes split_ahf_by_chip() mis-fire.
FRAME = bytes([0xD5, 0xB7, 0x20, 0x01, 0x00, 0x01, 0xC1, 0x00, 0x00, 0x02,
               0xD5, 0x11, 0x2A, 0x00])
PER_CHIP = bytes(5) + FRAME


def test_chip_frame_sets_address_and_keeps_payload():
    f = chip_frame(PER_CHIP, 3)
    assert f[0] == 0xD5 and f[5] == 3 and f[6] == 0xC1
    assert f[:5] == FRAME[:5] and f[6:] == FRAME[6:]   # only the address changes
    assert len(f) == len(FRAME)                        # stray 0xD5 did not split it


def test_chip_frame_rejects_bad_input():
    with pytest.raises(ValueError, match="frame sync"):
        chip_frame(bytes(20), 1)
    bad_ctrl = bytearray(PER_CHIP)
    bad_ctrl[5 + 6] = 0x81
    with pytest.raises(ValueError, match="control byte"):
        chip_frame(bytes(bad_ctrl), 1)
    with pytest.raises(ValueError, match="out of range"):
        chip_frame(PER_CHIP, 0)


def test_assemble_chain_addresses_by_position(tmp_path):
    srcs = []
    for i in range(4):
        d = bytearray(PER_CHIP)
        d[-3] = 0x10 + i                 # distinguishable payload per chip
        srcs.append(write_ahf(tmp_path / f"c{i}.ahf", bytes(d)))
    out = tmp_path / "chain.ahf"
    chain = assemble_chain(srcs, out)
    assert chain[:5] == bytes(5)
    n = len(FRAME)
    for i in range(4):
        fr = chain[5 + i * n: 5 + (i + 1) * n]
        assert fr[0] == 0xD5 and fr[5] == i + 1 and fr[-3] == 0x10 + i
    assert load_ahf_bytes(out) == chain  # written file round-trips


def test_assemble_chain_replicates_single_source():
    chain = assemble_chain(PER_CHIP)     # bytes, not a list -> 4 copies
    n = len(FRAME)
    assert len(chain) == 5 + 4 * n
    assert [chain[5 + i * n + 5] for i in range(4)] == [1, 2, 3, 4]
    assert len(assemble_chain(PER_CHIP, n_chips=2)) == 5 + 2 * n


def test_assemble_chain_error_names_position(tmp_path):
    good = write_ahf(tmp_path / "good.ahf", PER_CHIP)
    bad = write_ahf(tmp_path / "bad.ahf", bytes(12))
    with pytest.raises(ValueError, match="chain position 1"):
        assemble_chain([good, bad])
