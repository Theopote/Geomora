"""Ground-truth consistency checks for Reconstruction Metrics v1."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from math import hypot
from typing import Any


@dataclass(frozen=True)
class GTIssue:
    severity: str
    code: str
    path: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {"severity": self.severity, "code": self.code, "path": self.path, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


@dataclass
class GTValidationReport:
    photo_id: str
    issues: list[GTIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[GTIssue]: return [x for x in self.issues if x.severity == "error"]
    @property
    def warnings(self) -> list[GTIssue]: return [x for x in self.issues if x.severity == "warning"]
    @property
    def valid(self) -> bool: return not self.errors
    @property
    def gate_ready(self) -> bool: return not self.issues

    def add(self, severity: str, code: str, path: str, message: str, **details: Any) -> None:
        self.issues.append(GTIssue(severity, code, path, message, details))

    def to_dict(self) -> dict[str, Any]:
        return {"photo_id": self.photo_id, "valid": self.valid, "gate_ready": self.gate_ready, "error_count": len(self.errors), "warning_count": len(self.warnings), "issues": [x.to_dict() for x in self.issues]}


def _bbox(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 4: return None
    try: box = [float(x) for x in value]
    except (TypeError, ValueError): return None
    return box if all(0 <= x <= 1 for x in box) and box[2] > box[0] and box[3] > box[1] else None


def _median(values: list[float]) -> float:
    values = sorted(values); middle = len(values) // 2
    return values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2


def _iou(a: list[float], b: list[float]) -> float:
    w, h = max(0.0, min(a[2], b[2]) - max(a[0], b[0])), max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = w * h
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / union if union > 0 else 0.0


def validate_ground_truth(truth: dict[str, Any]) -> GTValidationReport:
    report = GTValidationReport(str(truth.get("photo_id") or "unknown"))
    topology = truth.get("topology") if isinstance(truth.get("topology"), dict) else {}
    storey_count, bay_count = topology.get("storey_count"), topology.get("bay_count")
    for name, value in (("storey", storey_count), ("bay", bay_count)):
        if not isinstance(value, int) or value < 1: report.add("error", f"invalid_{name}_count", f"topology.{name}_count", f"{name}_count must be a positive integer")
    openings = truth.get("openings") if isinstance(truth.get("openings"), list) else []
    ids: dict[str, int] = {}; valid: list[tuple[int, dict[str, Any], list[float]]] = []
    for index, opening in enumerate(openings):
        path = f"openings[{index}]"
        if not isinstance(opening, dict): report.add("error", "invalid_opening", path, "opening must be an object"); continue
        oid = str(opening.get("id") or "")
        if not oid: report.add("error", "missing_element_id", f"{path}.id", "opening id is required")
        elif oid in ids: report.add("error", "duplicate_element_id", f"{path}.id", f"duplicate opening id {oid}", first_index=ids[oid])
        else: ids[oid] = index
        box = _bbox(opening.get("bbox"))
        if box is None: report.add("error", "invalid_bbox", f"{path}.bbox", "bbox must be normalized [x1,y1,x2,y2]"); continue
        valid.append((index, opening, box))
        for key, maximum in (("storey", storey_count), ("bay", bay_count)):
            value = opening.get(key)
            if not isinstance(value, int) or value < 1 or not isinstance(maximum, int) or value > maximum:
                report.add("error", f"invalid_{key}_id", f"{path}.{key}", f"{key} must be within declared topology", value=value, maximum=maximum)
    for pos, (li, left, lb) in enumerate(valid):
        for ri, right, rb in valid[pos+1:]:
            overlap = _iou(lb, rb)
            if overlap >= .98: report.add("error", "duplicate_bbox", f"openings[{ri}].bbox", f"bbox duplicates {left.get('id')}", iou=round(overlap, 4))
            elif overlap >= .65 and left.get("type") == right.get("type"): report.add("warning", "high_annotation_overlap", f"openings[{ri}].bbox", f"substantial overlap with {left.get('id')}", iou=round(overlap, 4))
    _validate_spatial_storeys(valid, report); _validate_patterns(truth.get("pattern_groups"), valid, ids, report)
    _validate_annotation_claims(str(truth.get("annotation_notes") or ""), valid, report); _validate_metric(truth, report)
    return report


def _validate_spatial_storeys(valid, report):
    centers: dict[int, list[float]] = {}
    for _, item, box in valid:
        if isinstance(item.get("storey"), int): centers.setdefault(item["storey"], []).append((box[1]+box[3])/2)
    medians = {key: _median(values) for key, values in centers.items() if len(values) >= 2}
    if len(medians) < 2: return
    for index, item, box in valid:
        assigned = item.get("storey")
        if assigned not in medians: continue
        center = (box[1]+box[3])/2; nearest = min(medians, key=lambda key: abs(center-medians[key]))
        current, proposed = abs(center-medians[assigned]), abs(center-medians[nearest])
        if nearest != assigned and proposed <= .06 and current-proposed >= .10:
            report.add("warning", "spatial_storey_mismatch", f"openings[{index}].storey", f"{item.get('id')} is assigned to storey {assigned} but spatially matches storey {nearest}", assigned_storey=assigned, suggested_storey=nearest, center_y=round(center,4), assigned_distance=round(current,4), suggested_distance=round(proposed,4))


def _validate_patterns(groups, valid, ids, report):
    if not isinstance(groups, list): return
    boxes = {str(item.get("id")): box for _, item, box in valid}; items = {str(item.get("id")): item for _, item, _ in valid}
    for index, group in enumerate(groups):
        members = group.get("members") if isinstance(group, dict) else None
        if not isinstance(members, list): report.add("error", "invalid_pattern_members", f"pattern_groups[{index}].members", "pattern members must be an array"); continue
        if len(members) != len(set(members)): report.add("error", "duplicate_pattern_member", f"pattern_groups[{index}].members", "pattern group contains duplicate member ids")
        missing = [x for x in members if x not in ids]
        if missing: report.add("error", "unknown_pattern_member", f"pattern_groups[{index}].members", "pattern group references unknown openings", missing=missing)
        known = [x for x in members if x in boxes]
        if len(known) < 2: continue
        yc = _median([(boxes[x][1]+boxes[x][3])/2 for x in known]); widths=[boxes[x][2]-boxes[x][0] for x in known]; heights=[boxes[x][3]-boxes[x][1] for x in known]; kind=items[known[0]].get("type")
        omitted=[]
        for _, item, box in valid:
            oid=str(item.get("id")); center=(box[1]+box[3])/2; width=box[2]-box[0]; height=box[3]-box[1]
            if oid not in members and item.get("type")==kind and abs(center-yc)<=.04 and abs(width-_median(widths))<=.025 and abs(height-_median(heights))<=.04: omitted.append(oid)
        if omitted: report.add("warning", "probable_pattern_omission", f"pattern_groups[{index}].members", "spatially similar openings are omitted from the pattern group", omitted=omitted)


def _validate_annotation_claims(notes, valid, report):
    match=re.search(r"second floor has\s+(\w+)\s+(?:small\s+)?windows?", notes, re.I); words={"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10}
    if not match: return
    claimed=int(match.group(1)) if match.group(1).isdigit() else words.get(match.group(1).lower())
    annotated=sum(1 for _,item,_ in valid if item.get("type")=="window" and item.get("storey")==2)
    if claimed is not None and claimed != annotated: report.add("warning", "annotation_count_mismatch", "annotation_notes", f"note claims {claimed} second-floor windows but topology assigns {annotated}", claimed=claimed, annotated=annotated)


def _validate_metric(truth, report):
    metric=truth.get("metric") if isinstance(truth.get("metric"),dict) else {}; topology=truth.get("topology") or {}
    for key,value in metric.items():
        if key.endswith("_mm") and (not isinstance(value,(int,float)) or value<=0): report.add("error","invalid_metric",f"metric.{key}","metric dimensions must be positive",value=value)
    if metric.get("facade_height_mm") and metric.get("storey_height_mm") and topology.get("storey_count"):
        expected=metric["storey_height_mm"]*topology["storey_count"]
        if abs(expected-metric["facade_height_mm"])/metric["facade_height_mm"]>.1: report.add("warning","storey_metric_mismatch","metric.storey_height_mm","storey height × count disagrees with facade height",expected_height_mm=expected)
    seen=set()
    for index,anchor in enumerate(truth.get("metric_anchors") or []):
        path=f"metric_anchors[{index}]"; aid=str(anchor.get("id") or "")
        if not aid or aid in seen: report.add("error","duplicate_or_missing_anchor_id",f"{path}.id","metric anchor id must be present and unique")
        seen.add(aid); start,end=anchor.get("start"),anchor.get("end")
        if not (isinstance(start,list) and isinstance(end,list) and len(start)==2 and len(end)==2 and all(isinstance(v,(int,float)) and 0<=v<=1 for v in start+end)): report.add("error","invalid_anchor_coordinates",path,"anchor endpoints must be normalized 2D coordinates"); continue
        if hypot(end[0]-start[0],end[1]-start[1])<1e-6: report.add("error","zero_length_anchor",path,"anchor endpoints must differ")
        distance=anchor.get("distance_mm")
        if anchor.get("status")=="surveyed" and (not isinstance(distance,(int,float)) or distance<=0): report.add("error","surveyed_anchor_missing_distance",f"{path}.distance_mm","surveyed anchor requires a positive distance")
        if "width" in aid and abs(end[0]-start[0])<abs(end[1]-start[1]): report.add("warning","anchor_axis_mismatch",path,"width anchor is predominantly vertical")
        if "height" in aid and abs(end[1]-start[1])<abs(end[0]-start[0]): report.add("warning","anchor_axis_mismatch",path,"height anchor is predominantly horizontal")
