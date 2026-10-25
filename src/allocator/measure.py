"""Hide a secret at one audio share and measure quality, detector risk and robustness."""
import numpy as np

from src.allocator.learned import ATTACKS, SEVERITY
from src.channel.attacks import apply_attack
from src.eval.metrics import psnr, snr
from src.pipeline import embed_clip, recover_secret


def measure(audio, frames, bits, secret, key, share, detect) -> dict:
    sa, sv, n_a, n_v = embed_clip(audio, frames, bits, share)
    ra, rv, rf = detect(sa, sv)
    ok = {}
    for name in ATTACKS:
        a2, f2 = apply_attack(name, sa, sv, np.random.default_rng(0))
        ok[name] = recover_secret(a2, f2, n_a, n_v, key) == secret
    out = {"share": float(share),
           "snr": float(snr(audio, sa)) if n_a else np.nan,
           "psnr": float(psnr(frames, sv)) if n_v else np.nan,
           "stego_risk_a": float(ra), "stego_risk_v": float(rv), "stego_risk_f": float(rf)}
    for sev, names in SEVERITY.items():
        out[f"rob_{sev}"] = float(np.mean([ok[n] for n in names]))
    return out
