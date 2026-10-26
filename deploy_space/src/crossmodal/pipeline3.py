"""Three-carrier pipeline (audio, video, image) with k-of-n erasure coding.

n carriers hold n fragments; any k of them rebuild the secret.
  k = 1, n = 1  one carrier only            (no redundancy, single point of failure)
  k = n = 3     plain split                  (any lost carrier = lost secret)
  k = 2, n = 3  erasure coded                (one whole carrier may be lost)
  k = 1, n = 3  replication                  (two whole carriers may be lost)
"""
import os
from dataclasses import dataclass

import numpy as np
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.audio import stft_embed as A
from src.crossmodal import erasure as E
from src.crossmodal import image_carrier as I
from src.crypto.secret import NONCE_LEN
from src.video import dct_embed as VS
from src.video import motion_embed as VM

KEYS = {"audio": 7, "video": 5, "image": 3}
ORDER = ("audio", "video", "image")


@dataclass
class Plan:
    carriers: tuple          # which carriers are used, in fragment order
    k: int                   # fragments needed
    video: str = "standard"  # "standard" or "motion"

    @property
    def n(self):
        return len(self.carriers)


PLANS = {
    "audio_only": Plan(("audio",), 1),
    "video_only": Plan(("video",), 1),
    "image_only": Plan(("image",), 1),
    "split3": Plan(ORDER, 3),
    "erasure_2of3": Plan(ORDER, 2),
    "replicate_3": Plan(ORDER, 1),
    "erasure_2of3_motion": Plan(ORDER, 2, "motion"),
    "video_only_motion": Plan(("video",), 1, "motion"),
}


def _vid(plan):
    return VM if plan.video == "motion" else VS


def embed(audio, frames, still, secret: bytes, passphrase_key: bytes, plan: Plan):
    """Returns (stego_audio, stego_frames, stego_still, meta)."""
    nonce = os.urandom(NONCE_LEN)
    frame = nonce + AESGCM(passphrase_key).encrypt(nonce, secret, None)
    frags = E.split_parity(frame, plan.k, plan.n)
    out = {"audio": audio, "video": frames, "image": still}
    for name, frag in zip(plan.carriers, frags):
        bits = E.protect(frag)
        if name == "audio":
            out[name] = A.embed(audio, bits, KEYS[name])
        elif name == "video":
            out[name] = _vid(plan).embed(frames, bits, KEYS[name])
        else:
            out[name] = I.embed(still, bits, KEYS[name])
    meta = {"flen": len(frame), "k": plan.k, "n": plan.n, "carriers": plan.carriers,
            "video": plan.video, "frag_bits": E.fragment_nbits(len(frame), plan.k)}
    return out["audio"], out["video"], out["image"], meta


def extract(audio, frames, still, passphrase_key: bytes, meta: dict):
    """Returns (secret_or_None, list of per-carrier status 'ok'/'erased')."""
    plan = Plan(tuple(meta["carriers"]), meta["k"], meta["video"])
    nb = meta["frag_bits"]
    frags, status = [], []
    for name in plan.carriers:
        if name == "audio":
            bits = A.extract(audio, nb, KEYS[name])
        elif name == "video":
            bits = _vid(plan).extract(frames, nb, KEYS[name])
        else:
            bits = I.extract(still, nb, KEYS[name])
        f = E.unprotect(bits)
        frags.append(f)
        status.append("ok" if f is not None else "erased")
    frame = E.join_parity(frags, meta["flen"], plan.k, plan.n)
    if frame is None:
        return None, status
    try:
        return AESGCM(passphrase_key).decrypt(frame[:NONCE_LEN], frame[NONCE_LEN:], None), status
    except (InvalidTag, ValueError):
        return None, status
