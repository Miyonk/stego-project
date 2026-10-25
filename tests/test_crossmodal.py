import numpy as np
import pytest

from src.crossmodal import erasure as E
from src.crossmodal.pipeline3 import PLANS, Plan, extract, embed
from src.crypto.secret import derive_key


def test_erasure_any_k_of_n():
    frame = bytes(range(92))
    for k, n in ((2, 3), (1, 3), (3, 5), (3, 3)):
        frags = E.split_parity(frame, k, n)
        for lost in range(n - k + 1):
            for first in range(n):
                keep = [None if (i - first) % n < lost else f for i, f in enumerate(frags)]
                assert E.join_parity(keep, len(frame), k, n) == frame
        too_many = [None] * (n - k + 1) + frags[n - k + 1:]
        assert E.join_parity(too_many, len(frame), k, n) is None


def test_protect_roundtrip_and_erasure_flag():
    frag = bytes(range(46))
    bits = E.protect(frag)
    assert E.unprotect(bits) == frag
    bad = bits.copy()
    bad[::3] ^= 1                         # ~33% bit errors: must be flagged, not mis-decoded
    assert E.unprotect(bad) is None


def _toy():
    rng = np.random.default_rng(0)
    audio = (rng.normal(0, 3000, 16000 * 3)).astype(np.int16)
    frames = rng.integers(60, 190, (50, 128, 128)).astype(np.uint8)
    still = rng.integers(60, 190, (384, 384)).astype(np.uint8)
    return audio, frames, still


@pytest.mark.parametrize("name", ["erasure_2of3", "replicate_3", "split3", "erasure_2of3_motion"])
def test_clean_roundtrip(name):
    a, f, i = _toy()
    key = derive_key("pw")
    sa, sf, si, meta = embed(a, f, i, b"hello cross-modal world", key, PLANS[name])
    got, status = extract(sa, sf, si, key, meta)
    assert got == b"hello cross-modal world", status


def test_lost_carrier_is_survived():
    a, f, i = _toy()
    key = derive_key("pw")
    sa, sf, si, meta = embed(a, f, i, b"survive me", key, PLANS["erasure_2of3"])
    rng = np.random.default_rng(1)
    wrecked = rng.integers(0, 255, sf.shape).astype(np.uint8)       # video destroyed
    got, status = extract(sa, wrecked, si, key, meta)
    assert got == b"survive me" and status[1] == "erased"
    got2, _ = extract(sa, wrecked, rng.integers(0, 255, si.shape).astype(np.uint8), key, meta)
    assert got2 is None                                              # two lost: k=2 cannot
    sa, sf, si, meta = embed(a, f, i, b"survive me", key, PLANS["replicate_3"])
    got3, _ = extract(rng.integers(-999, 999, sa.shape).astype(np.int16), wrecked, si, key, meta)
    assert got3 == b"survive me"


def test_wrong_passphrase():
    a, f, i = _toy()
    sa, sf, si, meta = embed(a, f, i, b"x", derive_key("right"), PLANS["erasure_2of3"])
    assert extract(sa, sf, si, derive_key("wrong"), meta)[0] is None
