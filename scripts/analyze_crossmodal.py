"""Summarise results/crossmodal_<split>.csv into a recovery table, a cost table and a figure."""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

split = sys.argv[1] if len(sys.argv) > 1 else "test"
df = pd.read_csv(f"results/crossmodal_{split}.csv")
rec = df.pivot_table(index="strategy", columns="scenario", values="recovered", aggfunc="mean")
order = ["clean", "mild", "medium", "kill_audio", "kill_video", "kill_image",
         "kill_audio+video", "kill_audio+image", "kill_video+image"]
rec = rec[order].round(2)
rec["worst_single_kill"] = rec[["kill_audio", "kill_video", "kill_image"]].min(axis=1)
print("\nShare of clips where the secret was recovered:\n")
print(rec.to_string())
cost = df.groupby("strategy")[["bits_total", "psnr_video", "psnr_image"]].mean().round(1)
print("\nPrice paid (bits hidden in total, average picture quality):\n")
print(cost.to_string())
import os
os.makedirs("results/tables", exist_ok=True); os.makedirs("results/figures", exist_ok=True)
rec.to_csv(f"results/tables/crossmodal_recovery_{split}.csv")
cost.to_csv(f"results/tables/crossmodal_cost_{split}.csv")
ax = rec[order].T.plot(kind="bar", figsize=(11, 5), width=0.85)
ax.set_ylabel("secret recovered (share of clips)"); ax.set_ylim(0, 1.05)
ax.set_title("Surviving the loss of a whole carrier"); plt.xticks(rotation=30, ha="right")
plt.tight_layout(); plt.savefig(f"results/figures/crossmodal_recovery_{split}.png", dpi=150)
print(f"\nsaved figure results/figures/crossmodal_recovery_{split}.png")
