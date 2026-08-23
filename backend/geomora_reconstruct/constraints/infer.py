"""Infer IR-compatible soft constraints from architectural pattern evidence."""
from __future__ import annotations

from typing import Any

from ..vlm_evidence import ArchitecturalEvidence
from .models import ConstraintPriority, ConstraintSuggestion

TYPE_MAP = {
    "equal_width": "equal_width",
    "equal_height": "equal_height",
    "equal_spacing": "equal_spacing",
    "equal_sill": "align",
    "horizontal_alignment": "align",
    "vertical_alignment": "vertical",
    "symmetry": "symmetry",
}


def _vlm_support(
    members: list[str],
    evidence: ArchitecturalEvidence | None,
) -> tuple[float | None, dict[str, Any] | None]:
    if evidence is None:
        return None, None
    expected = len(members)
    candidates = [
        group
        for group in evidence.opening_groups
        if group.type in ("window", "mixed") and group.rows * group.columns >= expected
    ]
    if not candidates or evidence.repetition.value not in ("moderate", "strong"):
        return None, None
    best = max(candidates, key=lambda group: group.confidence)
    confidence = min(best.confidence, evidence.repetition.confidence)
    return confidence, {
        "opening_group": best.to_dict(),
        "repetition": evidence.repetition.to_dict(),
        "model": evidence.model,
        "prompt_version": evidence.prompt_version,
    }


def _combined_confidence(cv: float, vlm: float | None) -> float:
    if vlm is None:
        return cv
    return 1.0 - (1.0 - cv) * (1.0 - vlm)


def infer_constraint_suggestions(
    openings: list[dict[str, Any]],
    topology: dict[str, Any],
    *,
    architectural_evidence: ArchitecturalEvidence | None = None,
) -> list[ConstraintSuggestion]:
    valid_ids = {str(item["id"]) for item in openings if item.get("id")}
    suggestions: list[ConstraintSuggestion] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()

    for group in topology.get("pattern_groups") or []:
        members = [str(item) for item in group.get("members") or [] if str(item) in valid_ids]
        if len(members) < 2:
            continue
        cv_confidence = max(0.0, min(1.0, float(group.get("confidence", 0.5))))
        vlm_confidence, vlm_detail = _vlm_support(members, architectural_evidence)
        combined = _combined_confidence(cv_confidence, vlm_confidence)
        source = "cv_pattern+vlm" if vlm_confidence is not None else "cv_pattern"

        for raw_type in group.get("constraints") or []:
            constraint_type = TYPE_MAP.get(str(raw_type))
            if constraint_type is None:
                continue
            key = (constraint_type, tuple(sorted(members)))
            if key in seen:
                continue
            seen.add(key)
            evidence_payload: dict[str, Any] = {
                "pattern_group_id": group.get("id"),
                "cv_confidence": round(cv_confidence, 4),
            }
            if vlm_detail is not None:
                evidence_payload["vlm"] = vlm_detail
            suggestions.append(
                ConstraintSuggestion(
                    id=f"constraint_{len(suggestions) + 1:03d}",
                    type=constraint_type,
                    targets=members,
                    priority=ConstraintPriority.SOFT,
                    confidence=combined,
                    weight=max(0.1, combined),
                    source=source,
                    evidence=evidence_payload,
                )
            )
    return suggestions
