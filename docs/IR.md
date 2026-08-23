# Geomora Architectural IR v0.1

## Schema

Location: `schemas/geomora-ir-v0.1.schema.json`

Top-level structure:

```json
{
  "schema_version": "0.1",
  "project": {},
  "buildings": [],
  "openings": [],
  "components": [],
  "constraints": [],
  "sources": []
}
```

## Units

- IR input unit for Phase 0: **mm** (officially supported)
- All internal architectural values are normalized to millimetres
- Conversion to SketchUp inches happens only at the API boundary via `Geometry::Units.mm_to_length`
- Never scatter unit conversion in generator classes

## Coordinate System

```json
"coordinate_system": "z_up"
```

- X, Y: horizontal plan
- Z: vertical (up)

## Wall Baseline Convention

> **The baseline represents the wall centreline.**

```json
"geometry": {
  "baseline": [[0, 0, 0], [10000, 0, 0]],
  "height": 3300,
  "thickness": 240
}
```

- `baseline[0]` → start point (mm)
- `baseline[1]` → end point (mm)
- `height` → vertical extent above storey elevation (mm)
- `thickness` → total wall thickness (mm), offset ±half from centreline

## Openings

Windows and doors are defined in the top-level `openings` array and referenced from walls via `opening_ids`.

```json
{
  "id": "window_001",
  "type": "window",
  "parent_id": "wall_001",
  "geometry": {
    "offset": 500,
    "sill_height": 900,
    "width": 1500,
    "height": 1500,
    "depth": 240
  }
}
```

- `offset` — distance along wall baseline from start to opening left edge (mm)
- `sill_height` — bottom of opening above storey elevation (mm); doors default to 0
- `width`, `height` — opening dimensions (mm)
- `depth` — cut depth, typically equals wall thickness

Openings must fit within wall bounds and must not overlap.

## Components

Component definitions describe reusable geometry:

```json
{
  "id": "window_standard_1500",
  "type": "window",
  "parameters": { "width": 1500, "height": 1500 }
}
```

Instances reference definitions:

```json
"component": { "definition_id": "window_standard_1500" }
```

Phase 0 target: **one definition, many instances**.

## Constraints

Constraints are parsed, validated, and preserved — **not solved** in Phase 0.

Supported types:

```text
parallel, perpendicular, coplanar, horizontal, vertical,
equal_width, equal_height, equal_spacing, symmetry, align,
fixed_dimension, grid
```

Reconstruction Core may attach evidence metadata to a constraint:

```json
{
  "id": "constraint_001",
  "type": "equal_width",
  "targets": ["window_01", "window_02"],
  "priority": "soft",
  "confidence": 0.86,
  "weight": 0.86,
  "source": "cv_pattern+vlm",
  "status": "proposed",
  "evidence": {}
}
```

Only user or surveyed dimensions may create hard constraints. CV and VLM
pattern inference produces soft proposals; VLM may strengthen a proposal but
cannot invent target entities.

## Confidence and Source

Elements may carry:

```json
"confidence": 1.0
```

```json
"source": { "source_id": "photo_001" }
```

Phase 0 does not use these for geometry decisions.

## Validation Rules

The validator rejects:

- Unsupported schema version
- Missing required fields
- Duplicate entity IDs
- Invalid references (`parent_id`, `storey_id`, constraint targets)
- Negative or zero dimensions
- Zero-length wall baselines
- Unsupported units
- Openings outside wall bounds
- Opening height exceeding wall height
- Overlapping openings

Invalid IR **never** reaches the generator.
