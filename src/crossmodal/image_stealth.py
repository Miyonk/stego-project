"""Stealthier image embedder: key-dependent dither + optional texture-only embedding.

Plain QIM rounds coefficients to multiples of DELTA, which leaves a regular comb pattern in
the coefficient histograms that detectors learn. Here every slot gets its own secret random
offset (dither) so the lattice differs from slot to slot and the comb disappears for anyone
without the key. Optionally only blocks in busy (textured) regions are used; texture is measured
from the block averages (DC), which embedding never changes, so the receiver can recompute it.
"""
import numpy as np
from scipy.fft import dctn, idctn
from scipy.ndimage import uniform_filter

from src.video.dct_embed import COEFFS, _blocks, _slots, _unblocks

BLOCK = 8


def texture_mask(img: np.ndarray, keep: float) -> np.ndarray:
    dc = _blocks(img.astype(np.float64)[None]).mean(axis=(3, 4))[0]
    local = np.sqrt(np.maximum(uniform_filter(dc ** 2, 3) - uniform_filter(dc, 3) ** 2, 0))
    return local >= np.quantile(local, 1.0 - keep)


def _prep(img, nbits, key, reps, delta, keep):
    fr, row, col, c = _slots((1,) + img.shape, nbits, reps, key)
    cu = np.array([k[0] for k in COEFFS])[c]
    cv = np.array([k[1] for k in COEFFS])[c]
    dither = np.random.default_rng(key + 7919).uniform(0, 2 * delta, size=fr.shape)
    use = texture_mask(img, keep)[row, col] if keep < 1.0 else np.ones(fr.shape, bool)
    return fr, row, col, cu, cv, dither, use


def embed(img, bits, key, delta=64.0, reps=8, keep=1.0, dither=True):
    bits = np.asarray(bits, dtype=np.int64)
    dct = dctn(_blocks(img.astype(np.float64)[None]), axes=(3, 4), norm="ortho")
    fr, row, col, cu, cv, d, use = _prep(img, len(bits), key, reps, delta, keep)
    if not dither:
        d = np.zeros_like(d)
    val = (dct[fr, row, col, cu, cv] - d) / delta
    q = np.rint(val)
    q = np.where((q.astype(np.int64) % 2) != bits[None, :], q + np.where(val >= q, 1, -1), q)
    dct[fr[use], row[use], col[use], cu[use], cv[use]] = (q * delta + d)[use]
    out = _unblocks(idctn(dct, axes=(3, 4), norm="ortho"))[0]
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def extract(img, nbits, key, delta=64.0, reps=8, keep=1.0, dither=True):
    dct = dctn(_blocks(img.astype(np.float64)[None]), axes=(3, 4), norm="ortho")
    fr, row, col, cu, cv, d, use = _prep(img, nbits, key, reps, delta, keep)
    if not dither:
        d = np.zeros_like(d)
    u = (dct[fr, row, col, cu, cv] - d) / delta
    frac = np.mod(u, 2.0)
    soft = ((np.minimum(frac, 2 - frac) - np.abs(frac - 1.0)) * use).sum(axis=0)
    return (soft > 0).astype(np.uint8)