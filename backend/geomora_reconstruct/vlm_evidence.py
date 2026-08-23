"""Strict VLM architectural evidence contract.

VLM output is evidence only. It never contains final dimensions or IR geometry.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from geomora_detect.vlm_prelabel import extract_json_payload
from geomora_detect.vlm_prelabel import (
    encode_image_base64,
    gemini_generate_url,
    gemini_headers,
    post_json_with_retries,
)


PROMPT_VERSION = "architecture-evidence-v0.1"
ALLOWED_REPETITION = {"none", "weak", "moderate", "strong"}

SYSTEM_PROMPT = """You analyze visible architectural facade structure.
Return one JSON object only. Treat every conclusion as uncertain evidence.
Do not invent metric dimensions, hidden elevations, construction details, or a
final building model. Count visible storeys and facade bays; describe repeated
opening groups and occlusions. All confidence values must be between 0 and 1.

Schema:
{
  "building_type": {"value": "string", "confidence": 0.0},
  "facade": {
    "bbox": [x1,y1,x2,y2] | null,
    "visible_storeys": {"value": integer, "confidence": 0.0},
    "bay_count": {"value": integer, "confidence": 0.0},
    "repetition": {"value": "none|weak|moderate|strong", "confidence": 0.0}
  },
  "opening_groups": [
    {"type":"window|door|mixed|unknown", "rows":integer,
     "columns":integer, "region":[x1,y1,x2,y2], "confidence":0.0}
  ],
  "occlusions": [
    {"region":[x1,y1,x2,y2], "likely_hidden_opening":boolean,
     "confidence":0.0, "reason":"string"}
  ],
  "uncertainties": ["string"]
}
Coordinates are normalized to the image. Use null/empty arrays rather than
guessing when evidence is insufficient."""

ARCHITECTURE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["building_type", "facade", "opening_groups", "occlusions", "uncertainties"],
    "properties": {
        "building_type": {"$ref": "#/$defs/string_evidence"},
        "facade": {
            "type": "object", "additionalProperties": False,
            "required": ["bbox", "visible_storeys", "bay_count", "repetition"],
            "properties": {
                "bbox": {"anyOf": [{"$ref": "#/$defs/bbox"}, {"type": "null"}]},
                "visible_storeys": {"$ref": "#/$defs/count_evidence"},
                "bay_count": {"$ref": "#/$defs/count_evidence"},
                "repetition": {"type": "object", "additionalProperties": False, "required": ["value", "confidence"], "properties": {"value": {"type": "string", "enum": sorted(ALLOWED_REPETITION)}, "confidence": {"$ref": "#/$defs/confidence"}}},
            },
        },
        "opening_groups": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["type", "rows", "columns", "region", "confidence"], "properties": {"type": {"type": "string", "enum": ["window", "door", "mixed", "unknown"]}, "rows": {"type": "integer", "minimum": 0, "maximum": 100}, "columns": {"type": "integer", "minimum": 0, "maximum": 100}, "region": {"$ref": "#/$defs/bbox"}, "confidence": {"$ref": "#/$defs/confidence"}}}},
        "occlusions": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["region", "likely_hidden_opening", "confidence", "reason"], "properties": {"region": {"$ref": "#/$defs/bbox"}, "likely_hidden_opening": {"type": "boolean"}, "confidence": {"$ref": "#/$defs/confidence"}, "reason": {"type": "string"}}}},
        "uncertainties": {"type": "array", "items": {"type": "string"}},
    },
    "$defs": {
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "bbox": {"type": "array", "items": {"type": "number", "minimum": 0, "maximum": 1}, "minItems": 4, "maxItems": 4},
        "string_evidence": {"type": "object", "additionalProperties": False, "required": ["value", "confidence"], "properties": {"value": {"type": "string"}, "confidence": {"$ref": "#/$defs/confidence"}}},
        "count_evidence": {"type": "object", "additionalProperties": False, "required": ["value", "confidence"], "properties": {"value": {"type": "integer", "minimum": 0, "maximum": 100}, "confidence": {"$ref": "#/$defs/confidence"}}},
    },
}


def _confidence(value: Any, field_name: str) -> float:
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{field_name} confidence must be within [0, 1]")
    return number


def _count(value: Any, field_name: str) -> int:
    number = int(value)
    if number < 0 or number > 100:
        raise ValueError(f"{field_name} must be within [0, 100]")
    return number


def _bbox(value: Any, field_name: str) -> list[float] | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"{field_name} must be [x1, y1, x2, y2]")
    box = [float(item) for item in value]
    if not all(0.0 <= item <= 1.0 for item in box) or box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError(f"{field_name} must be a valid normalized bbox")
    return box


@dataclass(frozen=True)
class ValueEvidence:
    value: str | int
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "confidence": round(self.confidence, 4)}


@dataclass(frozen=True)
class OpeningGroupEvidence:
    type: str
    rows: int
    columns: int
    region: list[float]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "rows": self.rows, "columns": self.columns, "region": self.region, "confidence": round(self.confidence, 4)}


@dataclass(frozen=True)
class OcclusionEvidence:
    region: list[float]
    likely_hidden_opening: bool
    confidence: float
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"region": self.region, "likely_hidden_opening": self.likely_hidden_opening, "confidence": round(self.confidence, 4), "reason": self.reason}


@dataclass
class ArchitecturalEvidence:
    photo_id: str
    provider: str
    model: str
    building_type: ValueEvidence
    visible_storeys: ValueEvidence
    bay_count: ValueEvidence
    repetition: ValueEvidence
    facade_bbox: list[float] | None = None
    opening_groups: list[OpeningGroupEvidence] = field(default_factory=list)
    occlusions: list[OcclusionEvidence] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    prompt_version: str = PROMPT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PROMPT_VERSION,
            "photo_id": self.photo_id,
            "provider": self.provider,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "building_type": self.building_type.to_dict(),
            "facade": {"bbox": self.facade_bbox, "visible_storeys": self.visible_storeys.to_dict(), "bay_count": self.bay_count.to_dict(), "repetition": self.repetition.to_dict()},
            "opening_groups": [item.to_dict() for item in self.opening_groups],
            "occlusions": [item.to_dict() for item in self.occlusions],
            "uncertainties": self.uncertainties,
        }


def parse_architectural_evidence(content: str | dict[str, Any], *, photo_id: str, provider: str, model: str) -> ArchitecturalEvidence:
    payload = extract_json_payload(content) if isinstance(content, str) else content
    facade = payload.get("facade")
    if not isinstance(facade, dict):
        raise ValueError("facade object is required")

    def value_field(container: dict[str, Any], name: str, *, integer: bool = False) -> ValueEvidence:
        item = container.get(name)
        if not isinstance(item, dict) or "value" not in item or "confidence" not in item:
            raise ValueError(f"{name} evidence is required")
        value = _count(item["value"], name) if integer else str(item["value"]).strip()
        if not integer and not value:
            raise ValueError(f"{name} value must not be empty")
        return ValueEvidence(value, _confidence(item["confidence"], name))

    building_type = value_field(payload, "building_type")
    storeys = value_field(facade, "visible_storeys", integer=True)
    bays = value_field(facade, "bay_count", integer=True)
    repetition = value_field(facade, "repetition")
    if repetition.value not in ALLOWED_REPETITION:
        raise ValueError("repetition value is invalid")

    groups = []
    for index, item in enumerate(payload.get("opening_groups") or []):
        group_type = str(item.get("type", "unknown"))
        if group_type not in {"window", "door", "mixed", "unknown"}:
            raise ValueError(f"opening_groups[{index}].type is invalid")
        groups.append(OpeningGroupEvidence(group_type, _count(item.get("rows", 0), "rows"), _count(item.get("columns", 0), "columns"), _bbox(item.get("region"), f"opening_groups[{index}].region") or [0, 0, 1, 1], _confidence(item.get("confidence", 0), f"opening_groups[{index}]")))

    occlusions = []
    for index, item in enumerate(payload.get("occlusions") or []):
        occlusions.append(OcclusionEvidence(_bbox(item.get("region"), f"occlusions[{index}].region") or [0, 0, 1, 1], bool(item.get("likely_hidden_opening", False)), _confidence(item.get("confidence", 0), f"occlusions[{index}]"), str(item.get("reason", ""))))

    return ArchitecturalEvidence(photo_id=photo_id, provider=provider, model=model, building_type=building_type, visible_storeys=storeys, bay_count=bays, repetition=repetition, facade_bbox=_bbox(facade.get("bbox"), "facade.bbox"), opening_groups=groups, occlusions=occlusions, uncertainties=[str(item) for item in (payload.get("uncertainties") or [])])


def write_evidence_cache(path: Path, evidence: ArchitecturalEvidence) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_evidence_cache(path: Path) -> ArchitecturalEvidence:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return parse_architectural_evidence(payload, photo_id=payload["photo_id"], provider=payload["provider"], model=payload["model"])


def request_architectural_evidence(
    image_path: Path,
    *,
    photo_id: str,
    provider: str,
    model: str,
    api_key: str,
    base_url: str | None = None,
    timeout: float = 120.0,
) -> ArchitecturalEvidence:
    """Request structured evidence from an OpenAI-compatible or Gemini VLM."""
    normalized = provider.lower().strip()
    mime, data = encode_image_base64(image_path, max_dim=1536, jpeg_quality=88)
    user_text = "Analyze this facade as architectural evidence. Return JSON only."
    if normalized in {"openai", "openai_compatible"}:
        payload = {
            "model": model,
            "store": False,
            "instructions": SYSTEM_PROMPT,
            "input": [
                {"role": "user", "content": [{"type": "input_text", "text": user_text}, {"type": "input_image", "detail": "high", "image_url": f"data:{mime};base64,{data}"}]},
            ],
            "text": {"format": {"type": "json_schema", "name": "geomora_architectural_evidence", "strict": True, "schema": ARCHITECTURE_SCHEMA}},
        }
        body = post_json_with_retries(
            f"{(base_url or 'https://api.openai.com/v1').rstrip('/')}/responses",
            payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=timeout,
        )
        content = body.get("output_text")
        if not content:
            content = next(part["text"] for item in body.get("output", []) if item.get("type") == "message" for part in item.get("content", []) if part.get("type") == "output_text")
    elif normalized == "gemini":
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}, {"inline_data": {"mime_type": mime, "data": data}}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        }
        body = post_json_with_retries(gemini_generate_url(model), payload, headers=gemini_headers(api_key), timeout=timeout)
        content = body["candidates"][0]["content"]["parts"][0]["text"]
    else:
        raise ValueError("provider must be openai, openai_compatible or gemini")
    return parse_architectural_evidence(content, photo_id=photo_id, provider=normalized, model=model)


def provider_api_key(provider: str) -> str | None:
    from .runtime_settings import provider_api_key as runtime_provider_api_key
    return runtime_provider_api_key(provider)
