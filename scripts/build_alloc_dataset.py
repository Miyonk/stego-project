"""Measure quality, detector risk and robustness for many clips and audio shares.

Usage: python -m scripts.build_alloc_dataset <split> <n_clips> [payload_bytes]
Example: python -m scripts.build_alloc_dataset train 100
Writes results/alloc_<split>.csv and can be stopped and restarted (it resumes).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.allocator.detect import load_detect_fn
from src.allocator.learned import SHARES, clip_features
from src.allocator.measure import measure
from src.crypto.secret import derive_key, encode_secret
from src.media_io import read_luma, read_wav


def main() -> None:
    split = sys.argv[1]
    n_clips = int(sys.argv[2])
    payload = int(sys.argv[3]) if len(sys.argv) > 3 else 64
    out = Path(f"results/alloc_{split}.csv")
    detect = load_detect_fn("results/detectors.pkl")
    key = derive_key("alloc")

    manifest = pd.read_csv("data/manifest.csv")
    manifest = manifest[manifest["split"] == split].sample(frac=1.0, random_state=0)
    clips = manifest.head(n_clips)

    done, rows = set(), []
    if out.exists():
        old = pd.read_csv(out)
        rows = old.to_dict("records")
        done = set(old["clip_id"])
        print(f"resuming: {len(done)} clips already done")

    rng = np.random.default_rng(0)
    for i, (_, c) in enumerate(clips.iterrows(), 1):
        secret = rng.bytes(payload)            # drawn first so a resume stays reproducible
        if c["clip_id"] in done:
            continue
        audio, frames = read_wav(c["audio_path"]), read_luma(c["video_path"])
        bits = encode_secret(secret, key)
        feats = clip_features(audio, frames, payload, detect(audio, frames))
        for share in SHARES:
            rows.append({"clip_id": c["clip_id"], "split": split, **feats,
                         **measure(audio, frames, bits, secret, key, share, detect)})
        pd.DataFrame(rows).to_csv(out, index=False)
        print(f"[{i}/{len(clips)}] {c['clip_id']} done", flush=True)
    print(f"saved {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()