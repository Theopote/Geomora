from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from geomora_detect.pipeline import SUPPORTED_METHODS, detect_facade
from geomora_capture.video_frames import extract_frames
from geomora_multiview.pipeline import fuse_openings, multiview_capabilities, register_views
from geomora_reconstruct.service import reconstruct_facade

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
        "reconstruct": "POST /reconstruct",
        "detect_capabilities": "GET /detect/capabilities",
        "settings_capabilities": "GET /settings/capabilities",
        "video_extract_frames": "POST /video/extract_frames",
        "multiview_register": "POST /multiview/register",
        "multiview_fuse": "POST /multiview/fuse",
        "multiview_capabilities": "GET /multiview/capabilities",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "geomora-perception"}


@app.get("/settings/capabilities")
def settings_capabilities() -> dict[str, object]:
    detection = detect_capabilities()
    multiview = multiview_capabilities()
    return {
        "service_available": True,
        "service_version": app.version,
        "cloud_providers": {
            "openai": {
                "configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
                "credential_source": "OPENAI_API_KEY",
            },
            "gemini": {
                "configured": bool(
                    os.getenv("GEMINI_API_KEY", "").strip()
                    or os.getenv("GOOGLE_API_KEY", "").strip()
                ),
                "credential_source": "GEMINI_API_KEY or GOOGLE_API_KEY",
            },
        },
        "local_inference": {
            "detection_methods": detection["methods"],
            "yolo_available": detection["yolo_available"],
            "sam_onnx_available": detection["sam_onnx_available"],
            "multiview": multiview,
        },
        "security": {
            "api_keys_returned": False,
            "settings_store_contains_secrets": False,
        },
    }


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


@app.post("/reconstruct")
async def reconstruct(
    image: UploadFile = File(...),
    method: str = Form(default="auto"),
    photo_id: str = Form(default="workspace_photo"),
    wall_length_mm: float | None = Form(default=None),
    wall_height_mm: float | None = Form(default=None),
    routing_mode: str = Form(default="local_only"),
    vlm_provider: str = Form(default="openai"),
    vlm_model: str = Form(default="auto"),
    cloud_upload_authorized: bool = Form(default=False),
    depth_method: str = Form(default="off"),
) -> JSONResponse:
    if not is_image_upload(image):
        raise HTTPException(status_code=400, detail="Upload must be an image file")

    suffix = Path(image.filename or "upload.jpg").suffix or ".jpg"
    with tempfile.TemporaryDirectory(prefix="geomora_reconstruct_") as temp_dir:
        input_path = Path(temp_dir) / f"input{suffix}"
        input_path.write_bytes(await image.read())
        metric = None
        if wall_length_mm and wall_length_mm > 0 and wall_height_mm and wall_height_mm > 0:
            metric = {
                "facade_width_mm": wall_length_mm,
                "facade_height_mm": wall_height_mm,
            }
        try:
            result = reconstruct_facade(
                input_path,
                photo_id=photo_id.strip() or "workspace_photo",
                method=method,
                metric=metric,
                return_overlay=True,
                routing_mode=routing_mode,
                vlm_provider=vlm_provider,
                vlm_model=vlm_model,
                cloud_upload_authorized=cloud_upload_authorized,
                depth_method=depth_method,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:  # pragma: no cover - safety net
            raise HTTPException(status_code=500, detail=str(error)) from error

        return JSONResponse(result)


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
    from geomora_detect.mask_refiner import sam_model_available
    from geomora_detect.sam_onnx import mobile_sam_available
    from geomora_detect.yolo_detector import model_available

    return {
        "methods": list(SUPPORTED_METHODS),
        "yolo_available": model_available(),
        "sam_available": True,
        "sam_onnx_available": mobile_sam_available(),
        "sam_refine": "sam_v1 (auto detect + mask refine)",
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
