"""Is the motion-aware embedder harder to detect than the standard one?

For each embedder a detector is trained on that embedder's own stego (a fair, matched test),
then also tried on the other embedder's stego (cross test). All numbers are on unseen test clips.
Usage: python -m scripts.compare_stealth [n_train_clips=150] [n_test_clips=60] [n_bits=656]
"""
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from src.media_io import read_luma
from src.steganalysis.detectors import Detector, auc
from src.steganalysis.features import video_features
from src.video import dct_embed as S
from src.video import motion_embed as M

NB = 656


def one(args):
    path, i = args
    rng = np.random.default_rng(i)
    fr = read_luma(path)
    bits = rng.integers(0, 2, NB)
    return (video_features(fr), video_features(S.embed(fr, bits, int(rng.integers(1, 10**6)))),
            video_features(M.embed(fr, bits, int(rng.integers(1, 10**6)))))


def feats(paths, seed):
    with ProcessPoolExecutor() as ex:
        out = list(ex.map(one, [(p, seed + i) for i, p in enumerate(paths)], chunksize=4))
    return [np.stack([o[k] for o in out]) for k in range(3)]       # clean, standard, motion


def main():
    global NB
    ntr = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    nte = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    NB = int(sys.argv[3]) if len(sys.argv) > 3 else 656
    man = pd.read_csv("data/manifest.csv")
    tr = man[man.split == "train"].sample(ntr, random_state=0).video_path.tolist()
    te = man[man.split == "test"].sample(nte, random_state=0).video_path.tolist()
    ctr, str_, mtr = feats(tr, 0)
    cte, ste, mte = feats(te, 10_000)
    rows = {}
    for name, xtr in (("standard", str_), ("motion", mtr)):
        det = Detector(0).fit(np.r_[ctr, xtr], np.r_[np.zeros(len(ctr)), np.ones(len(xtr))])
        for tname, xte in (("standard", ste), ("motion", mte)):
            y = np.r_[np.zeros(len(cte)), np.ones(len(xte))]
            rows.setdefault(f"detector trained on {name}", {})[f"tested on {tname} stego"] = round(
                auc(y, det.score(np.r_[cte, xte])), 3)
    out = pd.DataFrame(rows).T
    print(f"\nDetection AUC (0.5 = cannot tell apart, 1.0 = always caught), {NB} bits, "
          f"{ntr} train / {nte} test clips:\n")
    print(out.to_string())
    out.to_csv("results/tables/stealth_standard_vs_motion.csv")


if __name__ == "__main__":
    main()