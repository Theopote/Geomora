from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import cv2

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


def extract_frames(
    video_path: str,
    *,
    output_dir: str,
    max_frames: int = 12,
) -> dict[str, Any]:
    path = Path(video_path)
    if not path.exists():
        raise ValueError(f"Video not found: {video_path}")
    if path.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError(f"Unsupported video type: {path.suffix}")

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Unable to open video: {video_path}")

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    if frame_count <= 0:
        frame_count = 1

    max_frames = max(1, min(int(max_frames), 24))
    if frame_count <= max_frames:
        indices = list(range(frame_count))
    else:
        step = frame_count / max_frames
        indices = [min(frame_count - 1, int(round(step * index))) for index in range(max_frames)]

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    frames: list[dict[str, Any]] = []
    for order, frame_index in enumerate(indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue

        timestamp_sec = frame_index / fps if fps > 0 else 0.0
        stem = f"frame_{order + 1:03d}"
        image_path = out_dir / f"{stem}.jpg"
        thumb_path = out_dir / f"{stem}_thumb.jpg"

        cv2.imwrite(str(image_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        thumb = _resize_thumb(frame, 240)
        cv2.imwrite(str(thumb_path), thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

        frames.append(
            {
                "index": order,
                "frame_number": frame_index,
                "timestamp_sec": round(timestamp_sec, 3),
                "path": str(image_path),
                "thumb_base64": base64.b64encode(_encode_jpeg(thumb)).decode("ascii"),
            }
        )

    cap.release()
    if not frames:
        raise ValueError("No frames could be extracted from video")

    return {
        "video_path": str(path),
        "frame_count": frame_count,
        "fps": round(fps, 3),
        "duration_sec": round(frame_count / fps if fps > 0 else 0.0, 3),
        "frames": frames,
    }


def _resize_thumb(frame, max_width: int):
    height, width = frame.shape[:2]
    if width <= max_width:
        return frame
    scale = max_width / width
    return cv2.resize(frame, (max_width, int(height * scale)), interpolation=cv2.INTER_AREA)


def _encode_jpeg(image) -> bytes:
    ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        raise ValueError("Failed to encode thumbnail")
    return encoded.tobytes()
