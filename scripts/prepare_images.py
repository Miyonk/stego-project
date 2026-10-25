"""Turn a folder of photos (or the CREMA-D clips) into a fixed-format image dataset.

Usage:
  python -m scripts.prepare_images cremad                      # one still per CREMA-D clip
  python -m scripts.prepare_images div2k data/raw_images/div2k [crops_per_image=4]
  python -m scripts.prepare_images <any_name> <folder_of_photos> [crops_per_image=4]
Output: data/images/<name>/*.png (384x384 gray) and data/images/<name>.csv (path, source, split).
The split is made per source photo, so crops of one photo never land in both train and test.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from src.crossmodal import image_carrier as I

SIZE = I.SIZE
EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".pgm"}


def split_of(i, n):
    f = i / max(1, n)
    return "train" if f < 0.7 else "val" if f < 0.85 else "test"


def from_cremad(out):
    man = pd.read_csv("data/manifest.csv")
    rows = []
    for _, r in man.iterrows():
        raw = Path("data/raw") / f"{r.clip_id}.flv"
        if not raw.exists():
            continue
        p = out / f"{r.clip_id}.png"
        if not p.exists():
            cv2.imwrite(str(p), I.load_still(str(raw)))
        rows.append(dict(path=str(p), source=r.clip_id, split=r.split))
    return rows


def from_folder(folder, out, crops):
    files = sorted(p for p in Path(folder).rglob("*") if p.suffix.lower() in EXT)
    if not files:
        sys.exit(f"no images found in {folder}")
    rng = np.random.default_rng(0)
    rows = []
    for i, f in enumerate(files):
        img = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        h, w = img.shape
        if min(h, w) < SIZE:                      # too small: scale up so a crop fits
            s = SIZE / min(h, w)
            img = cv2.resize(img, (int(np.ceil(w * s)), int(np.ceil(h * s))))
            h, w = img.shape
        for c in range(crops):
            y, x = int(rng.integers(0, h - SIZE + 1)), int(rng.integers(0, w - SIZE + 1))
            p = out / f"{f.stem}_{c}.png"
            cv2.imwrite(str(p), img[y:y + SIZE, x:x + SIZE])
            rows.append(dict(path=str(p), source=f.stem, split=split_of(i, len(files))))
    return rows


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    name = sys.argv[1]
    out = Path("data/images") / name
    out.mkdir(parents=True, exist_ok=True)
    if name == "cremad":
        rows = from_cremad(out)
    else:
        if len(sys.argv) < 3:
            sys.exit("give the folder of photos: python -m scripts.prepare_images NAME FOLDER")
        rows = from_folder(sys.argv[2], out, int(sys.argv[3]) if len(sys.argv) > 3 else 4)
    df = pd.DataFrame(rows)
    df.to_csv(f"data/images/{name}.csv", index=False)
    print(f"{name}: {len(df)} images, split counts {df.split.value_counts().to_dict()}")


if __name__ == "__main__":
    main()
