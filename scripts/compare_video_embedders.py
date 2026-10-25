"""Standard vs motion-aware video embedder: bit error rate under real codecs, plus picture quality.

Usage: python -m scripts.compare_video_embedders <split> <n_clips> [n_bits=656]
"""
import sys

import numpy as np
import pandas as pd

from src.channel.attacks import apply_attack
from src.eval.metrics import psnr, ssim
from src.media_io import read_luma
from src.video import dct_embed as S
from src.video import motion_embed as M

split, n = sys.argv[1], int(sys.argv[2])
nb = int(sys.argv[3]) if len(sys.argv) > 3 else 656
man = pd.read_csv("data/manifest.csv")
man = man[man.split == split].sample(frac=1, random_state=3).head(n)
atk = ["none", "h264_crf23", "h264_crf28", "h265_crf23", "h265_crf28", "h265_crf32", "drop_10", "resize_75"]
rng = np.random.default_rng(0)
ber = {m: {a: [] for a in atk} for m in ("standard", "motion")}
qual = {m: [] for m in ber}
for _, r in man.iterrows():
    fr, bits = read_luma(r.video_path), rng.integers(0, 2, nb)
    for name, mod in (("standard", S), ("motion", M)):
        sv = mod.embed(fr, bits, 5)
        qual[name].append((psnr(fr, sv), ssim(fr, sv)))
        for a in atk:
            f2 = apply_attack(a, np.zeros(16000, dtype=np.int16), sv, np.random.default_rng(0))[1]
            ber[name][a].append(float(np.mean(mod.extract(f2, nb, 5) != bits)))
mean = pd.DataFrame({m: {a: np.mean(v) for a, v in d.items()} for m, d in ber.items()})
bad = pd.DataFrame({m: {a: np.mean(np.array(v) > 0.06) for a, v in d.items()} for m, d in ber.items()})
print("\nMean bit error rate:\n", mean.round(4).to_string())
print("\nShare of clips with BER above 6% (error correction usually fails):\n", bad.round(2).to_string())
for m in qual:
    print(f"{m:9s} PSNR {np.mean(qual[m], axis=0)[0]:.2f}  SSIM {np.mean(qual[m], axis=0)[1]:.3f}")
mean.to_csv(f"results/tables/video_embedders_{split}.csv")
