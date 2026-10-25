"""Download the DIV2K validation images (100 high-resolution photos, about 450 MB).

Usage: python -m scripts.download_div2k
Result: data/raw_images/div2k/*.png  (then run: python -m scripts.prepare_images div2k data/raw_images/div2k)
If the download fails, get the zip by hand from https://data.vision.ee.ethz.ch/cvl/DIV2K/
(DIV2K_valid_HR.zip) and unzip it into data/raw_images/div2k. Any folder of photos also works.
"""
import urllib.request
import zipfile
from pathlib import Path

URL = "https://data.vision.ee.ethz.ch/cvl/DIV2K/DIV2K_valid_HR.zip"
DEST = Path("data/raw_images/div2k")


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    zpath = DEST / "DIV2K_valid_HR.zip"
    if not zpath.exists():
        print("downloading", URL)

        def hook(b, bs, total):
            if total > 0 and b % 200 == 0:
                print(f"\r{min(100, b * bs * 100 // total)}%", end="", flush=True)
        urllib.request.urlretrieve(URL, zpath, hook)
        print()
    with zipfile.ZipFile(zpath) as z:
        z.extractall(DEST)
    n = len(list(DEST.rglob("*.png")))
    print(f"ready: {n} images in {DEST}")


if __name__ == "__main__":
    main()
