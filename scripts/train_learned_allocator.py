"""Train the learned allocator (continuous audio share) from results/alloc_train.csv.

Usage: python -m scripts.train_learned_allocator
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from src.allocator.learned import SEVERITY_NAMES, SHARES, LearnedAllocator, build_xy, peak_share


def regret(model_curves, true_curves):
    """How much utility is lost by trusting the predicted curve (lower is better)."""
    out = []
    for pred, true in zip(model_curves, true_curves):
        pick = peak_share(SHARES, pred)
        nearest = int(np.argmin(np.abs(np.array(SHARES) - pick)))
        out.append(true.max() - true[nearest])
    return np.array(out)


def main() -> None:
    df = pd.read_csv("results/alloc_train.csv")
    x, y, groups = build_xy(df)
    print(f"{df['clip_id'].nunique()} clips -> {len(x)} training rows "
          f"(one per clip and severity), {y.shape[1]} shares each")

    # honest check on clips the model has not seen: how much utility does it lose?
    pred = np.zeros_like(y)
    for tr, te in GroupKFold(n_splits=5).split(x, y, groups):
        pred[te] = LearnedAllocator().fit(x.iloc[tr], y[tr]).model.predict(x.iloc[te])
    print("\ncross-validated regret (utility lost vs the best share; lower is better):")
    print(f"  learned allocator   {regret(pred, y).mean():.4f}")
    print(f"  always audio_only   {(y.max(axis=1) - y[:, -1]).mean():.4f}")
    print(f"  always video_only   {(y.max(axis=1) - y[:, 0]).mean():.4f}")
    print(f"  always 50/50        {(y.max(axis=1) - y[:, len(SHARES) // 2]).mean():.4f}")

    model = LearnedAllocator().fit(x, y)
    model.save("results/learned_allocator.pkl")
    print("\nshares the model picks (on the training clips):")
    for name, sev in SEVERITY_NAMES.items():
        rows = x[x["severity"] == sev]
        picks = np.array([peak_share(SHARES, c) for c in model.model.predict(rows)])
        print(f"  {name:7s} min {picks.min():.2f}  mean {picks.mean():.2f}  max {picks.max():.2f}  "
              f"({len(np.unique(picks.round(2)))} distinct values)")
    print("\nsaved results/learned_allocator.pkl")


if __name__ == "__main__":
    main()