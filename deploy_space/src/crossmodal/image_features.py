"""Steganalysis features for one still image (the image-carrier detector)."""
import numpy as np
from scipy.fft import dctn

from src.steganalysis.features import DCT_POS, _hist, _moments
from src.video.dct_embed import _blocks


def image_features(img: np.ndarray) -> np.ndarray:
    """DCT-coefficient histograms, pixel residuals and blockiness of a gray image."""
    f = img.astype(np.float64)[None]
    dct = dctn(_blocks(f), axes=(3, 4), norm="ortho")
    feats = [_hist(dct[..., u, v], -160, 160, 40) for u, v in DCT_POS]
    rh = f[:, :, 1:-1] - 0.5 * (f[:, :, :-2] + f[:, :, 2:])
    rv = f[:, 1:-1] - 0.5 * (f[:, :-2] + f[:, 2:])
    feats += [_hist(np.round(r), -6, 7, 13) for r in (rh, rv)]
    feats += [_moments(r) for r in (rh, rv)]
    dx = np.abs(np.diff(f, axis=2))
    dy = np.abs(np.diff(f, axis=1))
    feats.append([dx[:, :, 7::8].mean() / (dx.mean() + 1e-9),
                  dy[:, 7::8, :].mean() / (dy.mean() + 1e-9)])
    return np.concatenate([np.ravel(x) for x in feats])
