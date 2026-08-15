# Geomora Phase 0 — Cursor Master Prompt v0.1

You are the lead software architect and senior SketchUp Ruby plugin engineer for a new project named **Geomora**.

Geomora is an architectural geometry reconstruction system for SketchUp.

Your task is **NOT** to build the AI system yet.

Your ONLY responsibility in this task is to implement:

> **Phase 0 — Geomora Architectural IR + SketchUp Native Geometry Kernel**

Do not move to Phase 1.

Do not implement AI.

Do not add features outside the scope defined below.

---

# 1. Product Philosophy

Geomora is NOT primarily:

```text
Photo → Mesh
```

Geomora is designed around:

```text
Reality
→ Architectural Understanding
→ Geometry Rationalization
→ Architectural IR
→ Native SketchUp Geometry
```

The long-term product philosophy is:

> Geomora does not reconstruct pixels.  
> Geomora reconstructs architecture.

Phase 0 establishes the deterministic architectural geometry foundation upon which future AI perception systems will depend.

---

# 2. Critical Development Rule

Do NOT begin coding immediately.

First:

1. inspect the repository;
2. understand the existing files;
3. identify anything already implemented;
4. compare the current repository against this specification;
5. propose the minimal Phase 0 implementation plan;
6. only then begin implementation.

Never overwrite useful existing work without understanding it first.

If the repository already contains an implementation for part of Phase 0:

- audit it;
- preserve correct code;
- refactor only when justified;
- document why changes are required.

---

# 3. Strict Scope

You MAY implement:

```text
SketchUp Ruby extension bootstrap

Geomora Architectural IR v0.1

IR loader

IR parser

IR validator

Architecture model objects

Unit handling

SketchUp geometry helpers

Building generator

Storey generator

Wall generator

Window generator

Door generator

Opening generation

Component manager

Tag manager

Geomora metadata

SketchUp transaction management

Fixture JSON

Unit tests

SketchUp integration tests where appropriate

Documentation
```

You MUST NOT implement:

```text
SAM
SAM2
YOLO
GroundingDINO
Depth Anything
Marigold
COLMAP
NeRF
Gaussian Splatting
Computer vision
Image processing
LLM integration
OpenAI integration
FastAPI backend
WebSocket backend
Cloud API
Photo reconstruction
Multi-view reconstruction
React UI
production HtmlDialog workspace
IFC
Revit
Rhino
Blender integration
Geometry Rationalization Solver
Constraint solving algorithm
```

Constraint structures may be represented in the IR schema, but the solver itself MUST NOT be implemented during Phase 0.

---

# 4. Architectural Boundary

The core Phase 0 pipeline must be:

```text
JSON Fixture
    ↓
IR Loader
    ↓
IR Parser
    ↓
IR Validator
    ↓
Architectural Model
    ↓
SketchUp Generator
    ↓
Native SketchUp Geometry
```

There must be no dependency on AI.

The SketchUp Generator must not know:

- how an object was detected;
- which AI model found it;
- whether it originated from an image.

The generator receives validated architectural data only.

---

# 5. Repository Structure

Prefer approximately this structure unless the existing repository already has a better compatible structure:

```text
geomora/
│
├── plugin/
│   ├── geomora.rb
│   │
│   └── geomora/
│       ├── extension.rb
│       ├── version.rb
│       │
│       ├── core/
│       │   ├── loader.rb
│       │   ├── project.rb
│       │   └── errors.rb
│       │
│       ├── ir/
│       │   ├── parser.rb
│       │   ├── validator.rb
│       │   │
│       │   └── models/
│       │       ├── project.rb
│       │       ├── building.rb
│       │       ├── storey.rb
│       │       ├── wall.rb
│       │       ├── opening.rb
│       │       ├── window.rb
│       │       └── door.rb
│       │
│       ├── geometry/
│       │   ├── units.rb
│       │   ├── vectors.rb
│       │   └── polygon.rb
│       │
│       ├── generators/
│       │   ├── project_generator.rb
│       │   ├── building_generator.rb
│       │   ├── storey_generator.rb
│       │   ├── wall_generator.rb
│       │   ├── opening_generator.rb
│       │   ├── window_generator.rb
│       │   └── door_generator.rb
│       │
│       ├── components/
│       │   └── component_manager.rb
│       │
│       ├── metadata/
│       │   └── attributes.rb
│       │
│       ├── transactions/
│       │   └── operation.rb
│       │
│       └── ui/
│           └── commands.rb
│
├── schemas/
│   └── geomora-ir-v0.1.schema.json
│
├── examples/
│   └── facade_phase0.json
│
├── tests/
│   ├── fixtures/
│   ├── ir/
│   ├── geometry/
│   └── integration/
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── IR.md
│   └── PHASE_0.md
│
└── README.md
```

Do not create unnecessary empty architecture for future phases.

`backend/` and `frontend/` may remain absent or contain only explanatory placeholders if already required by the repository.

---

# 6. SketchUp Extension Bootstrap

Implement proper SketchUp extension registration.

Requirements:

- plugin loads without Ruby errors;
- namespaces do not pollute the global scope;
- all implementation belongs under a namespace such as:

```ruby
module Geomora
end
```

Use normal SketchUp extension registration patterns.

Avoid global variables.

Avoid monkey patches.

Avoid modifying native SketchUp classes.

---

# 7. Architectural IR v0.1

Create:

```text
schemas/geomora-ir-v0.1.schema.json
```

Top-level structure:

```json
{
  "schema_version": "0.1",

  "project": {},

  "buildings": [],

  "components": [],

  "constraints": [],

  "sources": []
}
```

---

# 8. Project Schema

Support:

```json
{
  "id": "project_001",
  "name": "Phase 0 Test",
  "unit": "mm",
  "coordinate_system": "z_up",
  "default_wall_thickness": 240
}
```

For Phase 0:

```text
unit = mm
```

must be officially supported.

Internally all architectural values must be normalized to millimetres.

Do not scatter unit conversion throughout generator classes.

Create a centralized unit utility.

---

# 9. Building

Example:

```json
{
  "id": "building_001",
  "name": "Main Building",
  "storeys": []
}
```

---

# 10. Storey

Example:

```json
{
  "id": "storey_01",
  "name": "Ground Floor",
  "elevation": 0,
  "height": 3300,
  "elements": []
}
```

---

# 11. Wall

Use baseline-based architectural representation.

Example:

```json
{
  "id": "wall_001",

  "type": "wall",

  "storey_id": "storey_01",

  "geometry": {
    "baseline": [
      [0, 0, 0],
      [10000, 0, 0]
    ],

    "height": 3300,

    "thickness": 240
  },

  "semantic": {
    "exterior": true
  },

  "opening_ids": [
    "window_001",
    "window_002",
    "window_003",
    "window_004",
    "door_001"
  ],

  "confidence": 1.0
}
```

Do not represent a wall as an arbitrary triangle mesh.

---

# 12. Opening Model

Create a common conceptual abstraction for:

```text
Window
Door
Generic Opening
```

Phase 0 needs actual implementation for:

```text
Window
Door
```

---

# 13. Window

Example:

```json
{
  "id": "window_001",

  "type": "window",

  "parent_id": "wall_001",

  "geometry": {
    "offset": 800,
    "sill_height": 900,
    "width": 1500,
    "height": 1500,
    "depth": 240
  },

  "component": {
    "definition_id": "window_standard_1500"
  },

  "confidence": 1.0
}
```

The exact fixture offsets must be selected so that no window overlaps another window or the door.

---

# 14. Door

Example:

```json
{
  "id": "door_001",

  "type": "door",

  "parent_id": "wall_001",

  "geometry": {
    "offset": 8500,
    "width": 900,
    "height": 2100,
    "depth": 240
  },

  "component": {
    "definition_id": "door_standard_900"
  },

  "confidence": 1.0
}
```

Again, correct fixture geometry if the example offset conflicts with another opening.

Correctness is more important than preserving a sample coordinate.

---

# 15. Constraint Schema

The IR must reserve a structure for constraints.

Example:

```json
{
  "id": "constraint_001",

  "type": "equal_width",

  "targets": [
    "window_001",
    "window_002",
    "window_003",
    "window_004"
  ],

  "priority": "hard"
}
```

Allowed initial schema values may include:

```text
parallel
perpendicular
coplanar
horizontal
vertical
equal_width
equal_height
equal_spacing
symmetry
align
fixed_dimension
grid
```

IMPORTANT:

Do not implement constraint solving.

Only:

- parse;
- validate;
- preserve.

---

# 16. Confidence and Source

Allow architectural elements to carry:

```json
{
  "confidence": 1.0
}
```

and optionally:

```json
{
  "source": {
    "source_id": "photo_001"
  }
}
```

Phase 0 does not use this information for geometry decisions.

---

# 17. IR Validation

Create a real validator.

Do not rely only on JSON syntax parsing.

The validator must detect at least:

```text
unsupported schema version

missing required fields

duplicate entity ID

invalid reference

invalid parent_id

invalid storey_id

negative width

negative height

negative thickness

zero-length wall baseline

unsupported unit

opening outside wall

opening height exceeding wall

opening overlap where clearly invalid
```

Validation failure must stop generation.

Do not silently repair invalid input in Phase 0.

Return actionable messages.

Example:

```text
IRValidationError:
window_003 exceeds bounds of wall_001
```

---

# 18. Domain Model

Do not pass raw nested Hash objects everywhere.

Create small architectural model classes or equivalent structured domain objects.

Examples:

```text
Project
Building
Storey
Wall
Window
Door
Constraint
```

Responsibilities:

- hold validated data;
- expose semantic properties;
- avoid SketchUp API calls.

Domain objects must remain SketchUp-independent whenever practical.

---

# 19. Geometry Generator

Create a clean generation layer.

Suggested interface:

```ruby
generator.generate(project)
```

which delegates to specialized generators.

Do not put the whole geometry generation algorithm into one method.

---

# 20. Wall Geometry

For every wall:

Input:

```text
baseline
height
thickness
```

Generate a clean native SketchUp wall volume.

Requirements:

```text
correct length
correct height
correct thickness
correct orientation
clean faces
clean edges
no duplicate coplanar surfaces
```

Wall thickness should be consistently placed relative to the baseline.

Choose and document a rule such as:

```text
baseline = wall centerline
```

or another explicit convention.

Use the same convention everywhere.

Recommended Phase 0 convention:

> baseline represents the wall centreline.

Document this in IR.md.

---

# 21. Wall Openings

This is a critical requirement.

Windows and doors must produce actual openings in the wall.

Wrong:

```text
wall cube
+
window object pasted onto wall
```

Correct:

```text
wall geometry
-
opening geometry
```

or an equivalent robust native SketchUp face construction strategy.

The wall must visually and geometrically contain the opening.

Do not fake openings using materials.

---

# 22. Window Components

Four identical windows must reuse ONE:

```text
ComponentDefinition
```

and create FOUR:

```text
ComponentInstance
```

Target:

```text
window_standard_1500
├── instance 1
├── instance 2
├── instance 3
└── instance 4
```

Do not duplicate raw component geometry four times.

---

# 23. Window Geometry

Phase 0 window geometry may remain intentionally simple.

A minimum acceptable window may include:

```text
outer frame
inner opening/glass placeholder
```

Do not spend Phase 0 implementing architectural window detail.

The purpose is to prove:

```text
IR
→ ComponentDefinition
→ ComponentInstance
```

---

# 24. Door Geometry

The Phase 0 door may also remain simple.

Focus on:

```text
correct opening
correct dimensions
correct placement
component reuse architecture
```

not visual detailing.

---

# 25. SketchUp Object Hierarchy

Generate a predictable hierarchy.

Suggested:

```text
Geomora Project
└── Building
    └── Storey
        ├── Wall
        ├── Window Instance
        ├── Window Instance
        ├── Window Instance
        ├── Window Instance
        └── Door Instance
```

Use Groups and Components sensibly.

Do not create deeply nested meaningless containers.

---

# 26. Tags

Create/reuse:

```text
Geomora_Walls
Geomora_Windows
Geomora_Doors
Geomora_Roofs
Geomora_Reference
```

Prefer tags on:

```text
Group
ComponentInstance
```

Do not unnecessarily tag raw Faces and Edges.

Ensure repeated runs reuse existing tags.

---

# 27. Metadata

Use SketchUp AttributeDictionary.

Dictionary:

```text
geomora
```

Store at least:

```text
entity_id
entity_type
schema_version
project_id
```

Example:

```ruby
entity.set_attribute(
  "geomora",
  "entity_id",
  "wall_001"
)
```

This metadata will later support:

```text
IR ↔ SketchUp Entity
```

synchronization.

---

# 28. Transaction Management

A complete generation must be a SINGLE SketchUp operation.

Expected conceptual behavior:

```ruby
model.start_operation(
  "Geomora Generate",
  true
)

begin
  ...
  model.commit_operation
rescue => e
  model.abort_operation
  raise
end
```

The user must be able to press:

```text
Ctrl + Z
```

once and remove the complete generated model.

This is a hard acceptance criterion.

---

# 29. Repeatability / Idempotency

Running:

```text
Generate
Generate
Generate
```

must not create three overlapping buildings by default.

Implement a clear Phase 0 strategy.

Preferred:

```text
Replace Existing Geomora Project
```

Use metadata to locate the previous generated project.

Suggested logic:

```text
find project with:
geomora.project_id == project_001

remove generated container

regenerate
```

Do not accidentally remove unrelated user geometry.

---

# 30. Error Handling

Create explicit exceptions such as:

```ruby
GeomoraError

IRValidationError

UnsupportedSchemaError

GeometryGenerationError

ReferenceResolutionError
```

Do not swallow exceptions.

Do not use empty rescue blocks.

Do not leave SketchUp in a partially generated state after failure.

---

# 31. Logging

Implement lightweight logging.

Required levels:

```text
DEBUG
INFO
WARN
ERROR
```

Example:

```text
[Geomora][INFO] IR loaded
[Geomora][INFO] Validation complete
[Geomora][DEBUG] Generating wall_001
[Geomora][DEBUG] Creating window component window_standard_1500
[Geomora][INFO] Generation complete
```

Do not introduce a large external logging dependency.

---

# 32. Phase 0 Fixture

Create:

```text
examples/facade_phase0.json
```

Required architectural test:

```text
wall length:
10000 mm

wall height:
3300 mm

wall thickness:
240 mm

windows:
4

window dimensions:
1500 × 1500 mm

window sill:
900 mm

door:
1

door dimensions:
900 × 2100 mm
```

Select offsets that produce a valid elevation.

All four windows must share:

```text
window_standard_1500
```

ComponentDefinition.

---

# 33. Invalid Fixtures

Create at least:

```text
tests/fixtures/invalid_duplicate_id.json

tests/fixtures/invalid_parent.json

tests/fixtures/invalid_negative_dimension.json

tests/fixtures/invalid_opening_bounds.json
```

All must fail validation intentionally.

---

# 34. Unit Tests

Test pure Ruby logic independently where possible.

At minimum test:

```text
schema version

ID uniqueness

reference resolution

wall dimension validation

opening bound validation

unit conversion

component definition cache behavior

metadata helper behavior
```

Do not pretend to unit-test SketchUp native API outside its runtime if that produces fake or meaningless tests.

Separate:

```text
pure unit tests
```

from:

```text
SketchUp integration tests
```

---

# 35. Integration Test

Provide a simple SketchUp-side integration or verification command.

For example:

```text
Plugins
→ Geomora
→ Run Phase 0 Fixture
```

The command should:

```text
load examples/facade_phase0.json

validate

generate model

report result
```

This command is for development verification.

It is NOT the final Geomora UI.

---

# 36. Minimal Menu

Phase 0 may expose:

```text
Extensions
→ Geomora
    → Generate Phase 0 Fixture
    → Validate Phase 0 Fixture
```

Do not implement a full production UI.

---

# 37. Documentation

Create/update:

## docs/ARCHITECTURE.md

Describe:

```text
layer boundaries

IR → Generator flow

why AI is intentionally absent
```

## docs/IR.md

Document:

```text
schema

units

baseline convention

openings

components

constraints
```

## docs/PHASE_0.md

Document:

```text
scope

test fixture

how to run

acceptance criteria
```

Update README with minimal developer setup.

---

# 38. Code Quality Rules

Follow these rules.

### Rule 1

Prefer small classes.

### Rule 2

Prefer explicit data flow.

### Rule 3

Avoid speculative abstractions.

### Rule 4

Do not create unused future-phase infrastructure.

### Rule 5

Avoid giant files.

### Rule 6

Avoid deep inheritance.

Prefer composition.

### Rule 7

No global mutable state unless absolutely required by SketchUp extension lifecycle.

### Rule 8

No silent fallback geometry.

### Rule 9

No automatic correction of invalid IR in Phase 0.

### Rule 10

Every generated major object must retain Geomora identity metadata.

---

# 39. Do Not Overengineer

Phase 0 is an architectural foundation, not a complete BIM system.

Do NOT implement:

```text
wall joins

automatic corner cleanup

complex roofs

multilayer wall assemblies

IFC property sets

parametric sash systems

materials database

structural systems

stairs

balconies

curtain walls
```

unless they are already implemented cleanly and necessary to preserve existing repository behavior.

---

# 40. Architectural Decisions That Are Already Final

Do not ask whether to change these unless you find a concrete technical blocker.

## ADR-001

Architectural IR exists between AI and SketchUp.

## ADR-002

Internal architectural units are millimetres.

## ADR-003

Wall is baseline + height + thickness.

## ADR-004

Wall baseline represents centreline in v0.1.

## ADR-005

Repeated elements use SketchUp Components.

## ADR-006

Generated operations are transactional.

## ADR-007

AI is excluded from Phase 0.

## ADR-008

SketchUp native editable geometry is preferred over triangle mesh.

## ADR-009

IR validation occurs before geometry generation.

## ADR-010

SketchUp-specific code must not leak into future perception/domain layers unnecessarily.

---

# 41. Required Development Sequence

Execute in this order.

Do not skip ahead.

## Step 0.1 — Repository Audit

Inspect repository.

Report:

```text
existing structure

existing useful code

conflicts with specification

files to preserve

files to add

files to modify
```

Do not code before completing this inspection.

---

## Step 0.2 — Skeleton

Establish only required architecture.

Confirm plugin loads.

Do not generate geometry yet.

---

## Step 0.3 — IR Schema

Implement:

```text
schema
parser
domain models
validator
```

Run validation tests.

Do not proceed until validator tests pass.

---

## Step 0.4 — Units + Geometry Helpers

Implement:

```text
mm conversion

vector helpers

wall basis

basic polygon utilities
```

Add tests.

---

## Step 0.5 — Wall Generator

Implement one wall with:

```text
10000 × 3300 × 240
```

Verify manually inside SketchUp.

---

## Step 0.6 — Opening Generator

Implement one simple valid wall opening.

Test:

```text
opening bounds

correct wall cut

clean geometry
```

---

## Step 0.7 — Window Component

Implement:

```text
one definition
multiple instances
```

Then verify all four windows reuse the same definition.

---

## Step 0.8 — Door

Implement door opening + component.

---

## Step 0.9 — Metadata + Tags

Add:

```text
AttributeDictionary

tags

entity IDs
```

---

## Step 0.10 — Transaction

Wrap full generation in one SketchUp operation.

Manually verify:

```text
Generate
Ctrl + Z
```

---

## Step 0.11 — Repeatability

Run generation three times.

Confirm:

```text
one project only
```

---

## Step 0.12 — Invalid IR

Run all invalid fixtures.

Confirm every invalid fixture fails safely.

---

## Step 0.13 — Documentation

Update all docs.

---

## Step 0.14 — Phase 0 Audit

Do not declare Phase 0 complete automatically.

Perform a final audit against the Definition of Done below.

---

# 42. Definition of Done

Phase 0 is COMPLETE only when every item is verified.

## Plugin

- [ ] extension loads successfully
- [ ] namespace is clean
- [ ] no obvious global pollution

## IR

- [ ] schema_version supported
- [ ] Project supported
- [ ] Building supported
- [ ] Storey supported
- [ ] Wall supported
- [ ] Window supported
- [ ] Door supported
- [ ] Component supported
- [ ] Constraint schema supported
- [ ] invalid IR rejected

## Wall

- [ ] length correct
- [ ] height correct
- [ ] thickness correct
- [ ] orientation correct

## Openings

- [ ] four real window openings
- [ ] one real door opening
- [ ] no fake surface-only opening

## Components

- [ ] four windows
- [ ] one shared window ComponentDefinition
- [ ] four ComponentInstances

## Organization

- [ ] Groups correct
- [ ] Tags correct
- [ ] Metadata correct

## Units

- [ ] mm input generates correct physical dimensions
- [ ] no 25.4 scale bug

## Transaction

- [ ] one Generate action
- [ ] one Ctrl+Z
- [ ] complete removal

## Repeatability

- [ ] generating three times does not stack duplicate buildings

## Error Safety

- [ ] invalid input does not leave partial geometry
- [ ] meaningful error message is produced

## Documentation

- [ ] README updated
- [ ] ARCHITECTURE.md updated
- [ ] IR.md updated
- [ ] PHASE_0.md updated

---

# 43. Final Audit Output Format

When implementation is finished, report exactly these sections:

```text
1. Phase 0 Summary

2. Files Added

3. Files Modified

4. Architecture Implemented

5. IR v0.1 Status

6. Geometry Generation Status

7. Test Results

8. Manual SketchUp Verification

9. Known Limitations

10. Technical Debt

11. Definition of Done Checklist

12. Recommendation:
    READY FOR PHASE 1
or
    NOT READY FOR PHASE 1
```

Do not recommend Phase 1 if any hard acceptance criterion remains unresolved.

---

# 44. When You Encounter a Problem

If you encounter a design problem:

Do NOT immediately redesign the architecture.

Instead:

```text
1. identify the problem;
2. explain why it blocks Phase 0;
3. identify the smallest compatible solution;
4. implement it;
5. document the decision.
```

If a problem requires changing one of the final ADRs:

STOP.

Explain the conflict before changing it.

---

# 45. Important Anti-Patterns

Do not do any of the following:

```text
one giant Ruby file

huge God class

visual model output directly driving SketchUp API

geometry generated from unvalidated hashes

copy-pasted window geometry

global state everywhere

silent unit conversion

silent geometry correction

swallowed exceptions

partial geometry after failed generation

fake tests

placeholder methods reported as complete

Phase 1 work mixed into Phase 0
```

---

# 46. Success Criterion

The final proof that Phase 0 works is extremely simple.

Given:

```text
examples/facade_phase0.json
```

Geomora must reliably produce:

```text
SketchUp

Geomora Project
└── Main Building
    └── Ground Floor
        ├── Wall
        ├── Window ×4
        └── Door ×1
```

with:

```text
wall:
10000 × 3300 × 240 mm

windows:
4 × 1500 × 1500 mm

door:
900 × 2100 mm
```

and:

```text
real openings

shared component definition

correct metadata

correct tags

safe repeated generation

single-step undo
```

If this works cleanly and repeatedly:

> Phase 0 is successful.

If it does not:

> keep working on Phase 0.

---

# FINAL INSTRUCTION

Start now with:

> **Step 0.1 — Repository Audit**

Do not start implementing AI.

Do not start Phase 1.

Do not generate speculative future modules.

First inspect the complete repository and return the Phase 0 audit and proposed minimal change plan.

Only after the audit is complete should implementation proceed.