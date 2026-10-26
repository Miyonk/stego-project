"""Learned allocator: a model that outputs the audio share (any value 0.0 to 1.0).

For many clips we measure, at audio shares 0.0, 0.1, ... 1.0, the quality, the detector
risk and whether the secret survives attacks of three severities (mild, medium,
harsh). Each measurement becomes a utility score. A regressor learns the whole
utility curve (11 values) from the clip's features and the expected channel
severity. At run time one prediction gives the curve, and its peak - refined between
grid points - is the share to use: a continuous value, no embed/detect/adjust rounds.
"""
import pickle

import cv2
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor

SHARES = tuple(round(0.1 * i, 1) for i in range(11))   # audio shares measured
SEVERITY = {0: ("mp3_128", "h264_crf23"),      # mild
            1: ("mp3_64", "h264_crf28"),       # medium
            2: ("mp3_64", "h265_crf28")}       # harsh
SEVERITY_NAMES = {"mild": 0, "medium": 1, "harsh": 2}
ATTACKS = tuple(sorted({a for v in SEVERITY.values() for a in v}))
WEIGHTS = {"quality": 1.0, "robustness": 1.0, "risk": 2.0}
CLIP_FEATURES = ["a_rms", "a_zcr", "a_band", "a_flat", "v_mean", "v_std", "v_motion",
                 "v_texture", "payload_bytes", "risk_a", "risk_v", "risk_f"]
FEATURES = CLIP_FEATURES + ["severity"]


def clip_features(audio, frames, payload_bytes, risks=(0.0, 0.0, 0.0)) -> dict:
    """Cheap numbers describing a clean clip, plus the detectors' view of it."""
    a = audio.astype(np.float64)
    n = len(a) // 512 * 512
    spec = np.abs(np.fft.rfft(a[:n].reshape(-1, 512) * np.hanning(512), axis=1)) + 1e-9
    freqs = np.fft.rfftfreq(512, 1 / 16000)
    band = (freqs >= 1000) & (freqs <= 4000)
    flat = np.exp(np.mean(np.log(spec), axis=1)) / np.mean(spec, axis=1)
    f = frames.astype(np.float64)
    lap = np.mean([np.abs(cv2.Laplacian(fr.astype(np.uint8), cv2.CV_64F)).mean()
                   for fr in frames[::5]])
    return {
        "a_rms": float(np.sqrt(np.mean(a ** 2)) / 32768),
        "a_zcr": float(np.mean(np.abs(np.diff(np.sign(a)))) / 2),
        "a_band": float(spec[:, band].sum() / spec.sum()),
        "a_flat": float(flat.mean()),
        "v_mean": float(f.mean() / 255),
        "v_std": float(f.std() / 255),
        "v_motion": float(np.abs(np.diff(f, axis=0)).mean() / 255),
        "v_texture": float(lap / 255),
        "payload_bytes": float(payload_bytes),
        "risk_a": float(risks[0]), "risk_v": float(risks[1]), "risk_f": float(risks[2]),
    }


def utility(snr, psnr, risk, rob, w=WEIGHTS) -> float:
    """One score: high quality and robustness are good, high detector risk is bad.
    A carrier that was not used is untouched, so it counts as perfect quality."""
    qa = 1.0 if snr is None or not np.isfinite(snr) else float(np.clip((snr - 15) / 15, 0, 1))
    qv = 1.0 if psnr is None or not np.isfinite(psnr) else float(np.clip((psnr - 28) / 14, 0, 1))
    quality = 0.5 * (qa + qv)
    return w["quality"] * quality + w["robustness"] * rob - w["risk"] * risk


def peak_share(shares, utilities) -> float:
    """Share at the peak of a utility curve, refined between grid points.

    At the ends of the range the answer is exactly 0 or 1. Inside the range, a
    parabola through the peak and its two neighbours gives a value between grid points.
    """
    shares = np.asarray(shares, dtype=float)
    u = np.asarray(utilities, dtype=float)
    k = int(np.argmax(u))
    if k == 0 or k == len(u) - 1:
        return float(shares[k])
    denom = u[k - 1] - 2 * u[k] + u[k + 1]
    if denom >= 0:                       # not a clear peak: stay on the grid point
        return float(shares[k])
    offset = 0.5 * (u[k - 1] - u[k + 1]) / denom        # in grid steps, within +/-0.5
    return float(np.clip(shares[k] + offset * (shares[1] - shares[0]), 0.0, 1.0))


def build_xy(df):
    """One training row per (clip, severity): features -> utility at each share."""
    x, y, groups = [], [], []
    for clip_id, g in df.groupby("clip_id"):
        g = g.sort_values("share")
        feats = g.iloc[0][CLIP_FEATURES].to_dict()
        for sev in SEVERITY:
            x.append({**feats, "severity": sev})
            y.append([utility(r.snr, r.psnr, r.stego_risk_f, getattr(r, f"rob_{sev}"))
                      for r in g.itertuples()])
            groups.append(clip_id)
    return pd.DataFrame(x)[FEATURES], np.array(y), np.array(groups)


class LearnedAllocator:
    def __init__(self):
        self.model = None

    def fit(self, x, y):
        self.model = ExtraTreesRegressor(
            n_estimators=300, min_samples_leaf=2, random_state=0, n_jobs=1).fit(x, y)
        return self

    def predict_curve(self, feats: dict, severity: int = 1) -> np.ndarray:
        row = pd.DataFrame([{**feats, "severity": severity}])[FEATURES]
        return self.model.predict(row)[0]

    def predict_share(self, feats: dict, severity: int = 1) -> float:
        return peak_share(SHARES, self.predict_curve(feats, severity))

    def save(self, path):
        with open(path, "wb") as fh:
            pickle.dump(self.model, fh)

    @classmethod
    def load(cls, path):
        obj = cls()
        with open(path, "rb") as fh:
            obj.model = pickle.load(fh)
        return obj