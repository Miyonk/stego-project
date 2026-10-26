"""Upload your own photo, hide a secret in it, look at the result, and read it back."""
import uuid

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from api.main import OUT
from src import photo

router = APIRouter(prefix="/photo")
MAX_UPLOAD = 15 * 1024 * 1024


def decode_upload(data: bytes) -> np.ndarray:
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "that file is not a readable image (use JPG, PNG, BMP or WEBP)")
    return img


async def read_upload(f: UploadFile) -> bytes:
    data = await f.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(400, "the image is larger than 15 MB")
    return data


@router.get("/options")
def options():
    return {"strengths": [
        {"name": "robust", "note": "survives heavy JPEG, but the picture changes more"},
        {"name": "balanced", "note": "good default"},
        {"name": "subtle", "note": "least visible, but can be lost under heavy compression"}],
        "max_secret_bytes": photo.MAX_SECRET, "max_side": photo.MAX_SIDE}


@router.post("/embed")
async def embed(file: UploadFile = File(...), secret: str = Form(...),
                passphrase: str = Form(...), strength: str = Form("balanced")):
    img = decode_upload(await read_upload(file))
    if not passphrase:
        raise HTTPException(400, "a passphrase is required")
    try:
        stego, info = photo.embed(img, secret, passphrase, strength)
    except ValueError as e:
        raise HTTPException(400, str(e))
    original = photo.prepare(img)
    job = "p" + uuid.uuid4().hex[:11]
    folder = OUT / job
    folder.mkdir()
    cv2.imwrite(str(folder / "original.png"), original)
    cv2.imwrite(str(folder / "stego.png"), stego)
    cv2.imwrite(str(folder / "difference.png"), photo.difference_map(original, stego))
    info.update(job_id=job, strength=strength, scaled=original.shape != img.shape,
                original_size=[int(img.shape[1]), int(img.shape[0])])
    return info


@router.post("/extract")
async def extract(passphrase: str = Form(...), file: UploadFile | None = File(None),
                  job_id: str = Form(""), strength: str = Form("auto"),
                  jpeg_quality: int = Form(0)):
    """Read the secret from an uploaded image, or from a job's stego image.
    jpeg_quality (1-100) first re-compresses the image, to show it surviving sharing."""
    if file is not None and file.filename:
        img = decode_upload(await read_upload(file))
    elif job_id:
        path = OUT / job_id / "stego.png"
        if not job_id.startswith("p") or not path.exists():
            raise HTTPException(404, "unknown job_id")
        img = cv2.imread(str(path))
    else:
        raise HTTPException(400, "upload an image or give a job_id")
    if 1 <= jpeg_quality <= 100:
        img = cv2.imdecode(cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])[1], 1)
    names = list(photo.STRENGTH) if strength == "auto" else [strength]
    for name in names:
        secret = photo.extract(img, passphrase, name)
        if secret is not None:
            return {"recovered": True, "secret": secret, "strength": name, "jpeg_quality": jpeg_quality or None}
    return {"recovered": False, "secret": None, "strength": None, "jpeg_quality": jpeg_quality or None}


@router.get("/file/{job_id}/{name}")
def get_file(job_id: str, name: str):
    if not job_id.startswith("p") or name not in ("original", "stego", "difference"):
        raise HTTPException(404, "not found")
    path = OUT / job_id / f"{name}.png"
    if not path.exists():
        raise HTTPException(404, "not found")
    return FileResponse(path, media_type="image/png",
                        filename=f"{job_id}_{name}.png" if name == "stego" else None)
