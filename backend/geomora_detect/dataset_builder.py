from __future__ import annotations

import random
import shutil
from pathlib import Path

import cv2
import numpy as np

from .fixture_scenes import RECTIFIED_CANONICAL, FixtureScene, scene_boxes

CLASS_IDS = {"window": 0, "door": 1}


def yolo_label_line(
    class_name: str,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    width: int,
    height: int,
) -> str:
    class_id = CLASS_IDS[class_name]
    cx = ((x1 + x2) / 2.0) / width
    cy = ((y1 + y2) / 2.0) / height
    box_w = (x2 - x1) / width
    box_h = (y2 - y1) / height
    return f"{class_id} {cx:.6f} {cy:.6f} {box_w:.6f} {box_h:.6f}"


def write_sample(
    images_dir: Path,
    labels_dir: Path,
    stem: str,
    image: np.ndarray,
    boxes: list[tuple[str, tuple[int, int, int, int]]],
) -> None:
    height, width = image.shape[:2]
    image_path = images_dir / f"{stem}.jpg"
    label_path = labels_dir / f"{stem}.txt"
    cv2.imwrite(str(image_path), image, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    lines = [
        yolo_label_line(class_name, x1, y1, x2, y2, width, height)
        for class_name, (x1, y1, x2, y2) in boxes
    ]
    label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def render_fixture_scene(scene: FixtureScene) -> np.ndarray:
    image = np.full((scene.height, scene.width, 3), (210, 210, 210), dtype=np.uint8)
    fx1, fy1, fx2, fy2 = scene.facade_rect
    cv2.rectangle(image, (fx1, fy1), (fx2, fy2), (175, 168, 158), -1)

    for class_name, (x1, y1, x2, y2) in scene_boxes(scene):
        color = (35, 35, 120) if class_name == "window" else (25, 25, 90)
        cv2.rectangle(image, (x1, y1), (x2, y2), color, -1)

    return image


def augment_fixture(image: np.ndarray, boxes: list[tuple[str, tuple[int, int, int, int]]]) -> tuple[np.ndarray, list]:
    height, width = image.shape[:2]
    out = image.copy()

    brightness = random.uniform(-25, 25)
    out = np.clip(out.astype(np.float32) + brightness, 0, 255).astype(np.uint8)

    if random.random() < 0.5:
        noise = np.random.normal(0, 6, out.shape).astype(np.float32)
        out = np.clip(out.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    if random.random() < 0.35:
        kernel = random.choice([3, 5])
        out = cv2.GaussianBlur(out, (kernel, kernel), 0)

    scale = random.uniform(0.85, 1.12)
    new_w = max(320, int(width * scale))
    new_h = max(240, int(height * scale))
    out = cv2.resize(out, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    scaled_boxes: list[tuple[str, tuple[int, int, int, int]]] = []
    for class_name, (x1, y1, x2, y2) in boxes:
        sx1 = int(x1 * scale)
        sy1 = int(y1 * scale)
        sx2 = int(x2 * scale)
        sy2 = int(y2 * scale)
        scaled_boxes.append((class_name, (sx1, sy1, sx2, sy2)))

    if random.random() < 0.25:
        out = cv2.flip(out, 1)
        scaled_boxes = [
            (
                class_name,
                (
                    new_w - x2,
                    y1,
                    new_w - x1,
                    y2,
                ),
            )
            for class_name, (x1, y1, x2, y2) in scaled_boxes
        ]

    return out, scaled_boxes


def random_facade(width: int = 800, height: int = 600) -> tuple[np.ndarray, list[tuple[str, tuple[int, int, int, int]]]]:
    image = np.full((height, width, 3), (210, 205, 198), dtype=np.uint8)
    boxes: list[tuple[str, tuple[int, int, int, int]]] = []

    margin = 40
    facade_x1 = random.randint(20, margin)
    facade_y1 = random.randint(20, margin)
    facade_x2 = width - random.randint(20, margin)
    facade_y2 = height - random.randint(20, margin)
    cv2.rectangle(image, (facade_x1, facade_y1), (facade_x2, facade_y2), (175, 168, 158), -1)

    window_count = random.randint(2, 6)
    facade_w = facade_x2 - facade_x1
    facade_h = facade_y2 - facade_y1
    slot_w = facade_w / window_count

    for index in range(window_count):
        win_w = int(slot_w * random.uniform(0.55, 0.85))
        win_h = int(facade_h * random.uniform(0.18, 0.32))
        cx_slot = facade_x1 + int(slot_w * (index + 0.5))
        x1 = max(facade_x1, cx_slot - win_w // 2)
        y1 = facade_y1 + int(facade_h * random.uniform(0.12, 0.22))
        x2 = min(facade_x2, x1 + win_w)
        y2 = min(facade_y2 - int(facade_h * 0.08), y1 + win_h)
        color = (
            random.randint(80, 140),
            random.randint(140, 200),
            random.randint(180, 240),
        )
        cv2.rectangle(image, (x1, y1), (x2, y2), color, -1)
        boxes.append(("window", (x1, y1, x2, y2)))

    if random.random() < 0.85:
        door_w = int(facade_w * random.uniform(0.08, 0.14))
        door_h = int(facade_h * random.uniform(0.42, 0.58))
        x1 = facade_x1 + random.randint(0, max(1, int(facade_w * 0.08)))
        y2 = facade_y2 - random.randint(5, 20)
        y1 = y2 - door_h
        x2 = min(facade_x2, x1 + door_w)
        cv2.rectangle(image, (x1, y1), (x2, y2), (70, 110, 80), -1)
        boxes.append(("door", (x1, y1, x2, y2)))

    return image, boxes


def import_custom_split(custom_root: Path, split: str, images_dir: Path, labels_dir: Path, prefix: str) -> int:
    src_images = custom_root / split / "images"
    src_labels = custom_root / split / "labels"
    if not src_images.exists():
        return 0

    count = 0
    for image_path in sorted(src_images.glob("*")):
        if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        stem = f"{prefix}_{image_path.stem}"
        shutil.copy2(image_path, images_dir / f"{stem}{image_path.suffix.lower()}")
        label_src = src_labels / f"{image_path.stem}.txt"
        if label_src.exists():
            shutil.copy2(label_src, labels_dir / f"{stem}.txt")
        count += 1
    return count


def build_dataset(
    output_root: Path,
    *,
    synthetic_train: int = 240,
    synthetic_val: int = 40,
    fixture_train: int = 80,
    fixture_val: int = 20,
    custom_root: Path | None = None,
    clean: bool = True,
) -> Path:
    if clean and output_root.exists():
        shutil.rmtree(output_root)

    canonical = render_fixture_scene(RECTIFIED_CANONICAL)
    canonical_boxes = scene_boxes(RECTIFIED_CANONICAL)

    for split, synthetic_count, fixture_count, prefix in (
        ("train", synthetic_train, fixture_train, "train"),
        ("val", synthetic_val, fixture_val, "val"),
    ):
        images_dir = output_root / split / "images"
        labels_dir = output_root / split / "labels"
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)

        for index in range(synthetic_count):
            image, boxes = random_facade()
            write_sample(images_dir, labels_dir, f"{prefix}_syn_{index:04d}", image, boxes)

        for index in range(fixture_count):
            image, boxes = augment_fixture(canonical, canonical_boxes)
            write_sample(images_dir, labels_dir, f"{prefix}_fix_{index:04d}", image, boxes)

        if custom_root:
            import_custom_split(custom_root, split, images_dir, labels_dir, f"{prefix}_custom")

    yaml_path = output_root / "facade.yaml"
    yaml_path.write_text(
        "\n".join(
            [
                f"path: {output_root.resolve().as_posix()}",
                "train: train/images",
                "val: val/images",
                "names:",
                "  0: window",
                "  1: door",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return yaml_path
