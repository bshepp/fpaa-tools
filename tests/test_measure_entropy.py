import numpy as np
from fpaa.measure import entropy as E


def test_min_and_shannon_entropy_extremes():
    assert abs(E.shannon_entropy(np.array([0, 1, 0, 1])) - 1.0) < 1e-9
    assert abs(E.min_entropy(np.array([0, 1, 0, 1])) - 1.0) < 1e-9
    assert E.shannon_entropy(np.ones(10)) == 0.0
    assert E.min_entropy(np.ones(10)) == 0.0
    # biased p=0.25 -> min-entropy = -log2(0.75) ~ 0.415
    bits = np.array([1, 0, 0, 0] * 100)
    assert abs(E.min_entropy(bits) - (-np.log2(0.75))) < 1e-9


def test_monobit_balanced_vs_biased():
    rng = np.random.default_rng(0)
    balanced = (rng.random(20000) < 0.5).astype(np.int8)
    biased = (rng.random(20000) < 0.7).astype(np.int8)
    assert E.monobit(balanced)["p_value"] > 0.01     # looks random
    assert E.monobit(biased)["p_value"] < 1e-6        # clearly biased


def test_runs_test_on_random():
    rng = np.random.default_rng(1)
    bits = (rng.random(20000) < 0.5).astype(np.int8)
    assert E.runs_test(bits)["p_value"] > 0.01


def test_autocorrelation():
    ac = E.autocorrelation(np.array([0, 1] * 500), maxlag=2)
    assert ac[0] == 1.0
    assert abs(ac[1] + 1.0) < 0.01                    # alternating -> ~-1 at lag 1
    rng = np.random.default_rng(2)
    acr = E.autocorrelation((rng.random(20000) < 0.5).astype(np.int8), maxlag=5)
    assert all(abs(a) < 0.05 for a in acr[1:])        # random -> ~0


def test_von_neumann_debiases():
    rng = np.random.default_rng(3)
    biased = (rng.random(200000) < 0.8).astype(np.int8)   # heavily biased, IID
    out = E.von_neumann(biased)
    assert out.size > 1000
    assert abs(out.mean() - 0.5) < 0.02                   # debiased toward 0.5


def test_xor_fold_and_pack():
    bits = np.array([1, 1, 0, 1, 1, 0], dtype=np.int8)
    assert E.xor_fold(bits, 2).tolist() == [0, 1, 1]      # 1^1, 0^1, 1^0
    assert E.xor_fold(bits, 3).tolist() == [0, 0]         # 1^1^0, 1^1^0
    assert E.pack_bytes(np.array([1, 0, 0, 0, 0, 0, 0, 1])) == bytes([0x81])


def test_xor_streams_identical_cancels():
    a = np.array([1, 0, 1, 1, 0], dtype=np.int8)
    assert list(E.xor_streams(a, a)) == [0, 0, 0, 0, 0]


def test_xor_streams_pairwise():
    a = np.array([1, 0, 1], dtype=np.int8)
    b = np.array([0, 0, 1], dtype=np.int8)
    assert list(E.xor_streams(a, b)) == [1, 0, 0]


def test_xor_streams_nway():
    a = np.array([1, 1, 0, 0], dtype=np.int8)
    b = np.array([0, 1, 1, 0], dtype=np.int8)
    c = np.array([0, 0, 0, 1], dtype=np.int8)
    # 1^0^0=1, 1^1^0=0, 0^1^0=1, 0^0^1=1
    assert list(E.xor_streams(a, b, c)) == [1, 0, 1, 1]


def test_xor_streams_truncates_to_shortest():
    a = np.array([1, 1, 1, 1], dtype=np.int8)
    b = np.array([1, 0], dtype=np.int8)
    assert list(E.xor_streams(a, b)) == [0, 1]


def test_xor_streams_normalizes_nonzero_to_one():
    a = np.array([2, 0, 5], dtype=np.int8)   # any nonzero -> 1
    b = np.array([0, 0, 1], dtype=np.int8)
    assert list(E.xor_streams(a, b)) == [1, 0, 0]


def test_xor_streams_requires_a_stream():
    import pytest
    with pytest.raises(ValueError):
        E.xor_streams()
