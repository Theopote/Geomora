from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from .depth_preprocess import resize_depth_to_image

MARIGOLD_MODEL_ID = "prs-eth/marigold-depth-v1-1"


def marigold_available() -> bool:
    try:
        import diffusers  # noqa: F401
        import torch  # noqa: F401

        return True
    except ImportError:
        return False


@lru_cache(maxsize=1)
def _load_pipeline():
    import torch
    from diffusers import MarigoldDepthPipeline

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    device = "cuda" if torch.cuda.is_available() else "cpu"
    pipeline = MarigoldDepthPipeline.from_pretrained(
        MARIGOLD_MODEL_ID,
        variant="fp16" if dtype == torch.float16 else None,
        torch_dtype=dtype,
    )
    pipeline = pipeline.to(device)
    pipeline.set_progress_bar_config(disable=True)
    return pipeline


def relative_depth_map_marigold(image_bgr: np.ndarray, *, num_inference_steps: int = 1) -> np.ndarray:
    if not marigold_available():
        raise RuntimeError(
            "Marigold requires optional deps. Install: pip install -r requirements-depth.txt"
        )

    from PIL import Image

    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb)
    pipeline = _load_pipeline()
    result = pipeline(pil_image, num_inference_steps=num_inference_steps)
    depth = np.asarray(result.prediction, dtype=np.float32).squeeze()
    return resize_depth_to_image(depth, image_bgr, None)
