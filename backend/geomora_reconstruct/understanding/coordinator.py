"""Reconcile geometric understanding with uncertain VLM evidence."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..vlm_evidence import ArchitecturalEvidence
from .result import UnderstandingResult

VLM_OVERRIDE_MIN = 0.85
CV_WEAK_MAX = 0.55


@dataclass(frozen=True)
class CountDecision:
    field: str
    value: int
    source: str
    confidence: float
    cv_value: int
    cv_confidence: float
    vlm_value: int
    vlm_confidence: float
    conflict: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "source": self.source,
            "confidence": round(self.confidence, 4),
            "cv": {"value": self.cv_value, "confidence": round(self.cv_confidence, 4)},
            "vlm": {"value": self.vlm_value, "confidence": round(self.vlm_confidence, 4)},
            "conflict": self.conflict,
        }


def _mean_confidence(items: list[Any], *, empty: float = 0.25) -> float:
    if not items:
        return empty
    return sum(float(item.confidence) for item in items) / len(items)


def reconcile_count(
    field: str,
    *,
    cv_value: int,
    cv_confidence: float,
    vlm_value: int,
    vlm_confidence: float,
) -> CountDecision:
    if cv_value == vlm_value:
        combined = 1.0 - (1.0 - cv_confidence) * (1.0 - vlm_confidence)
        return CountDecision(field, cv_value, "cv+vlm_agreement", combined, cv_value, cv_confidence, vlm_value, vlm_confidence, False)
    if vlm_confidence >= VLM_OVERRIDE_MIN and cv_confidence <= CV_WEAK_MAX:
        return CountDecision(field, vlm_value, "vlm_high_confidence", vlm_confidence, cv_value, cv_confidence, vlm_value, vlm_confidence, True)
    return CountDecision(field, cv_value, "cv_geometry", cv_confidence, cv_value, cv_confidence, vlm_value, vlm_confidence, True)


def coordinate_architectural_evidence(
    result: UnderstandingResult,
    evidence: ArchitecturalEvidence,
) -> UnderstandingResult:
    cv_storeys = int(result.debug.get("storey_count", len(result.storeys) or 1))
    cv_bays = int(result.debug.get("bay_count", len(result.bays) or 1))
    storey_cv_confidence = _mean_confidence(result.storeys)
    bay_cv_confidence = _mean_confidence(result.bays)
    opening_support = int(result.debug.get("core_window_count", 0))
    if opening_support < 2:
        storey_cv_confidence = min(storey_cv_confidence, 0.45)
        bay_cv_confidence = min(bay_cv_confidence, 0.45)
    elif opening_support < 4:
        storey_cv_confidence = min(storey_cv_confidence, 0.6)
        bay_cv_confidence = min(bay_cv_confidence, 0.6)

    storey_decision = reconcile_count(
        "storey_count",
        cv_value=cv_storeys,
        cv_confidence=storey_cv_confidence,
        vlm_value=int(evidence.visible_storeys.value),
        vlm_confidence=evidence.visible_storeys.confidence,
    )
    bay_decision = reconcile_count(
        "bay_count",
        cv_value=cv_bays,
        cv_confidence=bay_cv_confidence,
        vlm_value=int(evidence.bay_count.value),
        vlm_confidence=evidence.bay_count.confidence,
    )

    result.method = "understanding_v0.2_evidence"
    result.debug["storey_count"] = storey_decision.value
    result.debug["bay_count"] = bay_decision.value
    result.debug["evidence_coordination"] = {
        "storey_count": storey_decision.to_dict(),
        "bay_count": bay_decision.to_dict(),
        "building_type": evidence.building_type.to_dict(),
        "repetition": evidence.repetition.to_dict(),
        "opening_groups": [item.to_dict() for item in evidence.opening_groups],
        "provider": evidence.provider,
        "model": evidence.model,
        "prompt_version": evidence.prompt_version,
    }
    if result.facade_bbox is None and evidence.facade_bbox:
        result.facade_bbox = evidence.facade_bbox
    for decision in (storey_decision, bay_decision):
        if decision.conflict:
            result.uncertainties.append(
                f"{decision.field}_conflict:cv={decision.cv_value},vlm={decision.vlm_value},selected={decision.source}"
            )
        if decision.source == "vlm_high_confidence" and decision.value > decision.cv_value:
            result.uncertainties.append(f"{decision.field}_contains_unobserved_structure")
    result.uncertainties.extend(
        item for item in evidence.uncertainties if item not in result.uncertainties
    )
    return result
