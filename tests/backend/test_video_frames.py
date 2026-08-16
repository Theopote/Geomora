from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from geomora_capture.video_frames import extract_frames


def test_extract_frames_from_synthetic_video(tmp_path):
    width, height = 320, 240
    fps = 10
    frame_count = 20
    video_path = tmp_path / "sample.mp4"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    for index in range(frame_count):
        frame = np.full((height, width, 3), (index * 10, 80, 120), dtype=np.uint8)
        writer.write(frame)
    writer.release()

    output_dir = tmp_path / "frames"
    result = extract_frames(str(video_path), output_dir=str(output_dir), max_frames=6)

    assert result["frame_count"] == frame_count
    assert len(result["frames"]) == 6
    assert all(Path(frame["path"]).exists() for frame in result["frames"])

