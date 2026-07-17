"""Reservoir-computing readout + characterization.

Pure numpy analysis of an (T, N) state matrix (T timesteps x N reservoir nodes)
plus multi-channel PWM-duty -> voltage decode. Analysis only and fully
host-testable — hardware capture is the caller's job (see fpaa.measure.backends).
"""
import numpy as np

from .readers import duty as _duty
from .errors import NoEdgesError


def participation_ratio(states):
    """Effective number of independent nodes = (sum L)^2 / sum(L^2) of the
    node-covariance eigenvalues L. 1 = all nodes redundant, N = fully diverse."""
    x = np.asarray(states, dtype=np.float64)
    cov = np.cov(x, rowvar=False)
    cov = np.atleast_2d(cov)
    w = np.linalg.eigvalsh(cov)
    w = np.clip(w, 0.0, None)
    s = w.sum()
    if s <= 0.0:
        return 1.0
    return float(s * s / np.dot(w, w))


def pairwise_corr_summary(states):
    """Off-diagonal |Pearson correlation| summary across nodes."""
    x = np.asarray(states, dtype=np.float64)
    n = x.shape[1]
    c = np.corrcoef(x, rowvar=False)
    c = np.atleast_2d(c)
    iu = np.triu_indices(n, k=1)
    vals = np.abs(c[iu])
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return {"mean_abs": 0.0, "max_abs": 0.0, "n_pairs": 0}
    return {"mean_abs": float(vals.mean()), "max_abs": float(vals.max()),
            "n_pairs": int(vals.size)}


def responsiveness(driven, baseline, eps=1e-12):
    """Per-node variance ratio var(driven)/var(baseline); >> 1 = the node
    tracks the input rather than sitting at the noise floor."""
    d = np.asarray(driven, dtype=np.float64)
    b = np.asarray(baseline, dtype=np.float64)
    vd = d.var(axis=0)
    vb = np.maximum(b.var(axis=0), eps)
    return vd / vb


def decode_state(channel_trans, calibrations):
    """Decode N per-node PWM transition arrays into an (N,) voltage vector via
    each node's duty cycle and Calibration. Channels with no complete period
    decode to NaN."""
    out = np.full(len(channel_trans), np.nan, dtype=np.float64)
    for i, (trans, cal) in enumerate(zip(channel_trans, calibrations)):
        try:
            out[i] = cal.voltage(_duty(trans).duty)
        except NoEdgesError:
            out[i] = np.nan
    return out
