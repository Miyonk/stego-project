"""Motion-aware DCT video embedder (luma only, blind extraction, key-driven positions).

Same quantisation-index-modulation (QIM) idea as dct_embed.py, but hidden bits are
only written into the 8x8 block positions where the video is *moving*: the places
whose average brightness changes the most from frame to frame over the whole clip
(for a talking head, the face). Motion masks small changes better than still areas,
and it uses the time dimension of the video instead of treating every frame as an
independent picture.

The receiver has no access to the original, so it recomputes the motion map from the
block averages (the DC value), which the embedder never changes (it only modifies AC
coefficients). The map is averaged over all frames, so compression noise barely moves
it. Each bit has `reps` key-chosen candidate positions; a candidate is used only if its
block position is in the moving set, so about `keep * reps` copies of every bit exist.
The receiver counts exactly the same set (using a larger set would add false votes
from still areas, which always look like a 0 bit).
"""
import numpy as np
from scipy.fft import dctn, idctn

BLOCK = 8
COEFFS = ((0, 1), (1, 0), (1, 1), (0, 2), (2, 0))
DELTA = 64.0
REPS = 48            # candidate positions per bit
KEEP = 0.3           # share of block positions (the most moving ones) that may be used


def _blocks(frames: np.ndarray) -> np.ndarray:
    t, h, w = frames.shape
    b = frames.reshape(t, h // BLOCK, BLOCK, w // BLOCK, BLOCK)
    return b.transpose(0, 1, 3, 2, 4)            # (t, bh, bw, 8, 8)


def _unblocks(blocks: np.ndarray) -> np.ndarray:
    t, bh, bw, _, _ = blocks.shape
    return blocks.transpose(0, 1, 3, 2, 4).reshape(t, bh * BLOCK, bw * BLOCK)


def motion_mask(frames: np.ndarray, keep: float = KEEP) -> np.ndarray:
    """(bh, bw) boolean map: True for the `keep` share of block positions that move most."""
    dc = _blocks(frames.astype(np.float64)).mean(axis=(3, 4))     # block averages (t, bh, bw)
    motion = np.abs(np.diff(dc, axis=0)).mean(axis=0)             # average change per position
    return motion >= np.quantile(motion, 1.0 - keep)


def capacity_bits(shape, reps: int = REPS, coeffs=COEFFS) -> int:
    """Distinct bits that fit (every candidate position must exist, used or not)."""
    t, h, w = shape
    return (t * (h // BLOCK) * (w // BLOCK) * len(coeffs)) // reps


def _slots(shape, nbits: int, reps: int, stego_key: int, coeffs=COEFFS):
    t, h, w = shape
    bh, bw, nc = h // BLOCK, w // BLOCK, len(coeffs)
    total = t * bh * bw * nc
    if nbits * reps > total:
        raise ValueError(f"payload of {nbits} bits x {reps} reps exceeds capacity {total}")
    order = np.random.default_rng(stego_key).permutation(total)[: nbits * reps]
    order = order.reshape(reps, nbits)
    c = order % nc
    rest = order // nc
    col = rest % bw
    rest //= bw
    row = rest % bh
    fr = rest // bh
    return fr, row, col, c


def embed(frames: np.ndarray, bits, stego_key: int, delta=DELTA, reps=REPS,
          coeffs=COEFFS, keep=KEEP) -> np.ndarray:
    """Hide bits in the moving block positions of a (frames, H, W) uint8 luma array."""
    bits = np.asarray(bits, dtype=np.int64)
    mask = motion_mask(frames, keep)
    dct = dctn(_blocks(frames.astype(np.float64)), axes=(3, 4), norm="ortho")
    fr, row, col, c = _slots(frames.shape, len(bits), reps, stego_key, coeffs)
    use = mask[row, col]                                          # (reps, nbits)
    cu = np.array([k[0] for k in coeffs])[c]
    cv = np.array([k[1] for k in coeffs])[c]
    val = dct[fr, row, col, cu, cv] / delta
    q = np.rint(val)
    wrong = (q.astype(np.int64) % 2) != bits[None, :]
    q = np.where(wrong, q + np.where(val >= q, 1, -1), q)
    dct[fr[use], row[use], col[use], cu[use], cv[use]] = (q * delta)[use]
    out = _unblocks(idctn(dct, axes=(3, 4), norm="ortho"))
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def extract(frames: np.ndarray, nbits: int, stego_key: int, delta=DELTA, reps=REPS,
            coeffs=COEFFS, keep=KEEP) -> np.ndarray:
    """Read nbits back from a (possibly attacked) luma array. Needs no cover."""
    mask = motion_mask(frames, keep)
    dct = dctn(_blocks(frames.astype(np.float64)), axes=(3, 4), norm="ortho")
    fr, row, col, c = _slots(frames.shape, nbits, reps, stego_key, coeffs)
    use = mask[row, col]
    cu = np.array([k[0] for k in coeffs])[c]
    cv = np.array([k[1] for k in coeffs])[c]
    u = dct[fr, row, col, cu, cv] / delta
    frac = np.mod(u, 2.0)
    d_even = np.minimum(frac, 2.0 - frac)
    d_odd = np.abs(frac - 1.0)
    soft = ((d_even - d_odd) * use).sum(axis=0)                   # only the moving blocks vote
    return (soft > 0).astype(np.uint8)
