from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from geomora_detect.pipeline import SUPPORTED_METHODS, detect_facade
from geomora_capture.video_frames import extract_frames
from geomora_multiview.pipeline import fuse_openings, multiview_capabilities, register_views

from .pipeline import parse_corners, rectify_image

app = FastAPI(title="Geomora Perception", version="0.19.0")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "geomora-perception",
        "status": "ok",
        "health": "/health",
        "rectify": "POST /rectify",
        "detect": "POST /detect",
        "detect_capabilities": "GET /detect/capabilities",
        "video_extract_frames": "POST /video/extract_frames",
        "multiview_register": "POST /multiview/register",
        "multiview_fuse": "POST /multiview/fuse",
        "multiview_capabilities": "GET /multiview/capabilities",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "geomora-perception"}


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


def is_video_upload(upload: UploadFile) -> bool:
    if upload.content_type and upload.content_type.startswith("video/"):
        return True
    suffix = Path(upload.filename or "").suffix.lower()
    return suffix in VIDEO_EXTENSIONS


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
async def detect(
    image: UploadFile = File(...),
    method: str = Form(default="auto"),
) -> JSONResponse:
    if not is_image_upload(image):
        raise HTTPException(status_code=400, detail="Upload must be an image file")

    suffix = Path(image.filename or "upload.jpg").suffix or ".jpg"
    with tempfile.TemporaryDirectory(prefix="geomora_detect_") as temp_dir:
        input_path = Path(temp_dir) / f"input{suffix}"
        input_path.write_bytes(await image.read())

        try:
            result = detect_facade(str(input_path), method=method, return_overlay=True)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:  # pragma: no cover - safety net
            raise HTTPException(status_code=500, detail=str(error)) from error

        return JSONResponse(result.to_dict())


@app.get("/detect/capabilities")
def detect_capabilities() -> dict[str, object]:
    from geomora_detect.yolo_detector import model_available

    return {
        "methods": list(SUPPORTED_METHODS),
        "yolo_available": model_available(),
        "scale_hint": True,
        "recommended_workflow": [
            "Load image or video frame",
            "Rectify facade",
            "Detect elements",
            "Review overlay",
            "Rationalize",
            "Generate",
        ],
    }


@app.post("/video/extract_frames")
async def video_extract_frames(
    video: UploadFile = File(...),
    max_frames: int = Form(default=12),
) -> JSONResponse:
    import base64

    if not is_video_upload(video):
        raise HTTPException(status_code=400, detail="Upload must be a video file")

    suffix = Path(video.filename or "upload.mp4").suffix or ".mp4"
    with tempfile.TemporaryDirectory(prefix="geomora_video_") as temp_dir:
        input_path = Path(temp_dir) / f"input{suffix}"
        input_path.write_bytes(await video.read())

        try:
            result = extract_frames(
                str(input_path),
                output_dir=str(Path(temp_dir) / "frames"),
                max_frames=max_frames,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:  # pragma: no cover - safety net
            raise HTTPException(status_code=500, detail=str(error)) from error

        for frame in result["frames"]:
            image_path = Path(frame["path"])
            frame["image_base64"] = base64.b64encode(image_path.read_bytes()).decode("ascii")
            del frame["path"]

        return JSONResponse(result)


@app.get("/multiview/capabilities")
def multiview_caps() -> dict[str, object]:
    return multiview_capabilities()


@app.post("/multiview/register")
async def multiview_register(
    primary: UploadFile = File(...),
    secondary: UploadFile = File(...),
    method: str = Form(default="auto"),
) -> JSONResponse:
    if not is_image_upload(primary) or not is_image_upload(secondary):
        raise HTTPException(status_code=400, detail="Upload must be image files")

    with tempfile.TemporaryDirectory(prefix="geomora_multiview_") as temp_dir:
        primary_path = Path(temp_dir) / "primary.jpg"
        secondary_path = Path(temp_dir) / "secondary.jpg"
        primary_path.write_bytes(await primary.read())
        secondary_path.write_bytes(await secondary.read())

        try:
            result = register_views(str(primary_path), str(secondary_path), method=method)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:  # pragma: no cover - safety net
            raise HTTPException(status_code=500, detail=str(error)) from error

        return JSONResponse(result.to_dict())


@app.post("/multiview/fuse")
async def multiview_fuse(
    primary: UploadFile = File(...),
    secondary: UploadFile = File(...),
    homography: str | None = Form(default=None),
    method: str = Form(default="auto"),
    depth_method: str = Form(default="auto"),
    register_method: str = Form(default="auto"),
) -> JSONResponse:
    if not is_image_upload(primary) or not is_image_upload(secondary):
        raise HTTPException(status_code=400, detail="Upload must be image files")

    with tempfile.TemporaryDirectory(prefix="geomora_multiview_fuse_") as temp_dir:
        primary_path = Path(temp_dir) / "primary.jpg"
        secondary_path = Path(temp_dir) / "secondary.jpg"
        primary_path.write_bytes(await primary.read())
        secondary_path.write_bytes(await secondary.read())

        try:
            result = fuse_openings(
                str(primary_path),
                str(secondary_path),
                homography=homography,
                detect_method=method,
                depth_method=depth_method,
                register_method=register_method,
                return_overlay=True,
            )
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
