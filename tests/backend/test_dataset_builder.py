from __future__ import annotations

from pathlib import Path

from geomora_detect.dataset_builder import build_dataset, random_facade


def test_random_facade_has_labels():
    image, boxes = random_facade()
    assert image.shape[0] == 600
    assert len(boxes) >= 2


def test_build_dataset_writes_yaml(tmp_path: Path):
    root = tmp_path / "facade_yolo"
    yaml_path = build_dataset(
        root,
        synthetic_train=4,
        synthetic_val=2,
        fixture_train=3,
        fixture_val=1,
        clean=True,
    )
    assert yaml_path.exists()
    train_images = list((root / "train" / "images").glob("*.jpg"))
    train_labels = list((root / "train" / "labels").glob("*.txt"))
    assert len(train_images) == 7
    assert len(train_labels) == 7
