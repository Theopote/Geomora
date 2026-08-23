from __future__ import annotations

from geomora_detect.models import DetectionResult

from .graph import ObservationGraphBuilder
from .models import ObservationGraph, ObservationKind, ObservationSource


def yolo_to_observations(
    result: DetectionResult,
    *,
    photo_id: str,
) -> ObservationGraph:
    builder = ObservationGraphBuilder(photo_id, result.image_width, result.image_height)
    for element in result.elements:
        obs_id = builder.next_id("obs")
        builder.add(
            ObservationGraphBuilder.make_opening_observation(
                obs_id,
                element.bbox_norm,
                element.type,
                element.confidence,
                "yolo",
                metadata={"method": result.method},
            )
        )
    return builder.build(
        debug={
            "adapter": "yolo",
            "source_method": result.method,
            "element_count": len(result.elements),
        }
    )


def facade_row_to_observations(
    result: DetectionResult,
    *,
    photo_id: str,
) -> ObservationGraph:
    builder = ObservationGraphBuilder(photo_id, result.image_width, result.image_height)
    bounds = result.debug.get("facade_bounds")
    if bounds and len(bounds) >= 4:
        x1, y1, x2, y2 = bounds
        width = max(result.image_width, 1)
        height = max(result.image_height, 1)
        builder.add(
            ObservationGraphBuilder.make_facade_observation(
                builder.next_id("facade"),
                [x1 / width, y1 / height, x2 / width, y2 / height],
                0.6,
                "facade_row",
                metadata={"role": "facade_bounds"},
            )
        )

    for element in result.elements:
        obs_id = builder.next_id("obs")
        builder.add(
            ObservationGraphBuilder.make_opening_observation(
                obs_id,
                element.bbox_norm,
                element.type,
                element.confidence,
                "facade_row",
                metadata={"method": result.method},
            )
        )
    return builder.build(
        debug={
            "adapter": "facade_row",
            "source_method": result.method,
            "element_count": len(result.elements),
            "facade_bounds": bounds,
        }
    )


def detection_result_to_observations(
    result: DetectionResult,
    *,
    photo_id: str,
) -> ObservationGraph:
    source_type = result.method
    if source_type.startswith("yolo"):
        return yolo_to_observations(result, photo_id=photo_id)
    if source_type.startswith("facade_row"):
        return facade_row_to_observations(result, photo_id=photo_id)
    builder = ObservationGraphBuilder(photo_id, result.image_width, result.image_height)
    for element in result.elements:
        obs_id = builder.next_id("obs")
        builder.add(
            ObservationGraphBuilder.make_opening_observation(
                obs_id,
                element.bbox_norm,
                element.type,
                element.confidence,
                source_type,
            )
        )
    return builder.build(debug={"adapter": "generic", "source_method": result.method})
