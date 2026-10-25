"""Image carrier on two image sets, with the checks needed before trusting the numbers.

Usage: python -m scripts.image_cross_dataset <datasetA> <datasetB> [n_per_dataset=300] [n_bits=1000] [n_seeds=3]
(datasets must be prepared first with scripts.prepare_images)

What it does
  * leakage check: no source photo / actor appears in both the train and the test part
  * repeats everything with several random seeds (different images, payload bits, keys, detector seed)
  * robustness: bit error rate after JPEG, picture quality (mean +- std over seeds)
  * detection AUC, trained on one dataset and tested on the same and the other one (mean +- std)
  * control: the same detector trained on SHUFFLED labels must give AUC close to 0.5
"""
import sys
from concurrent.futures import ProcessPoolExecutor

import cv2
import numpy as np
import pandas as pd

from src.crossmodal import image_carrier as I
from src.crossmodal.image_features import image_features
from src.steganalysis.detectors import Detector, auc

QUALITIES = (None, 75, 30, 10)


def group_of(name, source):
    """Unit that must not be shared between train and test."""
    return str(source).split("_")[0] if name == "cremad" else str(source)


def load(name, n, seed):
    df = pd.read_csv(f"data/images/{name}.csv")
    parts = []
    for s in ("train", "test"):
        d = df[df.split == s]
        parts.append(d.sample(min(len(d), n if s == "train" else max(1, n // 3)), random_state=seed))
    return pd.concat(parts)


def leakage_report(name, df):
    g = df.assign(group=[group_of(name, s) for s in df.source])
    tr, te = set(g[g.split == "train"].group), set(g[g.split == "test"].group)
    both = tr & te
    return len(tr), len(te), len(both)


def one(args):
    path, split, nb, seed = args
    rng = np.random.default_rng(seed)
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    bits, key = rng.integers(0, 2, nb), int(rng.integers(1, 10**6))
    s = I.embed(img, bits, key)
    ber = [float(np.mean(I.extract(s if q is None else I.jpeg(s, q), nb, key) != bits)) for q in QUALITIES]
    psnr = 10 * np.log10(255 ** 2 / max(np.mean((img.astype(float) - s) ** 2), 1e-9))
    return dict(split=split, fc=image_features(img), fs=image_features(s), psnr=psnr, ber=ber)


def run_dataset(name, n, nb, seed, ex):
    df = load(name, n, seed)
    jobs = [(r.path, r.split, nb, seed * 100_000 + i) for i, r in enumerate(df.itertuples())]
    return list(ex.map(one, jobs, chunksize=4))


def xy(recs, split):
    r = [x for x in recs if x["split"] == split]
    return np.r_[[x["fc"] for x in r], [x["fs"] for x in r]], np.r_[np.zeros(len(r)), np.ones(len(r))]


def main():
    a, b = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    nb = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
    seeds = int(sys.argv[5]) if len(sys.argv) > 5 else 3

    print("\nLeakage check (train and test must share nothing):")
    for name in (a, b):
        ntr, nte, both = leakage_report(name, pd.read_csv(f"data/images/{name}.csv"))
        print(f"  {name}: {ntr} train groups, {nte} test groups, shared between them: {both}"
              + ("   <-- PROBLEM" if both else "   ok"))

    rob, auc_rows, ctrl = [], [], []
    with ProcessPoolExecutor() as ex:
        for seed in range(seeds):
            data = {name: run_dataset(name, n, nb, seed, ex) for name in (a, b)}
            det, shuf = {}, {}
            for name in (a, b):
                X, y = xy(data[name], "train")
                det[name] = Detector(seed).fit(X, y)
                shuf[name] = Detector(seed).fit(X, np.random.default_rng(seed).permutation(y))
                d = pd.DataFrame([{"psnr": r["psnr"], **{f"ber_{q}": v for q, v in zip(QUALITIES, r["ber"])}}
                                  for r in data[name]])
                rob.append(dict(seed=seed, dataset=name, psnr_db=d.psnr.mean(),
                                **{f"BER {'no JPEG' if q is None else f'JPEG q{q}'}": d[f"ber_{q}"].mean()
                                   for q in QUALITIES}))
            for tr in (a, b):
                for te in (a, b):
                    X, y = xy(data[te], "test")
                    auc_rows.append(dict(seed=seed, trained_on=tr, tested_on=te, auc=auc(y, det[tr].score(X))))
                    ctrl.append(dict(seed=seed, trained_on=tr, tested_on=te, auc=auc(y, shuf[tr].score(X))))
            print(f"seed {seed + 1}/{seeds} done", flush=True)

    ms = lambda s: f"{s.mean():.4f} +- {s.std(ddof=1) if len(s) > 1 else 0:.4f}"
    r = pd.DataFrame(rob).drop(columns="seed").groupby("dataset").agg(ms).T
    print(f"\nImage carrier, {nb} bits per image, {seeds} seeds (mean +- std):\n\n{r.to_string()}")
    for title, rows, tag in (("Detection AUC (0.5 = cannot tell apart, 1.0 = always caught)", auc_rows, "real"),
                             ("CONTROL: detector trained on shuffled labels (should be about 0.5)", ctrl, "control")):
        t = pd.DataFrame(rows).groupby(["trained_on", "tested_on"]).auc.agg(ms).unstack()
        print(f"\n{title}:\n\n{t.to_string()}")
        t.to_csv(f"results/tables/image_auc_{tag}_{a}_{b}.csv")
    r.to_csv(f"results/tables/image_robustness_{a}_{b}.csv")


if __name__ == "__main__":
    main()