# Geomora Frontend (Phase 1+)

Phase 1 ships an embedded HtmlDialog workspace under:

```text
plugin/geomora/ui/workspace/
  index.html
  app.js
  styles.css
```

This is intentional for RBZ distribution without a Node.js build step.

## Future migration

Per `docs/Geomora 技术架构与开发手册 v0.1.md` §6.2, the production frontend will move to:

```text
TypeScript + React + Vite
```

Planned layout:

```text
frontend/
  src/
    panels/
      Sources.tsx
      ImageViewer.tsx
      Elements.tsx
      Inspector.tsx
    App.tsx
  package.json
  vite.config.ts
```

Build output will be copied into `plugin/geomora/ui/workspace/dist/` during `build_rbz.ps1`.

## Bridge contract

Ruby callbacks (via `UI::HtmlDialog`):

| Callback | Purpose |
|---|---|
| `ready` | Load default template payload |
| `pick_image` | Open file panel for reference image |
| `load_template` | Load Phase 0 fixture as starting point |
| `validate` | Build IR from form → validate |
| `generate` | Build IR from form → generate SketchUp geometry |

JavaScript API (`window.geomora`):

| Method | Purpose |
|---|---|
| `loadPayload(data)` | Populate form and tree |
| `setImage(url, path)` | Show reference image |
| `setStatus(level, msg)` | Status bar message |
| `setIrPreview(ir)` | Update after validate/generate |
