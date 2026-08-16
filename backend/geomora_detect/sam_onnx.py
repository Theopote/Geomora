from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = BACKEND_ROOT / "models" / "sam_config.json"

PIXEL_MEAN = np.array([123.675, 116.28, 103.53], dtype=np.float32)
PIXEL_STD = np.array([58.395, 57.12, 57.375], dtype=np.float32)

BOX_POINT_LABELS = np.array([[2, 3]], dtype=np.float32)


@lru_cache(maxsize=1)
def _load_config(config_path: str) -> dict:
    with Path(config_path).open(encoding="utf-8") as handle:
        return json.load(handle)


def load_sam_config(config_path: str | None = None) -> dict:
    path = Path(config_path or os.environ.get("GEOMORA_SAM_CONFIG", DEFAULT_CONFIG_PATH))
    if not path.exists():
        return {
            "encoder_file": "mobile_sam_image_encoder.onnx",
            "decoder_file": "sam_mask_decoder_single.onnx",
            "input_size": 1024,
        }
    return _load_config(str(path))


def resolve_encoder_path(config: dict) -> Path:
    env_path = os.environ.get("GEOMORA_SAM_ENCODER")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    encoder_file = config.get("encoder_file", "mobile_sam_image_encoder.onnx")
    path = BACKEND_ROOT / "models" / encoder_file
    if path.exists():
        return path

    legacy = config.get("model_file")
    if legacy:
        legacy_path = BACKEND_ROOT / "models" / legacy
        if legacy_path.exists():
            return legacy_path

    raise FileNotFoundError(f"SAM encoder ONNX not found: {path}")


def resolve_decoder_path(config: dict) -> Path:
    env_path = os.environ.get("GEOMORA_SAM_DECODER")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    decoder_file = config.get("decoder_file", "sam_mask_decoder_single.onnx")
    path = BACKEND_ROOT / "models" / decoder_file
    if path.exists():
        return path

    raise FileNotFoundError(f"SAM decoder ONNX not found: {path}")


def mobile_sam_available(config_path: str | None = None) -> bool:
    try:
        config = load_sam_config(config_path)
        return resolve_encoder_path(config).exists() and resolve_decoder_path(config).exists()
    except FileNotFoundError:
        return False


def preprocess_shape(height: int, width: int, target_length: int) -> tuple[int, int]:
    scale = target_length / max(height, width)
    new_height = int(round(height * scale))
    new_width = int(round(width * scale))
    return new_height, new_width


def preprocess_image(bgr: np.ndarray, input_size: int = 1024) -> tuple[np.ndarray, tuple[int, int], tuple[int, int]]:
    height, width = bgr.shape[:2]
    new_height, new_width = preprocess_shape(height, width, input_size)
    resized = cv2.resize(bgr, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32)
    padded = np.zeros((input_size, input_size, 3), dtype=np.float32)
    padded[:new_height, :new_width] = rgb
    normalized = (padded - PIXEL_MEAN) / PIXEL_STD
    return normalized.astype(np.float32), (new_height, new_width), (height, width)


def bbox_norm_to_sam_box(
    bbox_norm: list[float],
    original_size: tuple[int, int],
    resized_size: tuple[int, int],
) -> np.ndarray:
    orig_height, orig_width = original_size
    new_height, new_width = resized_size
    x1 = bbox_norm[0] * orig_width
    y1 = bbox_norm[1] * orig_height
    x2 = bbox_norm[2] * orig_width
    y2 = bbox_norm[3] * orig_height
    scale_x = new_width / orig_width
    scale_y = new_height / orig_height
    coords = np.array(
        [[x1 * scale_x, y1 * scale_y, x2 * scale_x, y2 * scale_y]],
        dtype=np.float32,
    )
    return coords.reshape(1, 2, 2)


def mask_to_bbox_norm(mask: np.ndarray, resized_size: tuple[int, int]) -> list[float] | None:
    if mask.ndim == 4:
        mask = mask[0, 0]
    elif mask.ndim == 3:
        mask = mask[0]

    binary = (mask > 0.0).astype(np.uint8)
    if not np.any(binary):
        return None

    new_height, new_width = resized_size
    ys, xs = np.where(binary > 0)
    if xs.size == 0:
        return None

    x_norm_min = float(xs.min()) / new_width
    y_norm_min = float(ys.min()) / new_height
    x_norm_max = float(xs.max() + 1) / new_width
    y_norm_max = float(ys.max() + 1) / new_height
    return [
        max(0.0, min(1.0, x_norm_min)),
        max(0.0, min(1.0, y_norm_min)),
        max(0.0, min(1.0, x_norm_max)),
        max(0.0, min(1.0, y_norm_max)),
    ]


def mask_to_full_image(
    mask: np.ndarray,
    resized_size: tuple[int, int],
    original_size: tuple[int, int],
) -> np.ndarray:
    if mask.ndim == 4:
        mask = mask[0, 0]
    elif mask.ndim == 3:
        mask = mask[0]

    new_height, new_width = resized_size
    orig_height, orig_width = original_size
    cropped = (mask[:new_height, :new_width] > 0.0).astype(np.uint8) * 255
    if cropped.shape != (orig_height, orig_width):
        cropped = cv2.resize(cropped, (orig_width, orig_height), interpolation=cv2.INTER_NEAREST)
    return cropped


@lru_cache(maxsize=2)
def _load_encoder_session(encoder_path: str):
    import onnxruntime as ort

    return ort.InferenceSession(encoder_path, providers=["CPUExecutionProvider"])


@lru_cache(maxsize=2)
def _load_decoder_session(decoder_path: str):
    import onnxruntime as ort

    return ort.InferenceSession(decoder_path, providers=["CPUExecutionProvider"])


class MobileSamOnnxRunner:
    def __init__(
        self,
        encoder_path: Path,
        decoder_path: Path,
        *,
        input_size: int = 1024,
    ) -> None:
        self.encoder_path = encoder_path
        self.decoder_path = decoder_path
        self.input_size = input_size
        self.encoder = _load_encoder_session(str(encoder_path))
        self.decoder = _load_decoder_session(str(decoder_path))
        self._embedding: np.ndarray | None = None
        self._resized_size: tuple[int, int] | None = None
        self._original_size: tuple[int, int] | None = None

    @classmethod
    def from_config(cls, config: dict | None = None) -> MobileSamOnnxRunner:
        config = config or load_sam_config()
        return cls(
            resolve_encoder_path(config),
            resolve_decoder_path(config),
            input_size=int(config.get("input_size", 1024)),
        )

    def reset(self) -> None:
        self._embedding = None
        self._resized_size = None
        self._original_size = None

    def encode(self, bgr: np.ndarray) -> np.ndarray:
        tensor, resized_size, original_size = preprocess_image(bgr, self.input_size)
        input_meta = self.encoder.get_inputs()[0]
        if len(input_meta.shape) == 4:
            tensor = np.transpose(tensor, (2, 0, 1))[np.newaxis, ...]
        input_name = input_meta.name
        embedding = self.encoder.run(None, {input_name: tensor})[0]
        self._embedding = embedding
        self._resized_size = resized_size
        self._original_size = original_size
        return embedding

    def predict_mask_from_box(self, bbox_norm: list[float]) -> tuple[np.ndarray | None, list[float] | None]:
        if self._embedding is None or self._resized_size is None or self._original_size is None:
            raise RuntimeError("Call encode() before predict_mask_from_box()")

        point_coords = bbox_norm_to_sam_box(bbox_norm, self._original_size, self._resized_size)
        decoder_values = {
            "image_embeddings": self._embedding,
            "point_coords": point_coords,
            "point_labels": BOX_POINT_LABELS,
            "mask_input": np.zeros((1, 1, 256, 256), dtype=np.float32),
            "has_mask_input": np.array([0.0], dtype=np.float32),
            "orig_im_size": np.array(
                [self._resized_size[0], self._resized_size[1]],
                dtype=np.float32,
            ),
        }
        feed = {
            inp.name: decoder_values[inp.name]
            for inp in self.decoder.get_inputs()
            if inp.name in decoder_values
        }
        outputs = self.decoder.run(None, feed)
        masks = outputs[0]
        bbox = mask_to_bbox_norm(masks, self._resized_size)
        full_mask = mask_to_full_image(masks, self._resized_size, self._original_size)
        return full_mask, bbox

    def refine_bbox(
        self,
        bgr: np.ndarray,
        bbox_norm: list[float],
    ) -> tuple[list[float] | None, np.ndarray | None]:
        if self._original_size != (bgr.shape[0], bgr.shape[1]):
            self.encode(bgr)
        elif self._embedding is None:
            self.encode(bgr)

        full_mask, refined_bbox = self.predict_mask_from_box(bbox_norm)
        if refined_bbox is None:
            return None, None
        return refined_bbox, full_mask


def refine_bbox_mobile_sam(
    bgr: np.ndarray,
    bbox_norm: list[float],
    *,
    runner: MobileSamOnnxRunner | None = None,
    config: dict | None = None,
) -> tuple[list[float] | None, np.ndarray | None]:
    if not mobile_sam_available():
        return None, None

    active_runner = runner or MobileSamOnnxRunner.from_config(config)
    return active_runner.refine_bbox(bgr, bbox_norm)
