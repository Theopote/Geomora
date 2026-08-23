(function () {
  "use strict";

  const COLORS = {
    window: "#4a90e2",
    door: "#43a047",
    facade: "#f0b429",
    anchor: "#ab47bc",
    selected: "#88c0d0",
  };

  const state = {
    pack: window.PACK_DATA,
    photoIndex: 0,
    tool: "select",
    selectedKind: "opening",
    selectedId: null,
    drawing: null,
    drag: null,
    stageSize: { w: 0, h: 0 },
  };

  const els = {
    photoSelect: document.getElementById("photo-select"),
    stage: document.getElementById("stage"),
    image: document.getElementById("photo-image"),
    svg: document.getElementById("overlay-svg"),
    openingList: document.getElementById("opening-list"),
    status: document.getElementById("status"),
    photoMeta: document.getElementById("photo-meta"),
    fieldId: document.getElementById("field-id"),
    fieldType: document.getElementById("field-type"),
    fieldStorey: document.getElementById("field-storey"),
    fieldBay: document.getElementById("field-bay"),
    fieldBbox: document.getElementById("field-bbox"),
    fieldStoreyCount: document.getElementById("field-storey-count"),
    fieldBayCount: document.getElementById("field-bay-count"),
    fieldNotes: document.getElementById("field-notes"),
    fieldAnchorDistance: document.getElementById("field-anchor-distance"),
    fieldAnchorStart: document.getElementById("field-anchor-start"),
    fieldAnchorEnd: document.getElementById("field-anchor-end"),
    anchorPanel: document.getElementById("anchor-panel"),
  };

  function currentPhoto() {
    return state.pack.photos[state.photoIndex];
  }

  function currentGt() {
    return currentPhoto().ground_truth;
  }

  function clamp01(value) {
    return Math.max(0, Math.min(1, value));
  }

  function round4(value) {
    return Math.round(value * 10000) / 10000;
  }

  function normalizeRect(x1, y1, x2, y2) {
    return [
      round4(Math.min(x1, x2)),
      round4(Math.min(y1, y2)),
      round4(Math.max(x1, x2)),
      round4(Math.max(y1, y2)),
    ];
  }

  function bboxToPx(bbox) {
    const w = state.stageSize.w;
    const h = state.stageSize.h;
    return {
      x: bbox[0] * w,
      y: bbox[1] * h,
      width: (bbox[2] - bbox[0]) * w,
      height: (bbox[3] - bbox[1]) * h,
    };
  }

  function pxToNorm(x, y) {
    return [clamp01(x / state.stageSize.w), clamp01(y / state.stageSize.h)];
  }

  function setStatus(text) {
    els.status.textContent = text;
  }

  function nextOpeningId(type) {
    const gt = currentGt();
    const prefix = type === "door" ? "d" : "w";
    let max = 0;
    gt.openings.forEach(function (item) {
      const match = item.id && item.id.match(/^([wd])(\d+)(\d+)$/);
      if (match) {
        max = Math.max(max, parseInt(match[2] + match[3], 10));
      }
    });
    const next = String(max + 1).padStart(2, "0");
    return prefix + next + "1";
  }

  function selectItem(kind, id) {
    state.selectedKind = kind;
    state.selectedId = id;
    render();
    syncFields();
  }

  function syncFields() {
    const gt = currentGt();
    els.fieldStoreyCount.value = gt.topology.storey_count;
    els.fieldBayCount.value = gt.topology.bay_count;
    els.fieldNotes.value = gt.annotation_notes || "";

    const anchor = (gt.metric_anchors || [])[0];
    if (anchor) {
      els.anchorPanel.hidden = false;
      els.fieldAnchorDistance.value = anchor.distance_mm ?? "";
      els.fieldAnchorStart.value = (anchor.start || []).join(", ");
      els.fieldAnchorEnd.value = (anchor.end || []).join(", ");
    } else {
      els.anchorPanel.hidden = true;
    }

    let item = null;
    if (state.selectedKind === "opening") {
      item = gt.openings.find(function (o) {
        return o.id === state.selectedId;
      });
    } else if (state.selectedKind === "facade") {
      item = { id: "facade", type: "facade", bbox: gt.facade_bbox };
    } else if (state.selectedKind === "anchor" && anchor) {
      item = {
        id: anchor.id || "anchor_facade_width",
        type: "anchor",
        bbox: [
          Math.min(anchor.start[0], anchor.end[0]),
          Math.min(anchor.start[1], anchor.end[1]),
          Math.max(anchor.start[0], anchor.end[0]),
          Math.max(anchor.start[1], anchor.end[1]),
        ],
      };
    }

    if (!item) {
      els.fieldId.value = "";
      els.fieldType.value = "window";
      els.fieldStorey.value = "";
      els.fieldBay.value = "";
      els.fieldBbox.value = "";
      return;
    }

    els.fieldId.value = item.id || "";
    els.fieldType.value = item.type || "window";
    els.fieldStorey.value = item.storey ?? "";
    els.fieldBay.value = item.bay ?? "";
    els.fieldBbox.value = (item.bbox || []).map(round4).join(", ");
  }

  function applyFields() {
    const gt = currentGt();
    gt.topology.storey_count = parseInt(els.fieldStoreyCount.value, 10) || 1;
    gt.topology.bay_count = parseInt(els.fieldBayCount.value, 10) || 1;
    gt.annotation_notes = els.fieldNotes.value;

    if (state.selectedKind === "opening" && state.selectedId) {
      const item = gt.openings.find(function (o) {
        return o.id === state.selectedId;
      });
      if (!item) return;
      item.id = els.fieldId.value.trim() || item.id;
      item.type = els.fieldType.value;
      item.storey = parseInt(els.fieldStorey.value, 10) || item.storey;
      item.bay = parseInt(els.fieldBay.value, 10) || item.bay;
      const parts = els.fieldBbox.value.split(",").map(function (v) {
        return parseFloat(v.trim());
      });
      if (parts.length === 4 && parts.every(function (v) {
        return !Number.isNaN(v);
      })) {
        item.bbox = normalizeRect(parts[0], parts[1], parts[2], parts[3]);
      }
    } else if (state.selectedKind === "facade") {
      const parts = els.fieldBbox.value.split(",").map(function (v) {
        return parseFloat(v.trim());
      });
      if (parts.length === 4) {
        gt.facade_bbox = normalizeRect(parts[0], parts[1], parts[2], parts[3]);
      }
    }

    const anchor = (gt.metric_anchors || [])[0];
    if (anchor) {
      const distance = els.fieldAnchorDistance.value.trim();
      anchor.distance_mm = distance === "" ? null : parseFloat(distance);
      const start = els.fieldAnchorStart.value.split(",").map(parseFloat);
      const end = els.fieldAnchorEnd.value.split(",").map(parseFloat);
      if (start.length === 2) anchor.start = [round4(start[0]), round4(start[1])];
      if (end.length === 2) anchor.end = [round4(end[0]), round4(end[1])];
      if (anchor.distance_mm) anchor.status = "surveyed";
      else anchor.status = "pending_survey";
    }

    render();
  }

  function deleteSelected() {
    const gt = currentGt();
    if (state.selectedKind === "opening" && state.selectedId) {
      gt.openings = gt.openings.filter(function (o) {
        return o.id !== state.selectedId;
      });
      state.selectedId = null;
    }
    render();
    syncFields();
  }

  function addOpening(type) {
    const gt = currentGt();
    const id = nextOpeningId(type);
    gt.openings.push({
      id: id,
      type: type,
      bbox: [0.35, 0.35, 0.55, 0.55],
      storey: 1,
      bay: 1,
    });
    selectItem("opening", id);
  }

  function ensureAnchor() {
    const gt = currentGt();
    if (!gt.metric_anchors) gt.metric_anchors = [];
    if (!gt.metric_anchors.length) {
      gt.metric_anchors.push({
        id: "anchor_facade_width",
        type: "user_distance",
        status: "pending_survey",
        start: [0.05, 0.9],
        end: [0.95, 0.9],
        distance_mm: null,
        notes: "On-site measurement required",
      });
    }
    selectItem("anchor", gt.metric_anchors[0].id);
  }

  function renderOpeningList() {
    const gt = currentGt();
    els.openingList.innerHTML = "";
    const facadeLi = document.createElement("li");
    facadeLi.innerHTML = '<span class="tag facade">facade</span> facade_bbox';
    if (state.selectedKind === "facade") facadeLi.classList.add("selected");
    facadeLi.addEventListener("click", function () {
      selectItem("facade", "facade");
    });
    els.openingList.appendChild(facadeLi);

    gt.openings.forEach(function (item) {
      const li = document.createElement("li");
      li.innerHTML =
        '<span class="tag ' +
        item.type +
        '">' +
        item.type +
        "</span>" +
        item.id +
        " · s" +
        item.storey +
        " b" +
        item.bay;
      if (state.selectedKind === "opening" && state.selectedId === item.id) {
        li.classList.add("selected");
      }
      li.addEventListener("click", function () {
        selectItem("opening", item.id);
      });
      els.openingList.appendChild(li);
    });

    (gt.metric_anchors || []).forEach(function (anchor) {
      const li = document.createElement("li");
      li.innerHTML =
        '<span class="tag anchor">anchor</span>' +
        (anchor.id || "anchor") +
        (anchor.distance_mm ? " · " + anchor.distance_mm + "mm" : " · pending");
      if (state.selectedKind === "anchor") li.classList.add("selected");
      li.addEventListener("click", function () {
        selectItem("anchor", anchor.id);
      });
      els.openingList.appendChild(li);
    });
  }

  function drawRect(group, bbox, options) {
    const px = bboxToPx(bbox);
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", px.x);
    rect.setAttribute("y", px.y);
    rect.setAttribute("width", px.width);
    rect.setAttribute("height", px.height);
    rect.setAttribute("fill", options.fill);
    rect.setAttribute("stroke", options.stroke);
    rect.setAttribute("stroke-width", options.strokeWidth);
    rect.setAttribute("data-kind", options.kind);
    rect.setAttribute("data-id", options.id);
    if (options.dash) rect.setAttribute("stroke-dasharray", "6 4");
    rect.style.cursor = "move";
    group.appendChild(rect);

    if (options.selected) {
      ["nw", "ne", "sw", "se"].forEach(function (corner) {
        const handle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        const cx = corner.includes("e") ? px.x + px.width : px.x;
        const cy = corner.includes("s") ? px.y + px.height : px.y;
        handle.setAttribute("cx", cx);
        handle.setAttribute("cy", cy);
        handle.setAttribute("r", 5);
        handle.setAttribute("fill", "#eceff4");
        handle.setAttribute("stroke", "#2e3440");
        handle.setAttribute("data-handle", corner);
        handle.setAttribute("data-kind", options.kind);
        handle.setAttribute("data-id", options.id);
        handle.style.cursor = corner + "-resize";
        group.appendChild(handle);
      });
    }
  }

  function renderSvg() {
    const gt = currentGt();
    const svg = els.svg;
    svg.innerHTML = "";
    svg.setAttribute("viewBox", "0 0 " + state.stageSize.w + " " + state.stageSize.h);

    const layer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    svg.appendChild(layer);

    if (gt.facade_bbox) {
      drawRect(layer, gt.facade_bbox, {
        kind: "facade",
        id: "facade",
        fill: "rgba(240,180,41,0.08)",
        stroke: COLORS.facade,
        strokeWidth: 2,
        dash: true,
        selected: state.selectedKind === "facade",
      });
    }

    gt.openings.forEach(function (item) {
      const selected = state.selectedKind === "opening" && state.selectedId === item.id;
      drawRect(layer, item.bbox, {
        kind: "opening",
        id: item.id,
        fill: item.type === "door" ? "rgba(67,160,71,0.18)" : "rgba(74,144,226,0.18)",
        stroke: selected ? COLORS.selected : item.type === "door" ? COLORS.door : COLORS.window,
        strokeWidth: selected ? 3 : 2,
        selected: selected,
      });
    });

    (gt.metric_anchors || []).forEach(function (anchor) {
      if (!anchor.start || !anchor.end) return;
      const bbox = [
        Math.min(anchor.start[0], anchor.end[0]),
        Math.min(anchor.start[1], anchor.end[1]),
        Math.max(anchor.start[0], anchor.end[0]),
        Math.max(anchor.start[1], anchor.end[1]),
      ];
      const selected = state.selectedKind === "anchor";
      drawRect(layer, bbox, {
        kind: "anchor",
        id: anchor.id || "anchor",
        fill: "rgba(171,71,188,0.12)",
        stroke: COLORS.anchor,
        strokeWidth: selected ? 3 : 2,
        dash: true,
        selected: selected,
      });
    });

    if (state.drawing) {
      drawRect(layer, state.drawing.bbox, {
        kind: "draft",
        id: "draft",
        fill: "rgba(136,192,208,0.15)",
        stroke: COLORS.selected,
        strokeWidth: 2,
      });
    }
  }

  function renderPhotoMeta() {
    const photo = currentPhoto();
    els.photoMeta.textContent =
      photo.id +
      " · " +
      photo.category +
      " · " +
      photo.split +
      " · " +
      (photo.ground_truth.annotation_status || "draft");
  }

  function render() {
    renderPhotoMeta();
    renderOpeningList();
    renderSvg();
  }

  function resizeStage() {
    const img = els.image;
    state.stageSize.w = img.clientWidth;
    state.stageSize.h = img.clientHeight;
    renderSvg();
  }

  function getTarget(event) {
  const target = event.target;
    if (!target || !target.getAttribute) return null;
    return {
      kind: target.getAttribute("data-kind"),
      id: target.getAttribute("data-id"),
      handle: target.getAttribute("data-handle"),
    };
  }

  function getBboxRef(kind, id) {
    const gt = currentGt();
    if (kind === "facade") return gt.facade_bbox;
    if (kind === "opening") {
      const item = gt.openings.find(function (o) {
        return o.id === id;
      });
      return item ? item.bbox : null;
    }
    if (kind === "anchor") {
      const anchor = (gt.metric_anchors || [])[0];
      if (!anchor) return null;
      return [
        Math.min(anchor.start[0], anchor.end[0]),
        Math.min(anchor.start[1], anchor.end[1]),
        Math.max(anchor.start[0], anchor.end[0]),
        Math.max(anchor.start[1], anchor.end[1]),
      ];
    }
    return null;
  }

  function setBboxRef(kind, id, bbox) {
    const gt = currentGt();
    if (kind === "facade") {
      gt.facade_bbox = bbox;
      return;
    }
    if (kind === "opening") {
      const item = gt.openings.find(function (o) {
        return o.id === id;
      });
      if (item) item.bbox = bbox;
      return;
    }
    if (kind === "anchor") {
      const anchor = (gt.metric_anchors || [])[0];
      if (!anchor) return;
      anchor.start = [bbox[0], bbox[3]];
      anchor.end = [bbox[2], bbox[3]];
    }
  }

  function onPointerDown(event) {
    const rect = els.svg.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const target = getTarget(event);

    if (state.tool === "draw-window" || state.tool === "draw-door") {
      state.drawing = {
        type: state.tool === "draw-door" ? "door" : "window",
        start: [x, y],
        bbox: [x / state.stageSize.w, y / state.stageSize.h, x / state.stageSize.w, y / state.stageSize.h],
      };
      els.svg.setPointerCapture(event.pointerId);
      return;
    }

    if (target && target.kind && target.kind !== "draft") {
      selectItem(target.kind === "opening" ? "opening" : target.kind, target.id);
      const bbox = getBboxRef(target.kind, target.id);
      if (!bbox) return;
      state.drag = {
        kind: target.kind,
        id: target.id,
        handle: target.handle,
        startPx: [x, y],
        startBbox: bbox.slice(),
      };
      els.svg.setPointerCapture(event.pointerId);
      return;
    }

    if (state.tool === "select") {
      state.selectedId = null;
      syncFields();
      renderSvg();
    }
  }

  function onPointerMove(event) {
    const rect = els.svg.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    if (state.drawing) {
      const norm = pxToNorm(x, y);
      state.drawing.bbox = normalizeRect(
        state.drawing.start[0] / state.stageSize.w,
        state.drawing.start[1] / state.stageSize.h,
        norm[0],
        norm[1]
      );
      renderSvg();
      return;
    }

    if (!state.drag) return;
    const dx = (x - state.drag.startPx[0]) / state.stageSize.w;
    const dy = (y - state.drag.startPx[1]) / state.stageSize.h;
    const b = state.drag.startBbox.slice();

    if (state.drag.handle) {
      if (state.drag.handle.includes("w")) b[0] = clamp01(b[0] + dx);
      if (state.drag.handle.includes("e")) b[2] = clamp01(b[2] + dx);
      if (state.drag.handle.includes("n")) b[1] = clamp01(b[1] + dy);
      if (state.drag.handle.includes("s")) b[3] = clamp01(b[3] + dy);
    } else {
      b[0] = clamp01(b[0] + dx);
      b[2] = clamp01(b[2] + dx);
      b[1] = clamp01(b[1] + dy);
      b[3] = clamp01(b[3] + dy);
    }

    const bbox = normalizeRect(b[0], b[1], b[2], b[3]);
    setBboxRef(state.drag.kind, state.drag.id, bbox);
    els.fieldBbox.value = bbox.join(", ");
    renderSvg();
  }

  function onPointerUp(event) {
    if (state.drawing) {
      const bbox = state.drawing.bbox;
      if (bbox[2] - bbox[0] > 0.01 && bbox[3] - bbox[1] > 0.01) {
        const gt = currentGt();
        const type = state.drawing.type;
        const id = nextOpeningId(type);
        gt.openings.push({
          id: id,
          type: type,
          bbox: bbox,
          storey: 1,
          bay: 1,
        });
        selectItem("opening", id);
      }
      state.drawing = null;
      render();
    }
    state.drag = null;
    try {
      els.svg.releasePointerCapture(event.pointerId);
    } catch (err) {
      /* ignore */
    }
  }

  function setTool(tool) {
    state.tool = tool;
    document.querySelectorAll("[data-tool]").forEach(function (btn) {
      btn.classList.toggle("active", btn.getAttribute("data-tool") === tool);
    });
    setStatus("Tool: " + tool);
  }

  function exportPhotoJson(photo) {
    const gt = JSON.parse(JSON.stringify(photo.ground_truth));
    gt.review_rounds = (gt.review_rounds || 1) + 0;
    gt.annotation_status = "reviewed_v1";
    gt.reviewed_at = new Date().toISOString();
    return JSON.stringify(gt, null, 2) + "\n";
  }

  function downloadText(filename, text) {
    const blob = new Blob([text], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  function exportCurrent() {
    applyFields();
    const photo = currentPhoto();
    downloadText(photo.id + ".json", exportPhotoJson(photo));
    setStatus("Exported " + photo.id + ".json — save to review_pack/exports/");
  }

  function exportAll() {
    applyFields();
    state.pack.photos.forEach(function (photo) {
      downloadText(photo.id + ".json", exportPhotoJson(photo));
    });
    setStatus("Exported 5 JSON files — save to tests/reconstruction/review_pack/exports/");
  }

  function loadPhoto(index) {
    applyFields();
    state.photoIndex = index;
    const photo = currentPhoto();
    els.image.src = photo.image_rel;
    state.selectedId = null;
    state.selectedKind = "opening";
    render();
    setStatus("Loaded " + photo.id);
  }

  function init() {
    state.pack.photos.forEach(function (photo, index) {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = photo.id + " (" + photo.category + ")";
      els.photoSelect.appendChild(option);
    });

    els.photoSelect.addEventListener("change", function () {
      loadPhoto(parseInt(els.photoSelect.value, 10));
    });

    els.image.addEventListener("load", resizeStage);
    window.addEventListener("resize", resizeStage);

    els.svg.addEventListener("pointerdown", onPointerDown);
    els.svg.addEventListener("pointermove", onPointerMove);
    els.svg.addEventListener("pointerup", onPointerUp);
    els.svg.addEventListener("pointercancel", onPointerUp);

    document.querySelectorAll("[data-tool]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setTool(btn.getAttribute("data-tool"));
      });
    });

    document.getElementById("btn-add-window").addEventListener("click", function () {
      addOpening("window");
    });
    document.getElementById("btn-add-door").addEventListener("click", function () {
      addOpening("door");
    });
    document.getElementById("btn-add-anchor").addEventListener("click", ensureAnchor);
    document.getElementById("btn-delete").addEventListener("click", deleteSelected);
    document.getElementById("btn-apply").addEventListener("click", function () {
      applyFields();
      setStatus("Applied field edits");
    });
    document.getElementById("btn-export").addEventListener("click", exportCurrent);
    document.getElementById("btn-export-all").addEventListener("click", exportAll);
    document.getElementById("btn-select-facade").addEventListener("click", function () {
      selectItem("facade", "facade");
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Delete" || event.key === "Backspace") {
        if (document.activeElement && document.activeElement.tagName === "INPUT") return;
        deleteSelected();
      }
      if (event.key === "v" || event.key === "V") setTool("select");
      if (event.key === "w" || event.key === "W") setTool("draw-window");
      if (event.key === "d" || event.key === "D") setTool("draw-door");
    });

    loadPhoto(0);
    setTool("select");
  }

  init();
})();
