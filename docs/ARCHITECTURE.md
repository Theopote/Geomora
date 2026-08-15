# Geomora Architecture

## Overview

Geomora reconstructs **architecture**, not pixels. Phase 0 establishes the deterministic geometry foundation that future AI perception systems will depend on.

## Layer Boundaries

```text
┌─────────────────────────────────────┐
│  Future: AI Perception (Phase 1+)   │  ← NOT in Phase 0
├─────────────────────────────────────┤
│  Geomora Architectural IR v0.1      │  ← JSON contract
├─────────────────────────────────────┤
│  IR Loader / Parser / Validator     │  ← Pure Ruby, SketchUp-independent
├─────────────────────────────────────┤
│  Domain Model (Project, Wall, …)    │  ← Validated structs, no SU API
├─────────────────────────────────────┤
│  SketchUp Geometry Kernel           │  ← Generators, components, tags
└─────────────────────────────────────┘
```

## IR → Generator Flow

```text
examples/facade_phase0.json
        ↓
   Core::Loader          (read JSON)
        ↓
   IR::Parser            (Hash → domain objects)
        ↓
   IR::Validator         (hard stop on invalid IR)
        ↓
   Generators::ProjectGenerator
        ├── BuildingGenerator
        │     └── StoreyGenerator
        │           ├── WallGenerator
        │           ├── OpeningGenerator   (wall − opening)
        │           ├── WindowGenerator    (ComponentDefinition reuse)
        │           └── DoorGenerator
        └── ComponentManager
```

## Why AI Is Absent (Phase 0–1)

Phase 0 proves the pipeline:

```text
Validated Architectural Data → Native SketchUp Geometry
```

The SketchUp Generator has **no knowledge** of:

- how objects were detected
- which AI model produced the IR
- whether data originated from a photograph

This boundary ensures AI can be swapped, upgraded, or run offline without touching the geometry kernel.

## Phase Roadmap

| Phase | Status | Focus |
|---|---|---|
| 0 | Complete | IR + SketchUp geometry kernel |
| 1 | Complete | HtmlDialog workspace + manual facade definition |
| 2 | Complete (core) | Perspective rectification (OpenCV, local Python); manual 4-corner UI v0.5.0 |
| 3 | In progress | Semantic detection (`contour_v1` / `yolo_v1`) + overlay editing |
| 4 | Complete (core) | Geometry rationalization — snap, equal spacing, symmetry |
| 5 | Complete (core) | Pattern intelligence — bay detection, shared components |
| 6 | Complete (core) | Multi-view registration + fusion (6.5) |
| 7+ | Future | Full building elements |

See `docs/PHASE_0.md` … `PHASE_6.md`, `ACCEPTANCE.md`.

## Key Design Decisions (ADRs)

| ID | Decision |
|---|---|
| ADR-001 | Architectural IR sits between AI and SketchUp |
| ADR-002 | Internal units are millimetres |
| ADR-003 | Wall = baseline + height + thickness |
| ADR-004 | Baseline = wall centreline |
| ADR-005 | Repeated elements use SketchUp Components |
| ADR-006 | Generation is one SketchUp operation (Ctrl+Z) |
| ADR-007 | AI excluded from Phase 0 |
| ADR-008 | Native editable geometry, not triangle meshes |
| ADR-009 | Validation before generation |
| ADR-010 | Domain layer stays SketchUp-independent |

## Module Responsibilities

| Module | Responsibility |
|---|---|
| `core/` | Loading, orchestration, errors, logging |
| `ir/` | Parse, validate, domain models |
| `geometry/` | Units, vectors, polygon helpers |
| `generators/` | SketchUp geometry creation |
| `components/` | ComponentDefinition cache and reuse |
| `metadata/` | AttributeDictionary read/write |
| `tags/` | Layer/tag management |
| `transactions/` | Single-operation wrap |
| `ui/` | Minimal dev menu commands |

## Error Handling

All failures raise explicit exceptions (`IRValidationError`, `GeometryGenerationError`, etc.). Failed generation aborts the SketchUp operation — no partial geometry is left behind.

## Repeatability

Before each generation, `ProjectGenerator` finds and removes the existing project container by `geomora.project_id` metadata. Unrelated user geometry is never touched.
