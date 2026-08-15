# Geomora

Architectural geometry reconstruction system for SketchUp.

Phase 0 implements the **Architectural IR** and **SketchUp Native Geometry Kernel**.

**Phase 1** adds the **Reconstruction Workspace** (HtmlDialog + manual facade definition). See [PHASE_1.md](docs/PHASE_1.md) — **complete**.

**Phase 2** (core complete): perspective rectification + manual 4-corner UI — see [PHASE_2.md](docs/PHASE_2.md). Requires local Python backend (`backend/start_server.bat`).

**Phase 4** (core complete): geometry rationalization — see [PHASE_4.md](docs/PHASE_4.md).

Test images: see [examples/README.md](examples/README.md).

## Pipeline

```text
JSON Fixture → IR Loader → Parser → Validator → Domain Model → SketchUp Generator
```

## Repository Layout

```text
plugin/          SketchUp Ruby extension
schemas/         IR JSON Schema
examples/        Phase 0 test fixtures
tests/           Pure Ruby unit tests + invalid fixtures
docs/            Architecture documentation
```

## Developer Setup

Choose one installation method.

### Option A — RBZ Install (recommended)

Build and install the extension package:

```powershell
# From repository root
.\build_rbz.ps1
```

This creates `dist/geomora.rbz`. In SketchUp:

1. **Window → Extension Manager → Install Extension**
2. Select `dist/geomora.rbz`
3. Restart SketchUp when prompted

The build script syncs `examples/facade_phase0.json` into `plugin/geomora/examples/` before packaging.

### Option B — Symlink (for active development)

Create a symlink from the plugin loader into your SketchUp Plugins folder:

**Windows (PowerShell, admin may be required):**

```powershell
New-Item -ItemType SymbolicLink `
  -Path "$env:APPDATA\SketchUp\SketchUp 2024\SketchUp\Plugins\geomora.rb" `
  -Target "F:\development\Geomora\plugin\geomora.rb"
```

Adjust the SketchUp version year in the path as needed.

The loader (`plugin/geomora.rb`) registers the extension; all implementation lives under `plugin/geomora/`.

For symlink dev, copy the fixture into the plugin bundle after editing the repo fixture:

```powershell
Copy-Item examples\facade_phase0.json plugin\geomora\examples\facade_phase0.json -Force
```

Or run `.\build_rbz.ps1` — it syncs the fixture automatically.

### 2. Run Unit Tests (no SketchUp required)

```bash
ruby tests/run_tests.rb
```

### 3. Verify in SketchUp

1. Restart SketchUp
2. Open **Extensions → Geomora**
3. **Extensions → Geomora → Open Workspace** (Phase 1)
4. Or use **Generate Phase 0 Fixture** / **Validate Phase 0 Fixture**

### Acceptance Checks

- Wall: 10000 × 3300 × 240 mm
- 4 windows (1500 × 1500 mm) sharing one `window_standard_1500` definition
- 1 door (900 × 2100 mm)
- Real wall openings (not surface decals)
- Single Ctrl+Z removes entire generation
- Running Generate three times produces one project (replace strategy)

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [IR.md](docs/IR.md)
- [PHASE_0.md](docs/PHASE_0.md)
- [PHASE_1.md](docs/PHASE_1.md) — complete
- [PHASE_2.md](docs/PHASE_2.md) — planning

## License

TBD
