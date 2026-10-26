"""Hide a short secret in an ordinary colour photo (and read it back).

The secret is encrypted (AES-GCM), padded to a fixed size so its length is not visible,
protected with Reed-Solomon and written into the brightness (luma) channel with the dithered
QIM embedder. Colour channels are left alone, so the photo stays in colour.
Everything the receiver needs is the image and the passphrase.
"""
import hashlib

import cv2
import numpy as np

from src.crossmodal import image_stealth as S
from src.crypto.secret import coded_nbits, decode_secret, derive_key, encode_secret
from src.video.dct_embed import COEFFS

MAX_SECRET = 100                       # bytes of secret text
PLAIN_LEN = 1 + MAX_SECRET             # length byte + secret + padding
NBITS = coded_nbits(PLAIN_LEN)
MAX_REPS = 8
MAX_SIDE = 1600                        # larger photos are scaled down first
STRENGTH = {"robust": 64.0, "balanced": 32.0, "subtle": 16.0}   # QIM step per preset


def stego_key(passphrase: str) -> int:
    return int.from_bytes(hashlib.sha256(("photo:" + passphrase).encode()).digest()[:6], "big") % 10**9


def _reps(h8: int, w8: int) -> int:
    slots = (h8 // 8) * (w8 // 8) * len(COEFFS)
    return min(MAX_REPS, slots // NBITS)


def prepare(bgr: np.ndarray) -> np.ndarray:
    """Scale very large photos down so embedding stays fast."""
    h, w = bgr.shape[:2]
    s = MAX_SIDE / max(h, w)
    return cv2.resize(bgr, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA) if s < 1 else bgr


def embed(bgr: np.ndarray, secret: str, passphrase: str, strength: str = "balanced"):
    """Returns (stego_bgr, info dict). Raises ValueError with a readable message."""
    raw = secret.encode()
    if not raw:
        raise ValueError("the secret is empty")
    if len(raw) > MAX_SECRET:
        raise ValueError(f"the secret is {len(raw)} bytes; the limit is {MAX_SECRET}")
    if strength not in STRENGTH:
        raise ValueError(f"strength must be one of {list(STRENGTH)}")
    bgr = prepare(bgr)
    h, w = bgr.shape[:2]
    h8, w8 = h // 8 * 8, w // 8 * 8
    reps = _reps(h8, w8)
    if reps < 2:
        raise ValueError(f"this photo is too small ({w}x{h}); use one of at least about 200x200 pixels")
    plain = bytes([len(raw)]) + raw + bytes(MAX_SECRET - len(raw))
    bits = encode_secret(plain, derive_key(passphrase))
    ycc = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    y = ycc[:h8, :w8, 0].copy()
    ycc[:h8, :w8, 0] = S.embed(y, bits, stego_key(passphrase), delta=STRENGTH[strength], reps=reps)
    out = cv2.cvtColor(ycc, cv2.COLOR_YCrCb2BGR)
    mse = np.mean((bgr.astype(np.float64) - out) ** 2)
    return out, {"width": w, "height": h, "reps": reps, "delta": STRENGTH[strength],
                 "psnr_db": float(10 * np.log10(255 ** 2 / max(mse, 1e-9))),
                 "bits": int(NBITS), "scaled_from": None}


def extract(bgr: np.ndarray, passphrase: str, strength: str = "balanced"):
    """Returns the secret text, or None if it could not be recovered."""
    h, w = bgr.shape[:2]
    h8, w8 = h // 8 * 8, w // 8 * 8
    reps = _reps(h8, w8)
    if reps < 2 or strength not in STRENGTH:
        return None
    y = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)[:h8, :w8, 0]
    bits = S.extract(y, NBITS, stego_key(passphrase), delta=STRENGTH[strength], reps=reps)
    plain = decode_secret(bits, derive_key(passphrase))
    if plain is None or len(plain) != PLAIN_LEN or plain[0] > MAX_SECRET:
        return None
    return plain[1:1 + plain[0]].decode(errors="replace")


def difference_map(a: np.ndarray, b: np.ndarray, gain: float = 20.0) -> np.ndarray:
    """Magnified absolute difference, so changes that are invisible become visible."""
    d = np.abs(a.astype(np.float64) - b.astype(np.float64)).max(axis=2) * gain
    return cv2.applyColorMap(np.clip(d, 0, 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
