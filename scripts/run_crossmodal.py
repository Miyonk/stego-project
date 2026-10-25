"""Compare single-carrier, split and erasure-coded strategies when whole carriers get destroyed.

Usage: python -m scripts.run_crossmodal <split> <n_clips> [payload_bytes=64]
Writes results/crossmodal_<split>.csv (one row per clip x strategy x scenario).
"""
import sys
import time

import numpy as np
import pandas as pd

from src.channel import attacks as T
from src.crossmodal import image_carrier as I
from src.crossmodal.pipeline3 import PLANS, embed, extract
from src.crypto.secret import derive_key
from src.eval.metrics import psnr
from src.media_io import read_luma, read_wav

# (audio attack, video attack, image jpeg quality)  None = untouched
SCENARIOS = {
    "clean":         (None, None, None),
    "mild":          ("mp3_128", "h264_crf23", 75),
    "medium":        ("mp3_64", "h264_crf28", 30),
    "kill_audio":    ("mp3_32", None, None),
    "kill_video":    (None, "h265_crf35", None),
    "kill_image":    (None, None, 5),
    "kill_audio+video": ("mp3_32", "h265_crf35", None),
    "kill_audio+image": ("mp3_32", None, 5),
    "kill_video+image": (None, "h265_crf35", 5),
}


def channel(sa, sf, si, scen, rng):
    a, v, j = SCENARIOS[scen]
    if a:
        sa = T.mp3(sa, int(a.split("_")[1]))
    if v:
        sf = T.apply_attack(v, sa, sf, rng)[1]
    if j:
        si = I.jpeg(si, j)
    return sa, sf, si


def main():
    split, n = sys.argv[1], int(sys.argv[2])
    nbytes = int(sys.argv[3]) if len(sys.argv) > 3 else 64
    man = pd.read_csv("data/manifest.csv")
    man = man[man.split == split].sample(frac=1, random_state=0).head(n)
    key = derive_key("cross-modal-demo")
    rng = np.random.default_rng(0)
    rows, t0 = [], time.time()
    for ci, (_, r) in enumerate(man.iterrows()):
        au, fr = read_wav(r.audio_path), read_luma(r.video_path)
        still = I.load_still(f"data/raw/{r.clip_id}.flv")
        secret = rng.integers(0, 256, nbytes, dtype=np.uint8).tobytes()
        for name, plan in PLANS.items():
            sa, sf, si, meta = embed(au, fr, still, secret, key, plan)
            q = dict(psnr_video=psnr(fr, sf) if "video" in plan.carriers else np.nan,
                     psnr_image=psnr(still[None], si[None]) if "image" in plan.carriers else np.nan,
                     bits_total=meta["frag_bits"] * plan.n)
            for scen in SCENARIOS:
                a2, f2, i2 = channel(sa, sf, si, scen, np.random.default_rng(1))
                got, status = extract(a2, f2, i2, key, meta)
                rows.append(dict(clip_id=r.clip_id, strategy=name, scenario=scen,
                                 recovered=int(got == secret), erased="".join(s[0] for s in status),
                                 **q))
        print(f"clip {ci + 1}/{len(man)}  {time.time() - t0:.0f}s", flush=True)
        pd.DataFrame(rows).to_csv(f"results/crossmodal_{split}.csv", index=False)
    print("saved results/crossmodal_%s.csv" % split)


if __name__ == "__main__":
    main()
