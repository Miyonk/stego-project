"""Still-image carrier: the same DCT/QIM idea as the video embedder, on one picture."""
import subprocess

import cv2
import numpy as np

from src.video import dct_embed as V

SIZE = 384
REPS = 8
DELTA = 64.0


def load_still(raw_video_path: str, size: int = SIZE, t: float = 1.0) -> np.ndarray:
    """Grab one frame from the original clip, centre-crop to a square, make it size x size gray."""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(raw_video_path), "-frames:v", "1",
         "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
    img = cv2.imdecode(np.frombuffer(out, np.uint8), cv2.IMREAD_GRAYSCALE)
    h, w = img.shape
    s = min(h, w)
    img = img[(h - s) // 2:(h - s) // 2 + s, (w - s) // 2:(w - s) // 2 + s]
    return cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)


def capacity_bits(size: int = SIZE, reps: int = REPS) -> int:
    return V.capacity_bits((1, size, size), reps)


def embed(img: np.ndarray, bits, key: int, reps: int = REPS, delta: float = DELTA) -> np.ndarray:
    return V.embed(img[None], bits, key, delta=delta, reps=reps)[0]


def extract(img: np.ndarray, nbits: int, key: int, reps: int = REPS, delta: float = DELTA):
    return V.extract(img[None], nbits, key, delta=delta, reps=reps)


def jpeg(img: np.ndarray, quality: int) -> np.ndarray:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    return cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
