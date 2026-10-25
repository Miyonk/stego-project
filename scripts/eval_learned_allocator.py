"""Judge the learned allocator by really hiding at the share it predicts.

Usage: python -m scripts.eval_learned_allocator <split> <n_clips>
Example: python -m scripts.eval_learned_allocator test 30
For each clip and each channel severity it hides at the learned share (any value
0..1) and at the fixed policies, measures the utility, and compares them.
"""
import sys

import numpy as np
import pandas as pd

from src.allocator.detect import load_detect_fn
from src.allocator.learned import (SEVERITY_NAMES, SHARES, LearnedAllocator,
                                   clip_features, utility)
from src.allocator.measure import measure
from src.crypto.secret import derive_key, encode_secret
from src.media_io import read_luma, read_wav

PAYLOAD = 64


def main() -> None:
    split, n_clips = sys.argv[1], int(sys.argv[2])
    detect = load_detect_fn("results/detectors.pkl")
    model = LearnedAllocator.load("results/learned_allocator.pkl")
    key = derive_key("alloc")
    manifest = pd.read_csv("data/manifest.csv")
    manifest = manifest[manifest["split"] == split].sample(frac=1.0, random_state=1).head(n_clips)

    rng = np.random.default_rng(1)
    rows = []
    for i, (_, c) in enumerate(manifest.iterrows(), 1):
        audio, frames = read_wav(c["audio_path"]), read_luma(c["video_path"])
        secret = rng.bytes(PAYLOAD)
        bits = encode_secret(secret, key)
        feats = clip_features(audio, frames, PAYLOAD, detect(audio, frames))
        shares = {sev: model.predict_share(feats, sev) for sev in SEVERITY_NAMES.values()}
        needed = sorted(set(SHARES) | set(shares.values()))
        m = {s: measure(audio, frames, bits, secret, key, s, detect) for s in needed}
        for name, sev in SEVERITY_NAMES.items():
            def u(s):
                r = m[s]
                return utility(r["snr"], r["psnr"], r["stego_risk_f"], r[f"rob_{sev}"])
            chosen = shares[sev]
            rows.append({"clip_id": c["clip_id"], "severity": name, "learned_share": chosen,
                         "learned": u(chosen), "audio_only": u(1.0), "video_only": u(0.0),
                         "fixed_50_50": u(0.5), "best_of_grid": max(u(s) for s in SHARES),
                         "learned_risk": m[chosen]["stego_risk_f"],
                         "learned_rob": m[chosen][f"rob_{sev}"]})
        print(f"[{i}/{len(manifest)}] {c['clip_id']} done", flush=True)

    r = pd.DataFrame(rows)
    r.to_csv(f"results/tables/learned_eval_{split}.csv", index=False)
    boot = np.random.default_rng(0)
    for name in SEVERITY_NAMES:
        g = r[r["severity"] == name]
        print(f"\n=== expected channel: {name} ({len(g)} clips) ===")
        print("mean utility (higher is better):")
        for k in ("best_of_grid", "learned", "audio_only", "video_only", "fixed_50_50"):
            print(f"  {k:13s} {g[k].mean():.4f}")
        print(f"learned share: min {g['learned_share'].min():.2f}  "
              f"mean {g['learned_share'].mean():.2f}  max {g['learned_share'].max():.2f}  "
              f"({g['learned_share'].round(2).nunique()} distinct values)")
        print(f"learned: mean risk {g['learned_risk'].mean():.3f}, "
              f"mean robustness {g['learned_rob'].mean():.3f}")
        for k in ("audio_only", "video_only", "fixed_50_50"):
            d = (g["learned"] - g[k]).to_numpy()
            b = boot.choice(d, size=(2000, len(d))).mean(axis=1)
            print(f"  learned minus {k:12s} {d.mean():+.4f}  "
                  f"[{np.percentile(b, 2.5):+.4f}, {np.percentile(b, 97.5):+.4f}]")


if __name__ == "__main__":
    main()