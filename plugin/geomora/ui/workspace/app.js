(function () {
  const REVIEW_WINDOW_LIMIT = 8;

  const state = {
    sourcePath: null,
    sourceId: null,
    windows: [],
    originalImageUrl: null,
    rectifiedImageUrl: null,
    rectification: null,
    detection: null,
    overlayImageUrl: null,
    activeView: 'original',
    selectedWindowIndex: null,
    selectedDoor: false,
    doorBbox: null,
    drawMode: false,
    drag: null
  };

  const els = {
    status: document.getElementById('status'),
    sourceMeta: document.getElementById('source-meta'),
    rectifyMeta: document.getElementById('rectify-meta'),
    detectMeta: document.getElementById('detect-meta'),
    imageStack: document.getElementById('image-stack'),
    image: document.getElementById('reference-image'),
    overlaySvg: document.getElementById('detection-overlay'),
    viewerToolbar: document.getElementById('viewer-toolbar'),
    btnDrawWindow: document.getElementById('btn-draw-window'),
    btnDeleteSelected: document.getElementById('btn-delete-selected'),
    viewerHint: document.getElementById('viewer-hint'),
    placeholder: document.getElementById('viewer-placeholder'),
    tree: document.getElementById('element-tree'),
    form: document.getElementById('facade-form'),
    windowsContainer: document.getElementById('windows-container'),
    btnViewOriginal: document.getElementById('btn-view-original'),
    btnViewRectified: document.getElementById('btn-view-rectified'),
    btnViewOverlay: document.getElementById('btn-view-overlay')
  };

  function sketchupCall(name, arg) {
    if (!window.sketchup || typeof window.sketchup[name] !== 'function') return;
    if (arg === undefined) {
      window.sketchup[name]();
    } else {
      window.sketchup[name](arg);
    }
  }

  function setStatus(level, message) {
    els.status.textContent = message;
    els.status.className = 'status ' + (level || '');
  }

  function clearSelection() {
    state.selectedWindowIndex = null;
    state.selectedDoor = false;
    updateSelectionUi();
  }

  function selectWindow(index) {
    state.selectedWindowIndex = index;
    state.selectedDoor = false;
    updateSelectionUi();
    const row = els.windowsContainer.querySelector('[data-win-row="' + index + '"]');
    if (row) {
      row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }

  function selectDoor() {
    state.selectedDoor = true;
    state.selectedWindowIndex = null;
    updateSelectionUi();
  }

  function updateSelectionUi() {
    els.windowsContainer.querySelectorAll('.window-row').forEach(function (row) {
      const index = parseInt(row.dataset.winRow, 10);
      row.classList.toggle('selected', state.selectedWindowIndex === index);
    });
    const hasSelection = state.selectedDoor || state.selectedWindowIndex !== null;
    els.btnDeleteSelected.disabled = !hasSelection;
    renderDetectionOverlay();
  }

  function removeWindowAt(index) {
    if (index < 0 || index >= state.windows.length) return;
    state.windows.splice(index, 1);
    if (state.selectedWindowIndex === index) {
      clearSelection();
    } else if (state.selectedWindowIndex !== null && state.selectedWindowIndex > index) {
      state.selectedWindowIndex -= 1;
    }
    renderWindows(state.windows);
    updateReviewStatus();
  }

  function removeSelectedDoor() {
    els.form.elements.namedItem('door_offset').value = 0;
    els.form.elements.namedItem('door_width').value = 0;
    els.form.elements.namedItem('door_height').value = 0;
    state.doorBbox = null;
    state.drag = null;
    setDrawMode(false);
    clearSelection();
    renderTree();
    updateReviewStatus();
  }

  function removeSelected() {
    if (state.selectedDoor) {
      removeSelectedDoor();
      return;
    }
    if (state.selectedWindowIndex !== null) {
      removeWindowAt(state.selectedWindowIndex);
    }
  }

  function updateReviewStatus() {
    if (state.windows.length > REVIEW_WINDOW_LIMIT) {
      setStatus(
        'error',
        'Still ' + state.windows.length + ' windows — click false boxes on the image and Delete.'
      );
    } else if (state.windows.length > 0) {
      setStatus('', 'Selection updated — Generate when the image looks correct.');
    }
  }

  function overlayEditable() {
    return (
      (state.activeView === 'rectified' || state.activeView === 'overlay') &&
      state.rectifiedImageUrl
    );
  }

  function imageDimensions() {
    return {
      width: els.image.naturalWidth || 1,
      height: els.image.naturalHeight || 1
    };
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function bboxNormFromPixels(x1, y1, x2, y2) {
    const dims = imageDimensions();
    const left = clamp(Math.min(x1, x2), 0, dims.width);
    const top = clamp(Math.min(y1, y2), 0, dims.height);
    const right = clamp(Math.max(x1, x2), 0, dims.width);
    const bottom = clamp(Math.max(y1, y2), 0, dims.height);
    return [
      left / dims.width,
      top / dims.height,
      right / dims.width,
      bottom / dims.height
    ];
  }

  function bboxPixelsFromNorm(bbox) {
    const dims = imageDimensions();
    return {
      x: bbox[0] * dims.width,
      y: bbox[1] * dims.height,
      w: (bbox[2] - bbox[0]) * dims.width,
      h: (bbox[3] - bbox[1]) * dims.height
    };
  }

  function bboxNormToWindow(bbox) {
    const wallLength = Number(els.form.elements.namedItem('wall_length').value) || 10000;
    const wallHeight = Number(els.form.elements.namedItem('wall_height').value) || 3300;
    const x1 = bbox[0];
    const y1 = bbox[1];
    const x2 = bbox[2];
    const y2 = bbox[3];
    return {
      offset: Math.round(x1 * wallLength * 10) / 10,
      width: Math.round((x2 - x1) * wallLength * 10) / 10,
      height: Math.round((y2 - y1) * wallHeight * 10) / 10,
      sill_height: Math.round((1 - y2) * wallHeight * 10) / 10,
      bbox_norm: bbox.slice()
    };
  }

  function bboxNormToDoor(bbox) {
    const wallLength = Number(els.form.elements.namedItem('wall_length').value) || 10000;
    const wallHeight = Number(els.form.elements.namedItem('wall_height').value) || 3300;
    const x1 = bbox[0];
    const y1 = bbox[1];
    const x2 = bbox[2];
    const y2 = bbox[3];
    return {
      offset: Math.round(x1 * wallLength * 10) / 10,
      width: Math.round((x2 - x1) * wallLength * 10) / 10,
      height: Math.round((y2 - y1) * wallHeight * 10) / 10
    };
  }

  function applyBboxToWindow(index, bboxNorm) {
    const mapped = bboxNormToWindow(bboxNorm);
    state.windows[index] = Object.assign({}, state.windows[index], mapped);
    syncWindowRowFromState(index);
    renderDetectionOverlay();
    renderTree();
  }

  function applyBboxToDoor(bboxNorm) {
    const mapped = bboxNormToDoor(bboxNorm);
    els.form.elements.namedItem('door_offset').value = mapped.offset;
    els.form.elements.namedItem('door_width').value = mapped.width;
    els.form.elements.namedItem('door_height').value = mapped.height;
    state.doorBbox = bboxNorm.slice();
    renderDetectionOverlay();
    renderTree();
  }

  function syncWindowRowFromState(index) {
    const win = state.windows[index];
    const row = els.windowsContainer.querySelector('[data-win-row="' + index + '"]');
    if (!row || !win) {
      renderWindows(state.windows);
      return;
    }
    row.querySelector('[data-field="offset"]').value = win.offset;
    row.querySelector('[data-field="width"]').value = win.width;
    row.querySelector('[data-field="height"]').value = win.height;
    row.querySelector('[data-field="sill_height"]').value = win.sill_height;
  }

  function addWindowFromBboxNorm(bboxNorm) {
    const win = bboxNormToWindow(bboxNorm);
    state.windows.push(win);
    renderWindows(state.windows);
    selectWindow(state.windows.length - 1);
    updateReviewStatus();
  }

  function setDrawMode(enabled) {
    state.drawMode = enabled;
    els.btnDrawWindow.classList.toggle('active', enabled);
    els.imageStack.classList.toggle('draw-mode', enabled);
    updateViewerHint();
  }

  function svgPointFromEvent(event) {
    const pt = els.overlaySvg.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;
    const matrix = els.overlaySvg.getScreenCTM();
    if (!matrix) {
      return { x: 0, y: 0 };
    }
    const transformed = pt.matrixTransform(matrix.inverse());
    return { x: transformed.x, y: transformed.y };
  }

  function minBoxPixels() {
    const dims = imageDimensions();
    return {
      width: dims.width * 0.02,
      height: dims.height * 0.02
    };
  }

  function interactiveOverlayEnabled() {
    return overlayEditable();
  }

  function renderHandleMarkup(x, y, w, h, kind, index) {
    const corners = [
      ['nw', x, y],
      ['ne', x + w, y],
      ['se', x + w, y + h],
      ['sw', x, y + h]
    ];
    let markup = '';
    corners.forEach(function (corner) {
      markup +=
        '<circle class="det-handle" data-kind="' + kind + '" data-index="' + index +
        '" data-handle="' + corner[0] + '" cx="' + corner[1] + '" cy="' + corner[2] + '" r="7" />';
    });
    return markup;
  }

  function renderDetectionOverlay() {
    const svg = els.overlaySvg;
    if (!overlayEditable() || !els.image.complete || !els.image.naturalWidth) {
      svg.innerHTML = '';
      return;
    }

    const dims = imageDimensions();
    const nw = dims.width;
    const nh = dims.height;
    svg.setAttribute('viewBox', '0 0 ' + nw + ' ' + nh);

    let markup = '';
    state.windows.forEach(function (win, index) {
      if (!win.bbox_norm || win.bbox_norm.length !== 4) return;
      const box = bboxPixelsFromNorm(win.bbox_norm);
      const selected = state.selectedWindowIndex === index && !state.selectedDoor;
      markup +=
        '<rect class="det-box' + (selected ? ' selected' : '') + '" data-kind="window" data-index="' + index +
        '" x="' + box.x + '" y="' + box.y + '" width="' + box.w + '" height="' + box.h + '" />' +
        '<text class="det-label" x="' + (box.x + 4) + '" y="' + (box.y + 16) + '">' + (index + 1) + '</text>';
      if (selected && !state.drawMode) {
        markup += renderHandleMarkup(box.x, box.y, box.w, box.h, 'window', index);
      }
    });

    const doorWidth = Number(els.form.elements.namedItem('door_width').value) || 0;
    if (state.doorBbox && state.doorBbox.length === 4 && doorWidth > 0) {
      const box = bboxPixelsFromNorm(state.doorBbox);
      const selected = state.selectedDoor;
      markup +=
        '<rect class="det-box door' + (selected ? ' selected' : '') + '" data-kind="door" data-index="-1" x="' +
        box.x + '" y="' + box.y + '" width="' + box.w + '" height="' + box.h + '" />' +
        '<text class="det-label" x="' + (box.x + 4) + '" y="' + (box.y + 16) + '">D</text>';
      if (selected && !state.drawMode) {
        markup += renderHandleMarkup(box.x, box.y, box.w, box.h, 'door', -1);
      }
    }

    if (state.drag && state.drag.preview) {
      const p = state.drag.preview;
      markup +=
        '<rect class="det-preview" x="' + p.x + '" y="' + p.y + '" width="' + p.w + '" height="' + p.h + '" />';
    }

    svg.innerHTML = markup;
  }

  function onOverlayMouseDown(event) {
    if (!overlayEditable() || state.drag) return;
    const target = event.target;
    if (target.classList.contains('det-handle')) {
      event.preventDefault();
      startResizeDrag(event, target);
      return;
    }
    if (target.classList.contains('det-box')) {
      event.preventDefault();
      const kind = target.getAttribute('data-kind');
      const index = parseInt(target.getAttribute('data-index'), 10);
      if (kind === 'door') {
        selectDoor();
        if (!state.drawMode) {
          startMoveDrag(event, true, -1);
        }
      } else if (!Number.isNaN(index)) {
        selectWindow(index);
        if (!state.drawMode) {
          startMoveDrag(event, false, index);
        }
      }
      return;
    }
    if (state.drawMode && (target === els.overlaySvg || target.classList.contains('det-preview'))) {
      event.preventDefault();
      startDrawDrag(event);
    }
  }

  function startDrawDrag(event) {
    const pt = svgPointFromEvent(event);
    state.drag = {
      mode: 'draw',
      startX: pt.x,
      startY: pt.y,
      preview: { x: pt.x, y: pt.y, w: 0, h: 0 }
    };
    renderDetectionOverlay();
  }

  function startMoveDrag(event, isDoor, index) {
    const bbox = isDoor ? state.doorBbox : state.windows[index].bbox_norm;
    if (!bbox) return;
    const box = bboxPixelsFromNorm(bbox);
    const pt = svgPointFromEvent(event);
    state.drag = {
      mode: 'move',
      isDoor: isDoor,
      index: index,
      startX: pt.x,
      startY: pt.y,
      orig: { x: box.x, y: box.y, w: box.w, h: box.h }
    };
  }

  function startResizeDrag(event, target) {
    const kind = target.getAttribute('data-kind');
    const index = parseInt(target.getAttribute('data-index'), 10);
    const handle = target.getAttribute('data-handle');
    const isDoor = kind === 'door';
    const bbox = isDoor ? state.doorBbox : state.windows[index].bbox_norm;
    if (!bbox) return;
    const box = bboxPixelsFromNorm(bbox);
    const pt = svgPointFromEvent(event);
    state.drag = {
      mode: 'resize',
      isDoor: isDoor,
      index: index,
      handle: handle,
      startX: pt.x,
      startY: pt.y,
      orig: { x: box.x, y: box.y, w: box.w, h: box.h }
    };
  }

  function onOverlayMouseMove(event) {
    if (!state.drag) return;
    const pt = svgPointFromEvent(event);
    const dims = imageDimensions();
    const min = minBoxPixels();
    const drag = state.drag;

    if (drag.mode === 'draw') {
      const x = Math.min(drag.startX, pt.x);
      const y = Math.min(drag.startY, pt.y);
      const w = Math.abs(pt.x - drag.startX);
      const h = Math.abs(pt.y - drag.startY);
      drag.preview = { x: x, y: y, w: w, h: h };
      renderDetectionOverlay();
      return;
    }

    const orig = drag.orig;
    let x = orig.x;
    let y = orig.y;
    let w = orig.w;
    let h = orig.h;

    if (drag.mode === 'move') {
      const dx = pt.x - drag.startX;
      const dy = pt.y - drag.startY;
      x = clamp(orig.x + dx, 0, dims.width - orig.w);
      y = clamp(orig.y + dy, 0, dims.height - orig.h);
    } else if (drag.mode === 'resize') {
      const right = orig.x + orig.w;
      const bottom = orig.y + orig.h;
      let left = orig.x;
      let top = orig.y;
      let rightEdge = right;
      let bottomEdge = bottom;
      if (drag.handle.indexOf('w') >= 0) left = clamp(pt.x, 0, right - min.width);
      if (drag.handle.indexOf('e') >= 0) rightEdge = clamp(pt.x, left + min.width, dims.width);
      if (drag.handle.indexOf('n') >= 0) top = clamp(pt.y, 0, bottom - min.height);
      if (drag.handle.indexOf('s') >= 0) bottomEdge = clamp(pt.y, top + min.height, dims.height);
      x = left;
      y = top;
      w = rightEdge - left;
      h = bottomEdge - top;
    }

    drag.preview = { x: x, y: y, w: w, h: h };
    renderDetectionOverlay();
  }

  function onOverlayMouseUp(event) {
    if (!state.drag) return;
    const drag = state.drag;
    state.drag = null;

    if (!drag.preview || drag.preview.w < minBoxPixels().width || drag.preview.h < minBoxPixels().height) {
      renderDetectionOverlay();
      return;
    }

    const bboxNorm = bboxNormFromPixels(
      drag.preview.x,
      drag.preview.y,
      drag.preview.x + drag.preview.w,
      drag.preview.y + drag.preview.h
    );

    if (drag.mode === 'draw') {
      addWindowFromBboxNorm(bboxNorm);
      setDrawMode(false);
      return;
    }

    if (drag.isDoor) {
      applyBboxToDoor(bboxNorm);
    } else {
      applyBboxToWindow(drag.index, bboxNorm);
    }
    updateReviewStatus();
  }

  function updateViewerHint() {
    if (!overlayEditable()) return;
    if (state.drawMode) {
      els.viewerHint.textContent = 'Drag on image to draw a window · Esc to cancel';
    } else {
      els.viewerHint.textContent =
        'Click to select · drag box to move · drag corners to resize · Draw window to add';
    }
  }

  function updateViewerToolbar() {
    const enabled = overlayEditable();
    els.viewerToolbar.hidden = !enabled;
    if (enabled) {
      updateViewerHint();
    }
  }

  function renderWindows(windows) {
    state.windows = windows || [];
    els.windowsContainer.innerHTML = '';

    state.windows.forEach(function (win, index) {
      const row = document.createElement('div');
      row.className = 'window-row';
      row.dataset.winRow = String(index);
      if (state.selectedWindowIndex === index) {
        row.classList.add('selected');
      }
      row.innerHTML =
        '<div class="window-row-header">' +
        '<h3>Window ' + (index + 1) + '</h3>' +
        '<button type="button" class="btn-link" data-remove-win="' + index + '">Remove</button>' +
        '</div>' +
        '<label>Offset (mm)<input data-win="' + index + '" data-field="offset" type="number" step="1" value="' + win.offset + '"></label>' +
        '<label>Width (mm)<input data-win="' + index + '" data-field="width" type="number" step="1" value="' + win.width + '"></label>' +
        '<label>Height (mm)<input data-win="' + index + '" data-field="height" type="number" step="1" value="' + win.height + '"></label>' +
        '<label>Sill height (mm)<input data-win="' + index + '" data-field="sill_height" type="number" step="1" value="' + win.sill_height + '"></label>';
      els.windowsContainer.appendChild(row);
    });

    els.windowsContainer.querySelectorAll('input').forEach(function (input) {
      input.addEventListener('change', onWindowFieldChange);
    });

    els.windowsContainer.querySelectorAll('[data-remove-win]').forEach(function (button) {
      button.addEventListener('click', onRemoveWindow);
    });

    els.windowsContainer.querySelectorAll('.window-row-header h3').forEach(function (heading) {
      heading.addEventListener('click', function () {
        const row = heading.closest('.window-row');
        if (!row) return;
        selectWindow(parseInt(row.dataset.winRow, 10));
      });
    });

    renderTree();
    renderDetectionOverlay();
    updateViewerToolbar();
  }

  function onRemoveWindow(event) {
    event.stopPropagation();
    const index = parseInt(event.target.dataset.removeWin, 10);
    if (Number.isNaN(index)) return;
    removeWindowAt(index);
  }

  function onWindowFieldChange(event) {
    const input = event.target;
    const index = parseInt(input.dataset.win, 10);
    const field = input.dataset.field;
    state.windows[index][field] = parseFloat(input.value);
    renderTree();
  }

  function renderTree() {
    const params = collectParams();
    const items = [
      'Project: ' + params.project_name,
      'Wall: ' + params.wall_length + ' × ' + params.wall_height + ' × ' + params.wall_thickness + ' mm',
      'Windows: ' + params.windows.length,
      'Door: ' + params.door.width + ' × ' + params.door.height + ' mm @ ' + params.door.offset
    ];

    if (state.detection) {
      items.push(
        'Detection: ' + state.detection.method +
        ' (' + state.detection.element_count + ' elements, confidence ' + state.detection.confidence + ')'
      );
    }

    if (state.rectification) {
      items.push(
        'Rectified: ' + state.rectification.method +
        ' (confidence ' + state.rectification.confidence + ')'
      );
    }

    params.windows.forEach(function (win, index) {
      items.push(
        'Window ' + (index + 1) + ': ' + win.width + '×' + win.height +
        ' @ offset ' + win.offset + ', sill ' + win.sill_height
      );
    });

    els.tree.innerHTML = items.map(function (item) {
      return '<li>' + item + '</li>';
    }).join('');
  }

  function collectParams() {
    const formData = new FormData(els.form);
    const windows = state.windows.map(function (win) {
      return {
        offset: Number(win.offset),
        width: Number(win.width),
        height: Number(win.height),
        sill_height: Number(win.sill_height)
      };
    });

    return {
      project_name: formData.get('project_name'),
      wall_length: Number(formData.get('wall_length')),
      wall_height: Number(formData.get('wall_height')),
      wall_thickness: Number(formData.get('wall_thickness')),
      windows: windows,
      door: {
        offset: Number(formData.get('door_offset')),
        width: Number(formData.get('door_width')),
        height: Number(formData.get('door_height'))
      },
      source_path: state.sourcePath,
      source_id: state.sourceId
    };
  }

  function updateViewer() {
    let url = null;
    if (state.activeView === 'rectified' || state.activeView === 'overlay') {
      url = state.rectifiedImageUrl;
    } else {
      url = state.originalImageUrl;
    }

    if (!url) {
      els.imageStack.hidden = true;
      els.viewerToolbar.hidden = true;
      els.placeholder.hidden = false;
      els.overlaySvg.innerHTML = '';
      if (state.activeView === 'overlay') {
        els.placeholder.textContent = 'Rectify then use Overlay to edit boxes on image';
      } else if (state.activeView === 'rectified') {
        els.placeholder.textContent = 'Run Rectify Facade to see corrected image';
      } else {
        els.placeholder.textContent = 'Load a facade photo for manual reference';
      }
      return;
    }

    els.imageStack.hidden = false;
    els.placeholder.hidden = true;
    if (els.image.getAttribute('src') !== url) {
      els.image.src = url;
    }
    updateViewerToolbar();
    if (els.image.complete) {
      renderDetectionOverlay();
    }
  }

  function setActiveView(view) {
    state.activeView = view;
    els.btnViewOriginal.classList.toggle('active', view === 'original');
    els.btnViewRectified.classList.toggle('active', view === 'rectified');
    els.btnViewOverlay.classList.toggle('active', view === 'overlay');
    updateViewer();
  }

  function loadPayload(payload, mode) {
    els.form.elements.namedItem('project_name').value = payload.project_name || 'Untitled Facade';
    els.form.elements.namedItem('wall_length').value = payload.wall_length || 10000;
    els.form.elements.namedItem('wall_height').value = payload.wall_height || 3300;
    els.form.elements.namedItem('wall_thickness').value = payload.wall_thickness || 240;

    renderWindows(payload.windows || []);

    const door = payload.door || {};
    els.form.elements.namedItem('door_offset').value = door.offset || 0;
    els.form.elements.namedItem('door_width').value = door.width || 0;
    els.form.elements.namedItem('door_height').value = door.height || 2100;

    state.detection = null;
    state.overlayImageUrl = null;
    state.doorBbox = null;
    state.drag = null;
    setDrawMode(false);
    clearSelection();
    els.detectMeta.textContent = 'Detection: not run';

    if (payload.source_path) {
      setImage('file:///' + payload.source_path.replace(/\\/g, '/'), payload.source_path);
    }

    if (payload.ir_preview) {
      setIrPreview(payload.ir_preview);
    }

    renderTree();
    if (mode === 'template') {
      setStatus('', 'Phase 0 template loaded — for testing only');
    } else {
      setStatus('', 'Ready — load a photo to begin');
    }
  }

  function setImage(fileUrl, sourcePath) {
    state.sourcePath = sourcePath;
    state.sourceId = sourcePath ? 'photo_001' : null;
    state.originalImageUrl = fileUrl;
    state.rectifiedImageUrl = null;
    state.rectification = null;
    state.detection = null;
    state.overlayImageUrl = null;
    state.doorBbox = null;
    state.drag = null;
    setDrawMode(false);
    clearSelection();
    els.sourceMeta.textContent = sourcePath || 'Image loaded';
    els.rectifyMeta.textContent = 'Rectification: not run';
    els.detectMeta.textContent = 'Detection: not run';
    renderWindows([]);
    els.form.elements.namedItem('door_offset').value = 0;
    els.form.elements.namedItem('door_width').value = 0;
    els.form.elements.namedItem('project_name').value = 'Untitled Facade';
    setActiveView('original');
    renderTree();
    setStatus('', 'Photo loaded — run Rectify Facade, then Detect or edit manually');
  }

  function setRectifiedImage(fileUrl, result) {
    state.rectifiedImageUrl = fileUrl;
    state.rectification = result;
    els.rectifyMeta.textContent =
      'Rectification: ' + result.method + ' | confidence ' + result.confidence +
      ' | lines ' + result.line_count;
    setActiveView('rectified');
    renderTree();
  }

  function setDetectionMeta(detection, overlayUrl) {
    state.detection = detection || null;
    state.overlayImageUrl = overlayUrl || null;
    if (state.detection) {
      els.detectMeta.textContent =
        'Detection: ' + state.detection.method +
        ' | ' + state.detection.windows + ' windows, ' + state.detection.doors + ' doors' +
        ' | confidence ' + state.detection.confidence;
    }
    if (overlayUrl) {
      setActiveView('overlay');
    }
    renderTree();
  }

  function applyDetection(payload, overlayUrl) {
    const windows = (payload.windows || []).map(function (win) {
      return {
        offset: Number(win.offset),
        width: Number(win.width),
        height: Number(win.height),
        sill_height: Number(win.sill_height),
        bbox_norm: win.bbox_norm
      };
    });
    clearSelection();
    renderWindows(windows);

    const door = payload.door || {};
    const doorWidth = Number(door.width) || 0;
    els.form.elements.namedItem('door_offset').value = door.offset || 0;
    els.form.elements.namedItem('door_width').value = doorWidth;
    els.form.elements.namedItem('door_height').value = doorWidth > 0 ? (door.height || 2100) : 0;
    state.doorBbox = door.bbox_norm && doorWidth > 0 ? door.bbox_norm : null;

    state.detection = payload.detection || null;
    state.overlayImageUrl = overlayUrl || null;
    if (state.detection) {
      els.detectMeta.textContent =
        'Detection: ' + state.detection.method +
        ' | ' + state.detection.windows + ' windows, ' + state.detection.doors + ' doors' +
        ' | confidence ' + state.detection.confidence;
    }

    setActiveView('overlay');
    setDrawMode(false);
    renderTree();

    const doorCount = state.detection ? state.detection.doors : 0;
    if (windows.length > REVIEW_WINDOW_LIMIT || payload.review_required) {
      setStatus(
        'error',
        'Detected ' + windows.length + ' windows — click false boxes on the image and Delete.'
      );
    } else if (doorCount === 0) {
      setStatus('success', 'No door detected — click boxes on image to review, then Generate.');
    } else {
      setStatus('success', 'Click boxes on image to review, then Generate.');
    }
  }

  function setIrPreview(ir) {
    if (!ir || !ir.openings) return;
    renderTree();
  }

  window.geomora = {
    loadPayload: loadPayload,
    setImage: setImage,
    setRectifiedImage: setRectifiedImage,
    applyDetection: applyDetection,
    setDetectionMeta: setDetectionMeta,
    setIrPreview: setIrPreview,
    setStatus: setStatus
  };

  document.getElementById('btn-pick-image').addEventListener('click', function () {
    sketchupCall('pick_image');
  });

  document.getElementById('btn-rectify').addEventListener('click', function () {
    sketchupCall('rectify', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-detect').addEventListener('click', function () {
    sketchupCall('detect', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-load-template').addEventListener('click', function () {
    sketchupCall('load_template');
  });

  document.getElementById('btn-validate').addEventListener('click', function () {
    sketchupCall('validate', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-generate').addEventListener('click', function () {
    if (state.windows.length > REVIEW_WINDOW_LIMIT) {
      setStatus(
        'error',
        'Too many windows (' + state.windows.length + '). Delete false boxes on the image, then Generate.'
      );
      return;
    }
    sketchupCall('generate', JSON.stringify(collectParams()));
  });

  els.btnDeleteSelected.addEventListener('click', function () {
    removeSelected();
  });

  els.btnDrawWindow.addEventListener('click', function () {
    setDrawMode(!state.drawMode);
  });

  els.overlaySvg.addEventListener('mousedown', onOverlayMouseDown);
  document.addEventListener('mousemove', onOverlayMouseMove);
  document.addEventListener('mouseup', onOverlayMouseUp);

  els.image.addEventListener('load', function () {
    renderDetectionOverlay();
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      if (state.drawMode) {
        setDrawMode(false);
        state.drag = null;
        renderDetectionOverlay();
        event.preventDefault();
        return;
      }
    }
    if (event.key !== 'Delete' && event.key !== 'Backspace') return;
    const tag = (event.target && event.target.tagName) || '';
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    if (!overlayEditable()) return;
    if (state.selectedDoor || state.selectedWindowIndex !== null) {
      event.preventDefault();
      removeSelected();
    }
  });

  els.btnViewOriginal.addEventListener('click', function () {
    setActiveView('original');
  });

  els.btnViewRectified.addEventListener('click', function () {
    setActiveView('rectified');
  });

  document.getElementById('btn-view-overlay').addEventListener('click', function () {
    setActiveView('overlay');
  });

  els.form.addEventListener('change', renderTree);

  document.addEventListener('DOMContentLoaded', function () {
    sketchupCall('ready');
  });
})();
