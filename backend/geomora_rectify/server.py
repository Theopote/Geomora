from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from geomora_detect.pipeline import detect_facade

from .pipeline import parse_corners, rectify_image

app = FastAPI(title="Geomora Perception", version="0.4.0")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "geomora-perception",
        "status": "ok",
        "health": "/health",
        "rectify": "POST /rectify",
        "detect": "POST /detect",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "geomora-perception"}


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def is_image_upload(upload: UploadFile) -> bool:
    if upload.content_type and upload.content_type.startswith("image/"):
        return True
    suffix = Path(upload.filename or "").suffix.lower()
    return suffix in IMAGE_EXTENSIONS


@app.post("/rectify")
async def rectify(
    image: UploadFile = File(...),
    corners: str | None = Form(default=None),
) -> JSONResponse:
    if not is_image_upload(image):
        raise HTTPException(status_code=400, detail="Upload must be an image file")

    suffix = Path(image.filename or "upload.jpg").suffix or ".jpg"
    with tempfile.TemporaryDirectory(prefix="geomora_rectify_") as temp_dir:
        input_path = Path(temp_dir) / f"input{suffix}"
        output_path = Path(temp_dir) / "rectified.jpg"
        input_path.write_bytes(await image.read())

        try:
            corner_points = parse_corners(corners)
            result = rectify_image(
                str(input_path),
                output_path=str(output_path),
                corners=corner_points,
                return_base64=True,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:  # pragma: no cover - safety net
            raise HTTPException(status_code=500, detail=str(error)) from error

        return JSONResponse(result.to_dict())


@app.post("/detect")
async def detect(image: UploadFile = File(...)) -> JSONResponse:
    if not is_image_upload(image):
        raise HTTPException(status_code=400, detail="Upload must be an image file")

    suffix = Path(image.filename or "upload.jpg").suffix or ".jpg"
    with tempfile.TemporaryDirectory(prefix="geomora_detect_") as temp_dir:
        input_path = Path(temp_dir) / f"input{suffix}"
        input_path.write_bytes(await image.read())

        try:
            result = detect_facade(str(input_path), return_overlay=True)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:  # pragma: no cover - safety net
            raise HTTPException(status_code=500, detail=str(error)) from error

        return JSONResponse(result.to_dict())


def main() -> None:
    import uvicorn

    uvicorn.run("geomora_rectify.server:app", host="127.0.0.1", port=8765, reload=False)


if __name__ == "__main__":
    main()
