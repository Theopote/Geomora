"""Canonical facade scenes with pixel-space opening boxes for YOLO labels."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FixtureScene:
    name: str
    width: int
    height: int
    facade_rect: tuple[int, int, int, int]
    windows: tuple[tuple[int, int, int, int], ...]
    door: tuple[int, int, int, int] | None


RECTIFIED_CANONICAL = FixtureScene(
    name="rectified_canonical",
    width=800,
    height=600,
    facade_rect=(20, 40, 780, 560),
    windows=(
        (80, 140, 200, 320),
        (240, 140, 360, 320),
        (400, 140, 520, 320),
        (560, 140, 680, 320),
    ),
    door=(10, 330, 70, 560),
)


def scene_boxes(scene: FixtureScene) -> list[tuple[str, tuple[int, int, int, int]]]:
    boxes: list[tuple[str, tuple[int, int, int, int]]] = [
        ("window", box) for box in scene.windows
    ]
    if scene.door:
        boxes.append(("door", scene.door))
    return boxes
