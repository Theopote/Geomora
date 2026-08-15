# Geomora Phase 1 — Reconstruction Workspace

## Goal

```text
SketchUp + HtmlDialog + Image + Manual Facade Definition
```

Phase 1 adds a **workspace UI** for manually defining facade parameters against a reference image. **No AI.**

## Scope

### In scope

- HtmlDialog workspace (`Extensions → Geomora → Open Workspace`)
- Panels: Sources, Image Viewer, Elements, Inspector
- Manual wall / window / door parameter editing
- IR built from form via `Core::IRBuilder`
- Validate + Generate through existing Phase 0 pipeline
- Load Phase 0 template as starting point
- Load reference image (display only)

### Out of scope

- AI / computer vision
- Perspective rectification (Phase 2)
- Semantic detection (Phase 3)
- React/Vite production frontend (planned; see `frontend/README.md`)
- Backend / FastAPI

## How to use

1. Install / update RBZ (`dist/geomora.rbz`, v0.2.0+)
2. **Extensions → Geomora → Open Workspace**
3. Optional: **Load Reference Image** (facade photo for visual reference)
4. Edit wall / window / door dimensions in **Inspector**
5. Review structure in **Elements**
6. Click **Validate** then **Generate**

Or click **Load Phase 0 Template** to start from the known-good fixture values.

## Architecture

```text
HtmlDialog (app.js)
    ↕ Ruby callbacks
WorkspaceDialog
    ↓
Core::IRBuilder.build_manual_facade(params)
    ↓
Core::Project.validate_data / generate_from_data
    ↓
Phase 0 IR → Validator → Generator
```

Business logic stays in Ruby. The dialog is a thin UI shell.

## Acceptance criteria

- [ ] Workspace opens without error
- [ ] Reference image loads and displays
- [ ] Phase 0 template loads into form
- [ ] Elements tree updates when parameters change
- [ ] Validate shows success for default template values
- [ ] Generate produces correct SketchUp model from workspace
- [ ] Invalid parameters show actionable error (no partial geometry)
- [ ] Phase 0 menu commands still work

## Version

Introduced in **Geomora v0.2.0**.
