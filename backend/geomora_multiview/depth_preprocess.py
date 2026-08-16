from __future__ import annotations

import cv2
import numpy as np


def imagenet_square(image_bgr: np.ndarray, input_size: int, mean: list[float], std: list[float]) -> np.ndarray:
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    resized = cv2.resize(rgb, (input_size, input_size), interpolation=cv2.INTER_CUBIC)
    normalized = (resized - np.array(mean, dtype=np.float32)) / np.array(std, dtype=np.float32)
    return np.transpose(normalized, (2, 0, 1))[np.newaxis, ...]


def dpt_v2(
    image_bgr: np.ndarray,
    input_size: int,
    ensure_multiple_of: int,
    mean: list[float],
    std: list[float],
) -> tuple[np.ndarray, tuple[int, int]]:
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    height, width = rgb.shape[:2]
    scale = input_size / max(height, width)
    resized_height = int(np.ceil(height * scale / ensure_multiple_of) * ensure_multiple_of)
    resized_width = int(np.ceil(width * scale / ensure_multiple_of) * ensure_multiple_of)
    resized = cv2.resize(rgb, (resized_width, resized_height), interpolation=cv2.INTER_CUBIC)
    normalized = (resized - np.array(mean, dtype=np.float32)) / np.array(std, dtype=np.float32)
    tensor = np.transpose(normalized, (2, 0, 1))[np.newaxis, ...]
    return tensor, (resized_height, resized_width)


def normalize_depth_map(depth: np.ndarray) -> np.ndarray:
    depth = depth.astype(np.float32)
    depth = depth - depth.min()
    depth = depth / (depth.max() + 1e-6)
    return np.clip(depth, 0.0, 1.0)


def resize_depth_to_image(depth: np.ndarray, image_bgr: np.ndarray, model_size: tuple[int, int] | None) -> np.ndarray:
    height, width = image_bgr.shape[:2]
    if model_size is not None:
        depth = cv2.resize(depth, (model_size[1], model_size[0]), interpolation=cv2.INTER_CUBIC)
    if depth.shape[:2] != (height, width):
        depth = cv2.resize(depth, (width, height), interpolation=cv2.INTER_CUBIC)
    return normalize_depth_map(depth)
