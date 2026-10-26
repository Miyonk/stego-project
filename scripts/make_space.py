"""Assemble a ready-to-upload deployment folder (for a Hugging Face Docker Space).

Usage: python -m scripts.make_space [n_demo_clips=24]
Creates deploy_space/ containing: Dockerfile, README.md (Space settings), requirements.txt
(pinned to the versions installed HERE, so the saved models load the same way), the code,
the React source, a small demo set of CREMA-D clips, and the trained detector / allocator files.
"""
import shutil
import sys
from importlib import metadata
from pathlib import Path

import pandas as pd

OUT = Path("deploy_space")
PACKAGES = {  # import name on pip -> pip name to install in the container
    "numpy": "numpy", "scipy": "scipy", "pandas": "pandas", "scikit-learn": "scikit-learn",
    "reedsolo": "reedsolo", "cryptography": "cryptography", "soundfile": "soundfile",
    "fastapi": "fastapi", "uvicorn": "uvicorn", "python-multipart": "python-multipart",
    "pydantic": "pydantic", "pyyaml": "pyyaml",
}
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules", "dist", ".venv")

DOCKERFILE = """\
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:{py}-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \\
    && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
USER user
ENV PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user src ./src
COPY --chown=user api ./api
COPY --chown=user configs ./configs
COPY --chown=user data ./data
COPY --chown=user results ./results
COPY --chown=user --from=web /web/dist ./frontend/dist
EXPOSE 7860
CMD ["uvicorn", "api.app_deploy:app", "--host", "0.0.0.0", "--port", "7860"]
"""

README = """\
---
title: Cross-Modal Stego Lab
emoji: 🔐
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Cross-Modal Stego Lab

Adaptive cross-modal steganography demo: hide an encrypted secret in audio, video and an image,
send it through real compression, and read it back. Also: hide a secret in your own photo.
Demo clips are a small sample of CREMA-D (Open Database License, please credit the CREMA-D authors).
This is a research demo. Do not hide anything you cannot afford to lose.
"""


def pinned():
    lines = []
    for pip_name in PACKAGES.values():
        lines.append(f"{pip_name}=={metadata.version(pip_name)}")
    try:
        v = metadata.version("opencv-python")
    except metadata.PackageNotFoundError:
        v = metadata.version("opencv-python-headless")
    lines.append(f"opencv-python-headless=={v}")
    return "\n".join(lines) + "\n"


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for d in ("src", "api", "configs", "frontend"):
        shutil.copytree(d, OUT / d, ignore=IGNORE)
    (OUT / "frontend" / ".env.production").write_text("VITE_API=\n")     # same-origin API
    # demo clips: spread over actors and emotions from the test split
    man = pd.read_csv("data/manifest.csv")
    test = man[man.split == "test"].sample(frac=1, random_state=0)
    pick = test.groupby("emotion", group_keys=False).head(max(1, n // test.emotion.nunique())).head(n)
    for sub in ("processed", "raw"):
        (OUT / "data" / sub).mkdir(parents=True)
    for r in pick.itertuples():
        shutil.copy(r.video_path, OUT / "data" / "processed")
        shutil.copy(r.audio_path, OUT / "data" / "processed")
        shutil.copy(Path("data/raw") / f"{r.clip_id}.flv", OUT / "data" / "raw")
    pick.to_csv(OUT / "data" / "manifest.csv", index=False)
    (OUT / "results").mkdir()
    for f in ("detectors.pkl", "learned_allocator.pkl"):
        if Path("results", f).exists():
            shutil.copy(Path("results", f), OUT / "results" / f)
    py = f"{sys.version_info.major}.{sys.version_info.minor}"
    (OUT / "Dockerfile").write_text(DOCKERFILE.format(py=py))
    (OUT / "README.md").write_text(README, encoding="utf-8")
    (OUT / "requirements.txt").write_text(pinned())
    (OUT / ".gitignore").write_text("__pycache__/\napi_out/\nnode_modules/\n")
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file()) / 1e6
    print(f"deploy_space ready: {len(pick)} demo clips, {size:.0f} MB, Python {py}")
    print((OUT / "requirements.txt").read_text())


if __name__ == "__main__":
    main()
