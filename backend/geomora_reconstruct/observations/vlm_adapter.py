"""Convert VLM architectural evidence into Observation Graph evidence."""
from __future__ import annotations

from ..vlm_evidence import ArchitecturalEvidence
from .models import Observation, ObservationGraph, ObservationKind, ObservationSource


def vlm_evidence_to_observations(evidence: ArchitecturalEvidence, *, image_width: int = 0, image_height: int = 0) -> ObservationGraph:
    observations: list[Observation] = []
    source_meta = {"provider": evidence.provider, "model": evidence.model, "prompt_version": evidence.prompt_version}

    global_confidence = min(evidence.building_type.confidence, evidence.visible_storeys.confidence, evidence.bay_count.confidence)
    observations.append(Observation(id="vlm_architecture_001", kind=ObservationKind.ARCHITECTURAL_EVIDENCE, geometry={"visible_storeys": evidence.visible_storeys.value, "bay_count": evidence.bay_count.value}, semantic_candidates={str(evidence.building_type.value): evidence.building_type.confidence}, confidence=global_confidence, sources=[ObservationSource("vlm_architecture", global_confidence, source_meta)], uncertainties=list(evidence.uncertainties)))

    if evidence.facade_bbox:
        observations.append(Observation(id="vlm_facade_001", kind=ObservationKind.FACADE_CANDIDATE, geometry={"bbox": evidence.facade_bbox}, semantic_candidates={"facade": evidence.visible_storeys.confidence}, confidence=evidence.visible_storeys.confidence, sources=[ObservationSource("vlm_architecture", evidence.visible_storeys.confidence, source_meta)]))

    for index, group in enumerate(evidence.opening_groups, start=1):
        observations.append(Observation(id=f"vlm_repetition_{index:03d}", kind=ObservationKind.REPETITION_EVIDENCE, geometry={"bbox": group.region, "rows": group.rows, "columns": group.columns}, semantic_candidates={f"{group.type}_group": group.confidence}, confidence=group.confidence, sources=[ObservationSource("vlm_architecture", group.confidence, source_meta)]))

    for index, item in enumerate(evidence.occlusions, start=1):
        semantics = {"hidden_opening_possible": item.confidence} if item.likely_hidden_opening else {"occlusion": item.confidence}
        observations.append(Observation(id=f"vlm_occlusion_{index:03d}", kind=ObservationKind.OCCLUSION_REGION, geometry={"bbox": item.region}, semantic_candidates=semantics, confidence=item.confidence, sources=[ObservationSource("vlm_architecture", item.confidence, {**source_meta, "reason": item.reason})]))

    return ObservationGraph(photo_id=evidence.photo_id, image_width=image_width, image_height=image_height, observations=observations, debug={"adapter": "vlm_architecture", "prompt_version": evidence.prompt_version, "evidence_count": len(observations)})
