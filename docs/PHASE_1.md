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

## Acceptance Criteria

Legend: `[x]` verified · `[~]` code-only · `[ ]` pending

- [x] Workspace opens without error — SketchUp 2026 user verified
- [x] Reference image loads and displays — user verified
- [x] Phase 0 template loads into form — user verified (`Template loaded`)
- [x] Elements tree updates when parameters change — user verified
- [x] Validate shows success for default template values — user verified
- [x] Generate produces correct SketchUp model from workspace — user verified
- [x] Invalid parameters show actionable error — `IRValidationError` via validator; abort on generate
- [x] Phase 0 menu commands still work — Generate / Validate fixture retained

**Gate status: PASSED** (2026-08-16, user verified)

## Version

Introduced in **Geomora v0.2.0**.

---

# Phase 1.14 — Formal Audit Report

**Audit date:** 2026-08-16  
**Extension version:** 0.2.0  
**Platform:** SketchUp 2026.2 / Windows 10

## 1. Phase 1 Summary

Phase 1 delivers the **Reconstruction Workspace** — a four-panel HtmlDialog for manual facade definition. Users load a reference image, edit wall/window/door parameters, validate IR, and generate SketchUp geometry through the unchanged Phase 0 kernel. No AI, no backend.

## 2. Files Added (Phase 1)

```text
plugin/geomora/core/ir_builder.rb
plugin/geomora/ui/workspace_dialog.rb
plugin/geomora/ui/workspace/index.html
plugin/geomora/ui/workspace/app.js
plugin/geomora/ui/workspace/styles.css
tests/ir/ir_builder_test.rb
frontend/README.md
docs/PHASE_1.md
```

## 3. Files Modified

```text
plugin/geomora/core/project.rb       — generate_from_data, validate_data
plugin/geomora/ui/commands.rb        — Open Workspace menu + toolbar
plugin/geomora/loader.rb           — new requires
plugin/geomora/version.rb          — 0.2.0
README.md
```

## 4. Architecture Implemented

```text
Workspace UI (thin)
    ↓
IRBuilder (Ruby, SketchUp-independent logic)
    ↓
Phase 0 pipeline (unchanged)
```

ADR preserved: IR remains the contract; UI does not call SketchUp generators directly.

## 5. Manual Verification

| Test | Result |
|---|---|
| Open Workspace | ✅ |
| Load Phase 0 Template | ✅ |
| Load Reference Image | ✅ |
| Validate | ✅ |
| Generate | ✅ |
| Elements / Inspector sync | ✅ |

## 6. Known Limitations

- Vanilla HTML/JS workspace (no React build yet)
- Image is display-only; no overlay or click-to-measure
- One facade wall only (single wall IR builder)
- No save/load of workspace session to disk
- No undo inside workspace (SketchUp undo applies to Generate only)

## 7. Technical Debt

- [ ] Migrate workspace to React/Vite (`frontend/`)
- [ ] Persist workspace state / export IR JSON to file
- [ ] Add IRBuilder unit test to CI when Ruby available
- [ ] Pre-build require-path validation in `build_rbz.ps1`

## 8. Recommendation

### READY FOR PHASE 2 PLANNING

Phase 1 gate passed. Proceed to **Perspective Rectification** per `docs/PHASE_2.md`.

---

**Next:** [PHASE_2.md](PHASE_2.md) — Perspective Photo → Rectified Facade
