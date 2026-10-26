import cv2
import numpy as np
import pytest

from src import photo


def _img(h=320, w=320, seed=0):
    rng = np.random.default_rng(seed)
    base = cv2.GaussianBlur(rng.integers(0, 255, (h, w, 3)).astype(np.uint8), (0, 0), 6)
    return base


def test_roundtrip_all_strengths():
    img = _img()
    for st in photo.STRENGTH:
        s, info = photo.embed(img, "hello, secret world", "pw", st)
        assert s.shape == img.shape and info["reps"] >= 2
        assert photo.extract(s, "pw", st) == "hello, secret world"


def test_wrong_passphrase_and_png_jpeg():
    img = _img()
    s, _ = photo.embed(img, "abc", "right", "balanced")
    assert photo.extract(s, "wrong", "balanced") is None
    j = cv2.imdecode(cv2.imencode(".jpg", s, [cv2.IMWRITE_JPEG_QUALITY, 60])[1], 1)
    assert photo.extract(j, "right", "balanced") == "abc"


def test_errors_are_readable():
    with pytest.raises(ValueError):
        photo.embed(_img(), "x" * 101, "pw")
    with pytest.raises(ValueError):
        photo.embed(_img(64, 64), "x", "pw")
    with pytest.raises(ValueError):
        photo.embed(_img(), "", "pw")
