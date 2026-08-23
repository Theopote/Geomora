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
    drag: null,
    corners: null,
    originalImageSize: null,
    cornerDrag: null,
    rationalization: null,
    pattern: null,
    secondarySourcePath: null,
    secondarySourceId: null,
    secondaryImageUrl: null,
    multiview: null,
    fusion: null,
    doorConfidence: null,
    constraintSolution: null,
    reconstructionReview: null,
    understanding: null,
    selectedUncertaintyIndex: null,
    uncertaintyDecisions: {},
    activeStoreyIndex: 0,
    storeyWindows: [[]]
  };

  const els = {
    status: document.getElementById('status'),
    sourceMeta: document.getElementById('source-meta'),
    secondaryMeta: document.getElementById('secondary-meta'),
    multiviewMeta: document.getElementById('multiview-meta'),
    rectifyMeta: document.getElementById('rectify-meta'),
    detectMeta: document.getElementById('detect-meta'),
    reconstructionReview: document.getElementById('reconstruction-review'),
    reconstructionReviewDetail: document.getElementById('reconstruction-review-detail'),
    imageStack: document.getElementById('image-stack'),
    image: document.getElementById('reference-image'),
    overlaySvg: document.getElementById('detection-overlay'),
    cornerSvg: document.getElementById('corner-overlay'),
    showAiGuides: document.getElementById('show-ai-guides'),
    uncertaintyReview: document.getElementById('uncertainty-review'),
    uncertaintyReviewLabel: document.getElementById('uncertainty-review-label'),
    openingEvidence: document.getElementById('opening-evidence'),
    cornerGuide: document.getElementById('corner-guide'),
    viewerToolbar: document.getElementById('viewer-toolbar'),
    btnDrawWindow: document.getElementById('btn-draw-window'),
    btnDeleteSelected: document.getElementById('btn-delete-selected'),
    viewerHint: document.getElementById('viewer-hint'),
    placeholder: document.getElementById('viewer-placeholder'),
    tree: document.getElementById('element-tree'),
    treeSummary: document.getElementById('tree-summary'),
    treeReviewOnly: document.getElementById('tree-review-only'),
    form: document.getElementById('facade-form'),
    windowsContainer: document.getElementById('windows-container'),
    btnViewOriginal: document.getElementById('btn-view-original'),
    btnViewRectified: document.getElementById('btn-view-rectified'),
    btnViewOverlay: document.getElementById('btn-view-overlay'),
    detectMethod: document.getElementById('detect-method'),
    yoloSplit: document.getElementById('yolo-split'),
    btnExportYoloLabels: document.getElementById('btn-export-yolo-labels'),
    registerMethod: document.getElementById('register-method'),
    depthMethod: document.getElementById('depth-method'),
    storeyWindowBar: document.getElementById('storey-window-bar')
  };

  function cloneWindows(windows) {
    return (windows || []).map(function (win) {
      return Object.assign({}, win);
    });
  }

  function getStoreyCount() {
    const el = els.form.elements.namedItem('storey_count');
    const count = Number(el && el.value) || 1;
    return count < 1 ? 1 : count;
  }

  function isRepeatOpenings() {
    const el = els.form.elements.namedItem('repeat_openings');
    return el && el.checked;
  }

  function storeyLabel(index) {
    return index === 0 ? 'Ground' : 'Floor ' + (index + 1);
  }

  function persistActiveStoreyWindows() {
    state.storeyWindows[state.activeStoreyIndex] = cloneWindows(state.windows);
  }

  function syncStoreyWindowsLength() {
    const count = getStoreyCount();
    while (state.storeyWindows.length < count) {
      const seed = cloneWindows(state.storeyWindows[0] || []);
      state.storeyWindows.push(seed);
    }
    if (state.storeyWindows.length > count) {
      state.storeyWindows.length = count;
    }
    if (state.activeStoreyIndex >= count) {
      state.activeStoreyIndex = count - 1;
    }
  }

  function copyGroundWindowsToUpperStoreys() {
    const ground = cloneWindows(state.storeyWindows[0] || []);
    const count = getStoreyCount();
    for (let i = 1; i < count; i++) {
      state.storeyWindows[i] = cloneWindows(ground);
    }
  }

  function setActiveStorey(index) {
    if (isRepeatOpenings() && index > 0) {
      return;
    }
    persistActiveStoreyWindows();
    state.activeStoreyIndex = index;
    state.windows = cloneWindows(state.storeyWindows[index] || []);
    clearSelection();
    renderStoreySelector();
    renderWindows(state.windows);
  }

  function renderStoreySelector() {
    const bar = els.storeyWindowBar;
    if (!bar) return;

    const count = getStoreyCount();
    const repeat = isRepeatOpenings();
    bar.innerHTML = '';

    if (count <= 1) {
      bar.hidden = true;
      return;
    }

    bar.hidden = false;

    const title = document.createElement('div');
    title.className = 'storey-bar-title';
    title.textContent = repeat
      ? 'Upper floors repeat ground-floor windows'
      : 'Edit windows per floor';
    bar.appendChild(title);

    const tabs = document.createElement('div');
    tabs.className = 'storey-tabs';
    for (let i = 0; i < count; i++) {
      const wins = state.storeyWindows[i] || [];
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn secondary storey-tab';
      if (state.activeStoreyIndex === i) {
        btn.classList.add('active');
      }
      btn.textContent = storeyLabel(i) + ' (' + wins.length + ')';
      btn.disabled = repeat && i > 0;
      btn.addEventListener('click', function () {
        setActiveStorey(i);
      });
      tabs.appendChild(btn);
    }
    bar.appendChild(tabs);

    if (!repeat && count > 1) {
      const actions = document.createElement('div');
      actions.className = 'storey-bar-actions';
      const copyBtn = document.createElement('button');
      copyBtn.type = 'button';
      copyBtn.className = 'btn-link';
      copyBtn.textContent = 'Copy ground to all floors';
      copyBtn.addEventListener('click', function () {
        persistActiveStoreyWindows();
        copyGroundWindowsToUpperStoreys();
        state.windows = cloneWindows(state.storeyWindows[state.activeStoreyIndex] || []);
        renderStoreySelector();
        renderWindows(state.windows);
        setStatus('', 'Copied ground-floor windows to all upper floors.');
      });
      actions.appendChild(copyBtn);
      bar.appendChild(actions);
    }
  }

  function initStoreyWindowsFromPayload(payload) {
    if (payload.storey_windows && payload.storey_windows.length) {
      state.storeyWindows = payload.storey_windows.map(cloneWindows);
    } else {
      state.storeyWindows = [cloneWindows(payload.windows || [])];
    }
    syncStoreyWindowsLength();
    state.activeStoreyIndex = 0;
    state.windows = cloneWindows(state.storeyWindows[0] || []);
  }

  function summarizeStoreyWindows() {
    persistActiveStoreyWindows();
    const count = getStoreyCount();
    if (count <= 1) {
      return String((state.storeyWindows[0] || []).length);
    }
    return state.storeyWindows
      .map(function (wins, index) {
        return storeyLabel(index) + ':' + (wins || []).length;
      })
      .join(', ');
  }

  function onRepeatOpeningsChange() {
    persistActiveStoreyWindows();
    if (isRepeatOpenings()) {
      copyGroundWindowsToUpperStoreys();
      setActiveStorey(0);
    } else {
      renderStoreySelector();
    }
  }

  function onStoreyCountChange() {
    persistActiveStoreyWindows();
    syncStoreyWindowsLength();
    if (isRepeatOpenings()) {
      copyGroundWindowsToUpperStoreys();
    }
    state.windows = cloneWindows(state.storeyWindows[state.activeStoreyIndex] || []);
    renderStoreySelector();
    renderWindows(state.windows);
  }

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

  function setWorkflowStage(stage) {
    document.querySelectorAll('.workflow-steps li').forEach(function (step, index) {
      step.classList.toggle('active', index === stage);
      step.classList.toggle('complete', index < stage);
    });
  }

  function enhanceInspector() {
    const form = els.form;
    const filter = document.getElementById('inspector-filter');
    if (!form || !filter || form.dataset.grouped === 'true') return;
    const friendlyNames = {
      'Building Elements (Phase 7)': 'Building shell',
      'Multi-Storey (Phase 9)': 'Floors and structure',
      'LOD (Phase 10)': 'Model detail (LOD)',
      'Interior Layout (Phase 11)': 'Interior layout',
      'Interior Rooms (Phase 12)': 'Rooms',
      'Layout Refinement (Phase 13)': 'Layout refinement',
      'Fixtures + Overrides (Phase 14)': 'Fixtures and overrides',
      'Catalog + Layouts (Phase 15)': 'Catalog and layouts',
      'Presentation + Layout (Phase 16)': 'Presentation',
      'Layout Editor (Phase 17–3)': 'Layout editor',
      'Geometry Doctor (Phase 8)': 'Geometry repair',
      'Windows': 'Windows',
      'Door': 'Door'
    };
    const titles = Array.from(form.children).filter(function (child) {
      return child.classList && child.classList.contains('section-title');
    });
    titles.forEach(function (title) {
      const rawName = title.textContent.trim();
      const group = document.createElement('details');
      group.className = 'inspector-group';
      group.open = rawName === 'Windows' || rawName === 'Door';
      const summary = document.createElement('summary');
      summary.textContent = friendlyNames[rawName] || rawName.replace(/\s*\(Phase[^)]*\)/, '');
      group.appendChild(summary);
      form.insertBefore(group, title);
      let next = title.nextSibling;
      title.remove();
      while (next && !(next.classList && next.classList.contains('section-title'))) {
        const current = next;
        next = next.nextSibling;
        group.appendChild(current);
      }
      group.dataset.searchText = group.textContent.toLowerCase();
    });
    form.dataset.grouped = 'true';
    filter.addEventListener('input', function () {
      const query = filter.value.trim().toLowerCase();
      form.querySelectorAll('.inspector-group').forEach(function (group) {
        const matches = !query || group.dataset.searchText.indexOf(query) >= 0;
        group.hidden = !matches;
        if (query && matches) group.open = true;
      });
      Array.from(form.children).forEach(function (child) {
        if (child.tagName !== 'LABEL') return;
        child.hidden = !!query && child.textContent.toLowerCase().indexOf(query) < 0;
      });
    });
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
    renderOpeningEvidence();
    els.btnDeleteSelected.disabled = !hasSelection;
    renderDetectionOverlay();
  }

  function renderOpeningEvidence() {
    if (!els.openingEvidence) return;
    const index = state.selectedWindowIndex;
    const selected = state.selectedDoor ? { confidence: state.doorConfidence } :
      (index == null ? null : state.windows[index]);
    els.openingEvidence.hidden = !selected;
    if (!selected) return;
    const decision = Object.keys(state.uncertaintyDecisions).map(function (key) {
      return state.uncertaintyDecisions[key];
    }).find(function (item) {
      return item && !state.selectedDoor && item.model_opening_index === index;
    });
    const source = state.detection ? state.detection.method : 'manual';
    const confidence = confidenceNumber(selected.confidence);
    els.openingEvidence.innerHTML =
      '<strong>' + (state.selectedDoor ? 'Door evidence' : 'Window ' + (index + 1) + ' evidence') + '</strong>' +
      '<span>Source: ' + escapeHtml(source) + '</span>' +
      '<span>AI confidence: ' + (confidence == null ? 'unknown' : Math.round(confidence * 100) + '%') + '</span>' +
      '<span>Review: ' + escapeHtml(decision ? decision.decision.replace(/_/g, ' ') : 'not reviewed') + '</span>';
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

  const CORNER_LABELS = ['TL', 'TR', 'BR', 'BL'];

  function cornersEditable() {
    return state.activeView === 'original' && !!state.originalImageUrl;
  }

  function originalImageDimensions() {
    if (state.originalImageSize) {
      return state.originalImageSize;
    }
    if (state.activeView === 'original') {
      return imageDimensions();
    }
    return { width: 1, height: 1 };
  }

  function ensureDefaultCorners() {
    if (!state.originalImageUrl || state.activeView !== 'original') {
      return false;
    }
    if (state.corners && state.corners.length === 4) {
      return true;
    }
    initDefaultCorners();
    return !!(state.corners && state.corners.length === 4);
  }

  function initDefaultCorners() {
    const dims = originalImageDimensions();
    if (!dims.width || !dims.height) return;
    const mx = dims.width * 0.08;
    const my = dims.height * 0.08;
    state.corners = [
      [mx, my],
      [dims.width - mx, my],
      [dims.width - mx, dims.height - my],
      [mx, dims.height - my]
    ];
  }

  function resetCorners() {
    if (!state.originalImageUrl) return;
    initDefaultCorners();
    renderCornerOverlay();
    setStatus('', 'Corners reset — drag handles to frame the facade, then Rectify');
  }

  function cornerPointFromEvent(event) {
    const rect = els.image.getBoundingClientRect();
    if (!rect.width || !rect.height) {
      return { x: 0, y: 0 };
    }
    const dims = originalImageDimensions();
    return {
      x: (event.clientX - rect.left) * (dims.width / rect.width),
      y: (event.clientY - rect.top) * (dims.height / rect.height)
    };
  }

  function renderCornerOverlay() {
    const svg = els.cornerSvg;
    if (!cornersEditable()) {
      svg.innerHTML = '';
      if (els.cornerGuide) {
        els.cornerGuide.hidden = true;
      }
      return;
    }

    if (els.cornerGuide) {
      els.cornerGuide.hidden = false;
    }

    if (!ensureDefaultCorners()) {
      svg.innerHTML = '';
      return;
    }

    if (!els.image.complete) {
      return;
    }

    const dims = originalImageDimensions();
    if (dims.width <= 1 || dims.height <= 1) {
      return;
    }

    const nw = dims.width;
    const nh = dims.height;
    svg.setAttribute('viewBox', '0 0 ' + nw + ' ' + nh);
    svg.setAttribute('preserveAspectRatio', 'none');

    const points = state.corners.map(function (c) {
      return c[0] + ',' + c[1];
    }).join(' ');

    let markup =
      '<polygon class="corner-fill" points="' + points + '" />' +
      '<polygon class="corner-line" points="' + points + '" />';

    state.corners.forEach(function (corner, index) {
      markup +=
        '<circle class="corner-handle" data-corner="' + index + '" cx="' + corner[0] +
        '" cy="' + corner[1] + '" r="12" />' +
        '<text class="corner-label" x="' + (corner[0] + 14) + '" y="' + (corner[1] - 10) +
        '">' + CORNER_LABELS[index] + '</text>';
    });

    svg.innerHTML = markup;
  }

  function onCornerMouseDown(event) {
    if (!cornersEditable() || state.cornerDrag) return;
    const target = event.target;
    if (!target.classList.contains('corner-handle')) return;
    event.preventDefault();
    const index = parseInt(target.getAttribute('data-corner'), 10);
    if (Number.isNaN(index)) return;
    const pt = cornerPointFromEvent(event);
    state.cornerDrag = {
      index: index,
      startX: pt.x,
      startY: pt.y,
      orig: state.corners[index].slice()
    };
  }

  function onCornerMouseMove(event) {
    if (!state.cornerDrag) return;
    event.preventDefault();
    const dims = originalImageDimensions();
    const pt = cornerPointFromEvent(event);
    const drag = state.cornerDrag;
    const x = clamp(pt.x, 0, dims.width);
    const y = clamp(pt.y, 0, dims.height);
    state.corners[drag.index] = [x, y];
    renderCornerOverlay();
  }

  function onCornerMouseUp() {
    state.cornerDrag = null;
  }

  function scheduleCornerRender() {
    window.requestAnimationFrame(function () {
      renderCornerOverlay();
      window.requestAnimationFrame(renderCornerOverlay);
    });
  }

  function windowBboxFromMm(win) {
    const wallLength = Number(els.form.elements.namedItem('wall_length').value) || 10000;
    const wallHeight = Number(els.form.elements.namedItem('wall_height').value) || 3300;
    if (!wallLength || !wallHeight || !win.width || !win.height) {
      return null;
    }
    const x1 = win.offset / wallLength;
    const x2 = (win.offset + win.width) / wallLength;
    const y2 = 1 - win.sill_height / wallHeight;
    const y1 = 1 - (win.sill_height + win.height) / wallHeight;
    return [x1, y1, x2, y2];
  }

  function doorBboxFromMm(door) {
    const width = Number(door.width) || 0;
    if (!width) return null;
    const offset = Number(door.offset) || 0;
    const height = Number(door.height) || 2100;
    const x1 = offset / (Number(els.form.elements.namedItem('wall_length').value) || 10000);
    const x2 = (offset + width) / (Number(els.form.elements.namedItem('wall_length').value) || 10000);
    const y2 = 1;
    const y1 = 1 - height / (Number(els.form.elements.namedItem('wall_height').value) || 3300);
    return [x1, y1, x2, y2];
  }

  function ensureDoorBbox() {
    const doorWidth = Number(els.form.elements.namedItem('door_width').value) || 0;
    if (doorWidth <= 0) {
      state.doorBbox = null;
      return null;
    }
    if (state.doorBbox && state.doorBbox.length === 4) {
      return state.doorBbox;
    }
    state.doorBbox = doorBboxFromMm({
      offset: Number(els.form.elements.namedItem('door_offset').value) || 0,
      width: doorWidth,
      height: Number(els.form.elements.namedItem('door_height').value) || 2100
    });
    return state.doorBbox;
  }

  function updateOverlayLayers() {
    const cornerMode = cornersEditable();
    const overlayMode = overlayEditable();
    els.cornerSvg.classList.toggle('inactive', !cornerMode);
    els.overlaySvg.classList.toggle('inactive', !overlayMode);
  }

  function overlayEditable() {
    return (
      (state.activeView === 'rectified' || state.activeView === 'overlay') &&
      state.rectifiedImageUrl
    );
  }

  function imageDimensions() {
    const naturalWidth = els.image.naturalWidth;
    const naturalHeight = els.image.naturalHeight;
    if (naturalWidth > 0 && naturalHeight > 0) {
      return { width: naturalWidth, height: naturalHeight };
    }
    const rect = els.image.getBoundingClientRect();
    return {
      width: rect.width > 0 ? rect.width : 1,
      height: rect.height > 0 ? rect.height : 1
    };
  }

  function imagePointFromEvent(event) {
    const rect = els.image.getBoundingClientRect();
    if (!rect.width || !rect.height) {
      return { x: 0, y: 0 };
    }
    const dims = imageDimensions();
    return {
      x: (event.clientX - rect.left) * (dims.width / rect.width),
      y: (event.clientY - rect.top) * (dims.height / rect.height)
    };
  }

  function ensureWindowBboxNorm(win) {
    if (win.bbox_norm && win.bbox_norm.length === 4) {
      return win.bbox_norm.slice();
    }
    const wallLength = Number(els.form.elements.namedItem('wall_length').value) || 10000;
    const wallHeight = Number(els.form.elements.namedItem('wall_height').value) || 3300;
    if (!wallLength || !wallHeight || !win.width || !win.height) {
      return null;
    }
    const x1 = win.offset / wallLength;
    const x2 = (win.offset + win.width) / wallLength;
    const y2 = 1 - win.sill_height / wallHeight;
    const y1 = 1 - (win.sill_height + win.height) / wallHeight;
    return [x1, y1, x2, y2];
  }

  function ensureWindowsHaveBbox() {
    state.windows.forEach(function (win) {
      const bbox = ensureWindowBboxNorm(win);
      if (bbox) {
        win.bbox_norm = bbox;
      }
    });
  }

  function resolveWindowBbox(win) {
    return ensureWindowBboxNorm(win);
  }

  function ensureWindowBboxes() {
    ensureWindowsHaveBbox();
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
    persistActiveStoreyWindows();
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
    scheduleOverlayRender();
  }

  function svgPointFromEvent(event) {
    return imagePointFromEvent(event);
  }

  function minBoxPixels() {
    const dims = imageDimensions();
    return {
      width: dims.width * 0.02,
      height: dims.height * 0.02
    };
  }

  function scheduleOverlayRender() {
    window.requestAnimationFrame(function () {
      renderDetectionOverlay();
      window.requestAnimationFrame(renderDetectionOverlay);
    });
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

  function renderUnderstandingMarkup() {
    const understanding = state.understanding;
    if (!understanding || (els.showAiGuides && !els.showAiGuides.checked)) return '';
    const facade = understanding.facade_bbox || [0, 0, 1, 1];
    const facadeBox = bboxPixelsFromNorm(facade);
    let markup = '<g class="architecture-guide">' +
      '<rect class="architecture-facade" x="' + facadeBox.x + '" y="' + facadeBox.y +
      '" width="' + facadeBox.w + '" height="' + facadeBox.h + '" />';

    (understanding.storeys || []).forEach(function (storey) {
      const range = storey.y_range || [];
      if (range.length !== 2) return;
      const y = range[0] * imageDimensions().height;
      const height = Math.max((range[1] - range[0]) * imageDimensions().height, 1);
      markup += '<rect class="architecture-storey" x="' + facadeBox.x + '" y="' + y +
        '" width="' + facadeBox.w + '" height="' + height + '" />' +
        '<text class="architecture-label" x="' + (facadeBox.x + 5) + '" y="' + (y + 13) +
        '">S' + storey.id + '</text>';
    });

    (understanding.bays || []).forEach(function (bay) {
      const x = Number(bay.x_center) * imageDimensions().width;
      markup += '<line class="architecture-bay" x1="' + x + '" y1="' + facadeBox.y +
        '" x2="' + x + '" y2="' + (facadeBox.y + facadeBox.h) + '" />' +
        '<text class="architecture-label bay-label" x="' + (x + 4) + '" y="' +
        (facadeBox.y + facadeBox.h - 5) + '">B' + bay.id + '</text>';
    });

    (understanding.uncertain_openings || []).forEach(function (item, index) {
      if (!item.bbox || item.bbox.length !== 4) return;
      const box = bboxPixelsFromNorm(item.bbox);
      const selected = state.selectedUncertaintyIndex === index;
      const decided = state.uncertaintyDecisions[index];
      markup += '<rect class="architecture-uncertain' + (selected ? ' selected' : '') +
        (decided ? ' decided' : '') + '" x="' + box.x + '" y="' + box.y +
        '" width="' + box.w + '" height="' + box.h + '" />';
    });
    return markup + '</g>';
  }

  function renderDetectionOverlay() {
    const svg = els.overlaySvg;
    if (!overlayEditable()) {
      svg.innerHTML = '';
      return;
    }

    if (!els.image.complete) {
      return;
    }

    const dims = imageDimensions();
    if (dims.width <= 1 || dims.height <= 1) {
      return;
    }

    const nw = dims.width;
    const nh = dims.height;
    svg.setAttribute('viewBox', '0 0 ' + nw + ' ' + nh);
    svg.setAttribute('preserveAspectRatio', 'none');

    ensureWindowBboxes();

    let markup =
      '<rect class="det-hitlayer" x="0" y="0" width="' + nw + '" height="' + nh + '" />';
    markup += renderUnderstandingMarkup();

    state.windows.forEach(function (win, index) {
      const bbox = resolveWindowBbox(win);
      if (!bbox || bbox.length !== 4) return;
      win.bbox_norm = bbox;
      const box = bboxPixelsFromNorm(bbox);
      if (box.w < 1 || box.h < 1) return;
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
    const doorBbox = ensureDoorBbox();
    if (doorBbox && doorBbox.length === 4 && doorWidth > 0) {
      const box = bboxPixelsFromNorm(doorBbox);
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
    event.preventDefault();
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
    if (state.drawMode && (target.classList.contains('det-hitlayer') || target === els.overlaySvg || target.classList.contains('det-preview'))) {
      event.preventDefault();
      event.stopPropagation();
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
    event.preventDefault();
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
    if (cornersEditable()) {
      els.viewerHint.textContent = 'Drag corner handles to frame facade · then Rectify Facade';
      return;
    }
    if (!overlayEditable()) return;
    if (state.drawMode) {
      els.viewerHint.textContent = 'Drag on image to draw a window · Esc to cancel';
    } else {
      els.viewerHint.textContent =
        'Click to select · drag box to move · drag corners to resize · Draw window to add';
    }
  }

  function updateViewerToolbar() {
    const cornerMode = cornersEditable();
    const overlayMode = overlayEditable();
    updateOverlayLayers();
    els.viewerToolbar.hidden = !cornerMode && !overlayMode;
    els.btnDrawWindow.hidden = !overlayMode;
    els.btnDeleteSelected.hidden = !overlayMode;
    if (els.cornerGuide) {
      els.cornerGuide.hidden = !cornerMode;
    }
    if (cornerMode || overlayMode) {
      updateViewerHint();
    }
  }

  function renderWindows(windows) {
    state.windows = windows || [];
    state.storeyWindows[state.activeStoreyIndex] = cloneWindows(state.windows);
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
        '<h3>' + storeyLabel(state.activeStoreyIndex) + ' · Window ' + (index + 1) + '</h3>' +
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
    renderStoreySelector();
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
    persistActiveStoreyWindows();
    renderTree();
  }

  function renderTreeLegacy() {
    const params = collectParams();
    const items = [
      'Project: ' + params.project_name,
      'Wall: ' + params.wall_length + ' × ' + params.wall_height + ' × ' + params.wall_thickness + ' mm',
      'Storeys: ' + params.storey_count + (params.storey_height ? ' @ ' + params.storey_height + ' mm' : ''),
      'LOD: ' + (params.lod_level || 'lod_200'),
      'Windows: ' + summarizeStoreyWindows(),
      'Door: ' + params.door.width + ' × ' + params.door.height + ' mm @ ' + params.door.offset
    ];

    if (params.building_elements) {
      const enabled = Object.keys(params.building_elements).filter(function (key) {
        return params.building_elements[key];
      });
      if (enabled.length > 0) {
        items.push('Building: ' + enabled.join(', ') + ' (depth ' + params.building_depth + ' mm)');
      }
    }

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

    if (state.multiview) {
      items.push(
        'Multi-view: ' + state.multiview.method +
        ' — ' + state.multiview.match_count + ' matches, ' +
        state.multiview.inlier_count + ' inliers (' + state.multiview.confidence + ')'
      );
    }

    if (state.fusion) {
      items.push(
        'Fusion: ' + state.fusion.fusion_method +
        ' — ' + (state.fusion.fused_elements || []).length + ' openings (' +
        state.fusion.fusion_confidence + ')'
      );
    }

    if (state.pattern) {
      items.push(
        'Pattern: ' + state.pattern.type +
        ' (' + (state.pattern.patterns_detected || []).join(', ') + ')' +
        (state.pattern.component_id ? ' · ' + state.pattern.component_id : '')
      );
    }

    if (state.rationalization) {
      items.push(
        'Rationalized: ' + state.rationalization.method +
        ' (' + (state.rationalization.constraints_applied || []).join(', ') + ')'
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

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (character) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character];
    });
  }

  function confidenceNumber(value) {
    const number = Number(value);
    return value == null || !Number.isFinite(number) ? null : number;
  }

  function renderTree() {
    const params = collectParams();
    const items = [
      { type: 'project', title: params.project_name, detail: 'Project' },
      { type: 'wall', title: 'Facade wall', detail: params.wall_length + ' × ' + params.wall_height + ' × ' + params.wall_thickness + ' mm' },
      { type: 'storey', title: params.storey_count + ' storey' + (params.storey_count === 1 ? '' : 's'), detail: params.storey_height ? params.storey_height + ' mm each' : 'Automatic height' },
      { type: 'lod', title: (params.lod_level || 'lod_200').toUpperCase(), detail: 'Model detail' }
    ];
    if (state.understanding) {
      const uncertaintyCount = (state.understanding.uncertainties || []).length;
      items.push({
        type: uncertaintyCount ? 'review' : 'ai',
        title: 'Architectural understanding',
        detail: state.understanding.storey_count + ' storeys · ' + state.understanding.bay_count + ' bays',
        needsReview: uncertaintyCount > 0
      });
      (state.understanding.uncertain_openings || []).forEach(function (_uncertainty, index) {
        const decisionRecord = state.uncertaintyDecisions[index];
        items.push({
          type: 'review',
          title: 'Uncertain opening ' + (index + 1),
          detail: decisionRecord ? decisionRecord.decision.replace(/_/g, ' ') : 'Click to inspect',
          needsReview: !decisionRecord,
          uncertaintyIndex: index
        });
      });
    }
    if (state.detection) items.push({ type: 'ai', title: 'AI detection', detail: state.detection.method, confidence: confidenceNumber(state.detection.confidence) });
    if (state.rectification) items.push({ type: 'rectify', title: 'Perspective corrected', detail: state.rectification.method, confidence: confidenceNumber(state.rectification.confidence) });
    if (state.multiview) items.push({ type: 'views', title: 'Multi-view', detail: state.multiview.match_count + ' matches · ' + state.multiview.inlier_count + ' inliers', confidence: confidenceNumber(state.multiview.confidence) });
    if (state.fusion) items.push({ type: 'ai', title: 'View fusion', detail: (state.fusion.fused_elements || []).length + ' openings', confidence: confidenceNumber(state.fusion.fusion_confidence) });
    if (requiresReconstructionReview()) items.push({ type: 'review', title: 'Confirmation required', detail: 'Review the AI geometry before Generate', needsReview: true });
    state.windows.forEach(function (win, index) {
      items.push({ type: 'window', title: 'Window ' + (index + 1), detail: win.width + ' × ' + win.height + ' mm · sill ' + win.sill_height, confidence: confidenceNumber(win.confidence), index: index });
    });
    if (params.door.width > 0) items.push({ type: 'door', title: 'Door', detail: params.door.width + ' × ' + params.door.height + ' mm', confidence: state.doorConfidence, door: true });

    const reviewOnly = els.treeReviewOnly && els.treeReviewOnly.checked;
    const visible = items.filter(function (item) {
      return !reviewOnly || item.needsReview || (item.confidence != null && item.confidence < 0.65);
    });
    els.tree.innerHTML = visible.map(function (item) {
      const confidence = item.confidence == null ? '' : '<span class="confidence ' + (item.confidence < 0.65 ? 'low' : item.confidence < 0.82 ? 'medium' : 'high') + '">' + Math.round(item.confidence * 100) + '%</span>';
      const action = item.index != null ? ' data-tree-window="' + item.index + '"' : item.door ? ' data-tree-door="true"' : item.uncertaintyIndex != null ? ' data-tree-uncertainty="' + item.uncertaintyIndex + '"' : '';
      return '<li class="tree-item' + (action ? ' actionable' : '') + '"' + action + '><span class="tree-icon ' + item.type + '" aria-hidden="true"></span><span class="tree-copy"><strong>' + escapeHtml(item.title) + '</strong><small>' + escapeHtml(item.detail || '') + '</small></span>' + confidence + '</li>';
    }).join('');
    els.treeSummary.textContent = params.windows.length + ' windows' + (params.door.width > 0 ? ' · 1 door' : '') + (reviewOnly ? ' · review filter' : '');
    els.tree.querySelectorAll('[data-tree-window]').forEach(function (item) {
      item.addEventListener('click', function () { selectWindow(Number(item.dataset.treeWindow)); setActiveView('overlay'); });
    });
    els.tree.querySelectorAll('[data-tree-door]').forEach(function (item) {
      item.addEventListener('click', function () { selectDoor(); setActiveView('overlay'); });
    });
    els.tree.querySelectorAll('[data-tree-uncertainty]').forEach(function (item) {
      item.addEventListener('click', function () { selectUncertainty(Number(item.dataset.treeUncertainty)); });
    });
  }

  function selectUncertainty(index) {
    state.selectedUncertaintyIndex = index;
    setActiveView('overlay');
    renderUncertaintyReview();
    scheduleOverlayRender();
  }

  function renderUncertaintyReview() {
    if (!els.uncertaintyReview) return;
    const items = (state.understanding && state.understanding.uncertain_openings) || [];
    const item = state.selectedUncertaintyIndex == null ? null : items[state.selectedUncertaintyIndex];
    els.uncertaintyReview.hidden = !item;
    if (!item) return;
    els.uncertaintyReviewLabel.textContent = 'Uncertain opening ' + (state.selectedUncertaintyIndex + 1);
  }

  function decideUncertainty(decision) {
    if (state.selectedUncertaintyIndex == null) return;
    const items = (state.understanding && state.understanding.uncertain_openings) || [];
    const item = items[state.selectedUncertaintyIndex] || {};
    state.uncertaintyDecisions[state.selectedUncertaintyIndex] = {
      decision: decision,
      opening_id: item.id || ('uncertain_' + (state.selectedUncertaintyIndex + 1)),
      model_opening_index: nearestWindowIndex(item.bbox),
      reviewer: 'sketchup_user',
      reviewed_at: new Date().toISOString()
    };
    setStatus('success', 'Uncertainty recorded: ' + decision.replace(/_/g, ' ') + '.');
    renderTree();
    scheduleOverlayRender();
  }

  function nearestWindowIndex(targetBbox) {
    if (!targetBbox) return null;
    let bestIndex = null;
    let bestDistance = Infinity;
    state.windows.forEach(function (win, index) {
      const bbox = resolveWindowBbox(win);
      if (!bbox) return;
      const distance = Math.abs(bbox[0] - targetBbox[0]) + Math.abs(bbox[1] - targetBbox[1]) +
        Math.abs(bbox[2] - targetBbox[2]) + Math.abs(bbox[3] - targetBbox[3]);
      if (distance < bestDistance) { bestDistance = distance; bestIndex = index; }
    });
    return bestIndex;
  }

  function editSelectedUncertainty() {
    const items = (state.understanding && state.understanding.uncertain_openings) || [];
    const item = items[state.selectedUncertaintyIndex];
    if (!item || !item.bbox) return;
    const bestIndex = nearestWindowIndex(item.bbox);
    if (bestIndex != null) selectWindow(bestIndex);
    decideUncertainty('manual_edit');
    setStatus('warning', 'Opening selected · drag its box or handles to correct the geometry.');
  }

  function parsePartitionDoorOffsets(raw) {
    if (!raw || !String(raw).trim()) {
      return null;
    }
    return String(raw).split(',').map(function (value) {
      return Number(value.trim());
    }).filter(function (value) {
      return !Number.isNaN(value);
    });
  }

  function collectYoloExportPayload() {
    persistActiveStoreyWindows();
    ensureWindowBboxes();
    const groundWindows = state.storeyWindows[0] || state.windows || [];
    const windows = groundWindows.map(function (win) {
      const bbox = resolveWindowBbox(win);
      return bbox ? { bbox_norm: bbox.slice() } : null;
    }).filter(Boolean);

    const doorWidth = Number(els.form.elements.namedItem('door_width').value) || 0;
    const doorBbox = doorWidth > 0 ? ensureDoorBbox() : null;

    return {
      project_name: els.form.elements.namedItem('project_name').value,
      source_path: state.sourcePath,
      yolo_split: els.yoloSplit ? els.yoloSplit.value : 'train',
      windows: windows,
      door_bbox_norm: doorBbox
    };
  }

  function collectParams() {
    persistActiveStoreyWindows();
    const formData = new FormData(els.form);
    const storeyWindows = state.storeyWindows.map(function (storeyWins) {
      return (storeyWins || []).map(function (win) {
        return {
          offset: Number(win.offset),
          width: Number(win.width),
          height: Number(win.height),
          sill_height: Number(win.sill_height),
          confidence: confidenceNumber(win.confidence),
          bbox_norm: win.bbox_norm || null
        };
      });
    });
    const windows = storeyWindows[state.activeStoreyIndex] || storeyWindows[0] || [];

    return {
      project_name: formData.get('project_name'),
      wall_length: Number(formData.get('wall_length')),
      wall_height: Number(formData.get('wall_height')),
      auto_scale: formData.get('auto_scale') === 'on',
      wall_thickness: Number(formData.get('wall_thickness')),
      building_depth: Number(formData.get('building_depth') || 6000),
      building_elements: {
        floor: formData.get('include_floor') === 'on',
        roof: formData.get('include_roof') === 'on',
        columns: formData.get('include_columns') === 'on',
        beam: formData.get('include_beam') === 'on',
        stair: formData.get('include_stair') === 'on',
        balcony: formData.get('include_balcony') === 'on',
        parapet: formData.get('include_parapet') === 'on',
        cornice: formData.get('include_cornice') === 'on',
        perimeter_walls: formData.get('include_perimeter_walls') === 'on',
        structural_grid: formData.get('include_structural_grid') === 'on',
        interior_partitions: formData.get('include_interior_partitions') === 'on',
        full_trim: formData.get('include_full_trim') === 'on',
        partition_doors: formData.get('include_partition_doors') === 'on',
        room_zones: formData.get('include_room_zones') === 'on',
        room_types: formData.get('include_room_types') === 'on',
        furniture: formData.get('include_furniture') === 'on',
        fixture_sets: formData.get('include_fixture_sets') === 'on',
        fixture_catalog: formData.get('include_fixture_catalog') === 'on',
        structural_constraints: formData.get('include_structural_constraints') === 'on',
        perpendicular_constraints: formData.get('include_perpendicular_constraints') === 'on',
        perpendicular_repair: formData.get('include_perpendicular_repair') === 'on',
        furniture_collision: formData.get('include_furniture_collision') === 'on',
        furniture_wall_align: formData.get('include_furniture_wall_align') === 'on'
      },
      room_type_overrides: formData.get('room_type_overrides') || '',
      room_furniture_layouts: formData.get('room_furniture_layouts') || '',
      fixture_catalog_path: formData.get('fixture_catalog_path') || '',
      partition_grid_spacing: formData.get('partition_grid_spacing')
        ? Number(formData.get('partition_grid_spacing'))
        : null,
      partition_count: Number(formData.get('partition_count') || 1),
      partition_door_width: Number(formData.get('partition_door_width') || 900),
      partition_door_height: Number(formData.get('partition_door_height') || 2100),
      partition_door_offsets: parsePartitionDoorOffsets(formData.get('partition_door_offsets')),
      storey_count: Number(formData.get('storey_count') || 1),
      storey_height: formData.get('storey_height') ? Number(formData.get('storey_height')) : null,
      repeat_openings: formData.get('repeat_openings') === 'on',
      lod_level: formData.get('lod_level') || 'lod_200',
      grid_x_spacing: formData.get('grid_x_spacing') ? Number(formData.get('grid_x_spacing')) : null,
      grid_y_spacing: formData.get('grid_y_spacing') ? Number(formData.get('grid_y_spacing')) : null,
      geometry_doctor: {
        tiny_edges: formData.get('doctor_tiny_edges') === 'on',
        tiny_faces: formData.get('doctor_tiny_faces') === 'on',
        coplanar_merge: formData.get('doctor_coplanar_merge') === 'on',
        duplicate_faces: formData.get('doctor_duplicate_faces') === 'on',
        duplicate_instances: formData.get('doctor_duplicate_instances') === 'on',
        normal_repair: formData.get('doctor_normal_repair') === 'on',
        alignment_repair: formData.get('doctor_alignment_repair') === 'on',
        opening_repair: formData.get('doctor_opening_repair') === 'on',
        grid_mm: Number(formData.get('doctor_grid_mm') || 10)
      },
      windows: windows,
      storey_windows: storeyWindows,
      door: {
        offset: Number(formData.get('door_offset')),
        width: Number(formData.get('door_width')),
        height: Number(formData.get('door_height')),
        confidence: state.doorConfidence,
        bbox_norm: state.doorBbox
      },
      source_path: state.sourcePath,
      source_id: state.sourceId,
      secondary_source_path: state.secondarySourcePath,
      secondary_source_id: state.secondarySourceId,
      corners: state.corners && state.corners.length === 4
        ? state.corners.map(function (c) { return [c[0], c[1]]; })
        : null,
      detection_method: els.detectMethod ? els.detectMethod.value : 'auto',
      register_method: els.registerMethod ? els.registerMethod.value : 'auto',
      depth_method: els.depthMethod ? els.depthMethod.value : 'auto',
      rationalization: state.rationalization,
      pattern: state.pattern,
      multiview: state.multiview,
      fusion: state.fusion,
      constraint_solution: state.constraintSolution,
      reconstruction_review: state.reconstructionReview,
      uncertainty_decisions: state.uncertaintyDecisions
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
      if (els.cornerGuide) {
        els.cornerGuide.hidden = true;
      }
      els.overlaySvg.innerHTML = '';
      els.cornerSvg.innerHTML = '';
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
    updateOverlayLayers();
    if (els.image.complete) {
      if (state.activeView === 'original') {
        ensureDefaultCorners();
        renderCornerOverlay();
        els.overlaySvg.innerHTML = '';
      } else {
        if (els.cornerGuide) {
          els.cornerGuide.hidden = true;
        }
        els.cornerSvg.innerHTML = '';
        renderDetectionOverlay();
      }
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

    if (payload.storey_count) {
      els.form.elements.namedItem('storey_count').value = payload.storey_count;
    }

    initStoreyWindowsFromPayload(payload);
    renderWindows(state.windows);

    const door = payload.door || {};
    els.form.elements.namedItem('door_offset').value = door.offset || 0;
    els.form.elements.namedItem('door_width').value = door.width || 0;
    els.form.elements.namedItem('door_height').value = door.height || 2100;

    state.detection = null;
    state.rationalization = null;
    state.constraintSolution = payload.constraint_solution || null;
    state.reconstructionReview = null;
    renderReconstructionReview();
    state.reconstructionReview = payload.reconstruction_review || null;
    state.pattern = null;
    state.overlayImageUrl = null;
    state.doorBbox = null;
    state.drag = null;
    state.corners = null;
    state.originalImageSize = null;
    state.cornerDrag = null;
    setDrawMode(false);
    clearSelection();
    els.detectMeta.textContent = 'Detection: not run';

    if (payload.source_path) {
      setImage('file:///' + payload.source_path.replace(/\\/g, '/'), payload.source_path);
    }

    renderTree();
    if (mode === 'template') {
      setStatus('', 'Phase 0 template loaded — for testing only');
    } else {
      setStatus('', 'Ready — load a photo to begin');
    }
    if (payload.ir_preview) {
      setIrPreview(payload.ir_preview);
    }
  }

  function setVideoFrames(payload) {
    const picker = document.getElementById('video-frame-picker');
    if (!picker) return;
    picker.innerHTML = '';
    if (!payload || !payload.frames || !payload.frames.length) {
      picker.hidden = true;
      return;
    }
    picker.hidden = false;
    const title = document.createElement('div');
    title.className = 'meta';
    title.textContent =
      'Video frames: ' + payload.frames.length +
      ' · ' + (payload.duration_sec || 0) + 's';
    picker.appendChild(title);
    const grid = document.createElement('div');
    grid.className = 'video-frame-grid';
    payload.frames.forEach(function (frame) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'video-frame-thumb';
      button.title = 'Frame ' + (frame.frame_number + 1) + ' @ ' + frame.timestamp_sec + 's';
      if (frame.thumb_url) {
        const img = document.createElement('img');
        img.src = frame.thumb_url;
        img.alt = 'Video frame ' + (frame.index + 1);
        button.appendChild(img);
      } else {
        button.textContent = '#' + (frame.index + 1);
      }
      button.addEventListener('click', function () {
        sketchupCall('load_video_frame', JSON.stringify({ path: frame.path }));
      });
      grid.appendChild(button);
    });
    picker.appendChild(grid);
    els.sourceMeta.textContent = payload.video_path || 'Video loaded';
  }

  function setImage(fileUrl, sourcePath, sourceKind) {
    setWorkflowStage(0);
    state.sourcePath = sourcePath;
    state.sourceId = sourcePath ? 'photo_001' : null;
    state.originalImageUrl = fileUrl;
    state.rectifiedImageUrl = null;
    state.rectification = null;
    state.detection = null;
    state.rationalization = null;
    state.pattern = null;
    state.secondarySourcePath = null;
    state.secondarySourceId = null;
    state.secondaryImageUrl = null;
    state.multiview = null;
    state.fusion = null;
    state.overlayImageUrl = null;
    state.doorBbox = null;
    state.drag = null;
    state.corners = null;
    state.originalImageSize = null;
    state.cornerDrag = null;
    setDrawMode(false);
    clearSelection();
    els.sourceMeta.textContent = sourcePath || 'Primary image loaded';
    els.secondaryMeta.textContent = 'Secondary: not loaded';
    els.multiviewMeta.textContent = 'Multi-view: not registered';
    els.rectifyMeta.textContent = 'Rectification: not run';
    els.detectMeta.textContent = 'Detection: not run';
    renderWindows([]);
    els.form.elements.namedItem('door_offset').value = 0;
    els.form.elements.namedItem('door_width').value = 0;
    els.form.elements.namedItem('project_name').value = 'Untitled Facade';
    setActiveView('original');
    renderTree();
    setStatus('', sourceKind === 'video_frame'
      ? 'Video frame loaded — drag corners to frame facade, then Rectify'
      : 'Photo loaded — drag corners to frame facade, then Rectify');
    window.requestAnimationFrame(function () {
      if (ensureDefaultCorners()) {
        renderCornerOverlay();
        updateViewerToolbar();
      }
    });
  }

  function setSecondaryImage(fileUrl, sourcePath) {
    state.secondarySourcePath = sourcePath;
    state.secondarySourceId = sourcePath ? 'view_002' : null;
    state.secondaryImageUrl = fileUrl;
    state.multiview = null;
    els.secondaryMeta.textContent = sourcePath || 'Secondary image loaded';
    els.multiviewMeta.textContent = 'Multi-view: not registered';
    renderTree();
    setStatus('', 'Secondary image loaded — click Register Views to align with primary');
  }

  function setMultiviewRegistration(result) {
    state.multiview = result || null;
    if (state.multiview) {
      els.multiviewMeta.textContent =
        'Multi-view: ' + state.multiview.method +
        ' | ' + state.multiview.match_count + ' matches, ' +
        state.multiview.inlier_count + ' inliers | confidence ' + state.multiview.confidence;
    } else {
      els.multiviewMeta.textContent = 'Multi-view: not registered';
    }
    renderTree();
  }

  function setRectifiedImage(fileUrl, result) {
    state.rectifiedImageUrl = fileUrl;
    state.rectification = result;
    els.rectifyMeta.textContent =
      'Rectification: ' + result.method + ' | confidence ' + result.confidence +
      ' | lines ' + result.line_count;
    setActiveView('rectified');
    scheduleOverlayRender();
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
    if (state.rectifiedImageUrl) {
      setActiveView('overlay');
    } else if (overlayUrl) {
      setActiveView('overlay');
    }
    scheduleOverlayRender();
    renderTree();
  }

  function onDetectionEmpty(detection, overlayUrl) {
    setDetectionMeta(detection, overlayUrl);
    setDrawMode(false);
    setStatus(
      'warning',
      'No openings detected — click Draw window on the image, or try Detection: Contour.'
    );
  }

  function applyFusion(payload, overlayUrl) {
    applyDetection(payload, overlayUrl);
    state.fusion = payload.fusion || null;
    renderTree();
    if (state.fusion) {
      setStatus(
        'success',
        'Fused openings from two views — review overlay, then Rationalize or Generate.'
      );
    }
  }

  function applyReconstruction(payload, overlayUrl) {
    applyDetection(payload, overlayUrl);
    state.understanding = payload.understanding || null;
    state.selectedUncertaintyIndex = null;
    state.uncertaintyDecisions = {};
    state.constraintSolution = payload.constraint_solution || null;
    state.reconstructionReview = payload.reconstruction_review || null;
    if (state.understanding && state.understanding.storey_count) {
      els.form.elements.namedItem('storey_count').value = state.understanding.storey_count;
      onStoreyCountChange();
    }
    if (payload.ir_preview) setIrPreview(payload.ir_preview);
    renderReconstructionReview();
    renderTree();

    const summary = state.understanding;
    if (summary) {
      const uncertain = (summary.uncertainties || []).length;
      setStatus(
        uncertain || payload.review_required ? 'warning' : 'success',
        'AI understanding: ' + summary.storey_count + ' storeys, ' +
          summary.bay_count + ' bays, ' + summary.opening_count + ' openings' +
          (uncertain ? ' · ' + uncertain + ' uncertain items need review.' : ' · ready for review.')
      );
    }
  }

  function applyDetection(payload, overlayUrl) {
    setWorkflowStage(2);
    if (payload.scale_hint) {
      els.form.elements.namedItem('wall_length').value = payload.scale_hint.wall_length_mm;
      els.form.elements.namedItem('wall_height').value = payload.scale_hint.wall_height_mm;
    }
    const windows = (payload.windows || []).map(function (win) {
      return {
        offset: Number(win.offset),
        width: Number(win.width),
        height: Number(win.height),
        sill_height: Number(win.sill_height),
        bbox_norm: win.bbox_norm,
        confidence: confidenceNumber(win.confidence)
      };
    });
    state.storeyWindows[0] = cloneWindows(windows);
    if (isRepeatOpenings()) {
      copyGroundWindowsToUpperStoreys();
    }
    state.activeStoreyIndex = 0;
    state.windows = cloneWindows(state.storeyWindows[0] || windows);
    clearSelection();
    renderWindows(state.windows);
    renderStoreySelector();

    const door = payload.door || {};
    const doorWidth = Number(door.width) || 0;
    els.form.elements.namedItem('door_offset').value = door.offset || 0;
    els.form.elements.namedItem('door_width').value = doorWidth;
    els.form.elements.namedItem('door_height').value = doorWidth > 0 ? (door.height || 2100) : 0;
    if (door.bbox_norm && doorWidth > 0) {
      state.doorBbox = door.bbox_norm;
    } else {
      state.doorBbox = doorWidth > 0 ? doorBboxFromMm(door) : null;
    }
    state.doorConfidence = confidenceNumber(door.confidence);

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
    scheduleOverlayRender();
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

  function applyPattern(payload) {
    const windows = (payload.windows || []).map(function (win) {
      return {
        offset: Number(win.offset),
        width: Number(win.width),
        height: Number(win.height),
        sill_height: Number(win.sill_height),
        bbox_norm: win.bbox_norm || windowBboxFromMm(win),
        component_id: win.component_id
      };
    });

    renderWindows(windows);

    const door = payload.door || {};
    const doorWidth = Number(door.width) || 0;
    els.form.elements.namedItem('door_offset').value = door.offset || 0;
    els.form.elements.namedItem('door_width').value = doorWidth;
    els.form.elements.namedItem('door_height').value = doorWidth > 0 ? (door.height || 2100) : 0;
    state.doorBbox = doorWidth > 0 ? (door.bbox_norm || doorBboxFromMm(door)) : null;

    state.pattern = payload.pattern || null;
    scheduleOverlayRender();
    renderTree();

    const patternType = state.pattern ? state.pattern.type : 'none';
    if (patternType === 'none' || patternType === 'custom') {
      setStatus('', 'No repeating bay pattern detected — dimensions kept as-is.');
    } else {
      setStatus(
        'success',
        'Pattern applied — shared component ' + (state.pattern.component_id || 'pending') + '.'
      );
    }
  }

  function applyRationalization(payload) {
    const windows = (payload.windows || []).map(function (win) {
      const mapped = {
        offset: Number(win.offset),
        width: Number(win.width),
        height: Number(win.height),
        sill_height: Number(win.sill_height),
        bbox_norm: win.bbox_norm || windowBboxFromMm(win)
      };
      return mapped;
    });

    renderWindows(windows);

    const door = payload.door || {};
    const doorWidth = Number(door.width) || 0;
    els.form.elements.namedItem('door_offset').value = door.offset || 0;
    els.form.elements.namedItem('door_width').value = doorWidth;
    els.form.elements.namedItem('door_height').value = doorWidth > 0 ? (door.height || 2100) : 0;
    state.doorBbox = doorWidth > 0 ? (door.bbox_norm || doorBboxFromMm(door)) : null;

    state.rationalization = payload.rationalization || null;
    scheduleOverlayRender();
    renderTree();
    setStatus('success', 'Dimensions rationalized — review Inspector, then Validate or Generate.');
  }

  function applyConstraintSolution(payload) {
    const windows = (payload.windows || []).map(function (win) {
      return {
        offset: Number(win.offset),
        width: Number(win.width),
        height: Number(win.height),
        sill_height: Number(win.sill_height),
        bbox_norm: win.bbox_norm || windowBboxFromMm(win)
      };
    });

    renderWindows(windows);

    const door = payload.door || {};
    const doorWidth = Number(door.width) || 0;
    els.form.elements.namedItem('door_offset').value = door.offset || 0;
    els.form.elements.namedItem('door_width').value = doorWidth;
    els.form.elements.namedItem('door_height').value = doorWidth > 0 ? (door.height || 2100) : 0;
    state.doorBbox = doorWidth > 0 ? (door.bbox_norm || doorBboxFromMm(door)) : null;

    state.constraintSolution = payload.constraint_solution || null;
    state.reconstructionReview = null;
    renderReconstructionReview();
    scheduleOverlayRender();
    renderTree();
    setStatus('success', 'Constraint solution applied — review Inspector, then Validate or Generate.');
  }

  function setIrPreview(ir) {
    if (!ir || !ir.openings) return;
    renderTree();
    const solver = ir.reconstruction && ir.reconstruction.constraint_solver;
    state.constraintSolution = solver || state.constraintSolution;
    state.reconstructionReview = (ir.reconstruction && ir.reconstruction.review) || state.reconstructionReview;
    renderReconstructionReview();
    if (!solver) return;
    if (solver.safety_status === 'fallback_observed_geometry') {
      setStatus('warning', 'Unsafe AI optimization was rejected. Original detected geometry is preserved; review is recommended.');
    } else if (solver.safety_status === 'accepted_after_soft_weight_retry') {
      setStatus('warning', 'AI geometry was optimized with reduced constraint strength; review is recommended.');
    } else {
      setStatus('success', 'AI geometry was optimized and passed safety checks.');
    }
  }

  function reviewDecision(decision) {
    state.reconstructionReview = {
      decision: decision,
      reviewer: 'sketchup_user',
      reviewed_at: new Date().toISOString(),
      solver_status: state.constraintSolution && state.constraintSolution.safety_status
    };
    renderReconstructionReview();
    setStatus('success', 'Reconstruction review recorded: ' + decision.replace(/_/g, ' ') + '.');
  }

  function requiresReconstructionReview() {
    if (!state.constraintSolution) return false;
    return ['fallback_observed_geometry', 'accepted_after_soft_weight_retry'].indexOf(state.constraintSolution.safety_status) >= 0;
  }

  function reconstructionReviewApproved() {
    if (!state.reconstructionReview) return false;
    return ['accepted_observed_geometry', 'accepted_manual_adjustments'].indexOf(state.reconstructionReview.decision) >= 0;
  }

  function renderReconstructionReview() {
    if (!els.reconstructionReview) return;
    const needsReview = requiresReconstructionReview();
    els.reconstructionReview.hidden = !needsReview;
    if (!needsReview) return;
    const reasons = state.constraintSolution.fallback_reasons || [];
    const decision = state.reconstructionReview && state.reconstructionReview.decision;
    els.reconstructionReviewDetail.textContent = decision
      ? 'Recorded: ' + decision.replace(/_/g, ' ')
      : 'Reason: ' + (reasons.join(', ') || 'unsafe constraint result');
  }

  function applyRoomLayoutSuggestion(layout) {
    const field = els.form.querySelector('[name="room_furniture_layouts"]');
    if (!field) return;
    field.value = layout || '';
    setStatus('success', 'Room layout presets filled — review and Generate.');
  }

  window.geomora = {
    loadPayload: loadPayload,
    setImage: setImage,
    resetCorners: resetCorners,
    ensureDefaultCorners: ensureDefaultCorners,
    setVideoFrames: setVideoFrames,
    setSecondaryImage: setSecondaryImage,
    setMultiviewRegistration: setMultiviewRegistration,
    setRectifiedImage: setRectifiedImage,
    applyDetection: applyDetection,
    applyReconstruction: applyReconstruction,
    applyFusion: applyFusion,
    applyRationalization: applyRationalization,
    applyConstraintSolution: applyConstraintSolution,
    applyPattern: applyPattern,
    applyRoomLayoutSuggestion: applyRoomLayoutSuggestion,
    setRoomLayoutPreview: setRoomLayoutPreview,
    setLayoutCatalogPalette: setLayoutCatalogPalette,
    setCatalogDiffPreview: setCatalogDiffPreview,
    setViewportSnapshot: setViewportSnapshot,
    setDetectionMeta: setDetectionMeta,
    onDetectionEmpty: onDetectionEmpty,
    setIrPreview: setIrPreview,
    setStatus: setStatus,
    setWorkflowStage: setWorkflowStage
  };

  window.geomoraLayoutBootstrap = {
    requestPreview: function () {
      sketchupCall('preview_room_layout', JSON.stringify(collectParams()));
    },
    requestPalette: function () {
      sketchupCall('layout_catalog_palette', JSON.stringify(collectParams()));
    },
    requestCatalogDiff: function () {
      sketchupCall('preview_fixture_catalog_diff', JSON.stringify(collectParams()));
    },
    exportLayoutReport: function () {
      sketchupCall('export_layout_report', JSON.stringify(collectParams()));
    },
    syncLayoutField: function (layout) {
      const field = els.form.querySelector('[name="room_furniture_layouts"]');
      if (field) field.value = layout || '';
    },
    setStatus: setStatus
  };

  function setRoomLayoutPreview(storeys) {
    if (window.geomoraLayoutEditor) {
      window.geomoraLayoutEditor.setPreview(storeys);
    }
  }

  function setLayoutCatalogPalette(items) {
    if (window.geomoraLayoutEditor) {
      window.geomoraLayoutEditor.setPalette(items);
    }
  }

  function setCatalogDiffPreview(diff) {
    if (window.geomoraLayoutEditor) {
      window.geomoraLayoutEditor.setCatalogDiff(diff);
    }
  }

  let viewportRefreshTimer = null;

  function setViewportSnapshot(snapshot) {
    const image = document.getElementById('viewport-snapshot-image');
    const placeholder = document.getElementById('viewport-snapshot-placeholder');
    if (!image || !snapshot || !snapshot.data_url) return;
    image.src = snapshot.data_url;
    image.hidden = false;
    if (placeholder) placeholder.hidden = true;
  }

  function refreshViewportSnapshot() {
    sketchupCall('refresh_viewport_snapshot');
  }

  function startViewportStream(interval) {
    sketchupCall('start_viewport_stream', JSON.stringify({ interval: interval || 1.0 }));
  }

  function stopViewportStream() {
    sketchupCall('stop_viewport_stream');
    stopViewportStreamFallback();
  }

  function startViewportStreamFallback(interval) {
    stopViewportStreamFallback();
    refreshViewportSnapshot();
    viewportRefreshTimer = setInterval(refreshViewportSnapshot, (interval || 1) * 1000);
  }

  function stopViewportStreamFallback() {
    if (viewportRefreshTimer) {
      clearInterval(viewportRefreshTimer);
      viewportRefreshTimer = null;
    }
  }

  window.geomora.startViewportStreamFallback = startViewportStreamFallback;
  window.geomora.stopViewportStreamFallback = stopViewportStreamFallback;

  let viewportStreamWanted = false;

  function pauseViewportStream() {
    const live = document.getElementById('viewport-live-stream');
    viewportStreamWanted = !!(live && live.checked);
    sketchupCall('pause_viewport_stream');
    stopViewportStreamFallback();
    if (live) live.checked = false;
  }

  function resumeViewportStream() {
    const live = document.getElementById('viewport-live-stream');
    if (live) live.checked = true;
    viewportStreamWanted = true;
    sketchupCall('resume_viewport_stream', JSON.stringify({ interval: 1.0 }));
  }

  function resumeViewportStreamIfWanted() {
    if (!viewportStreamWanted) return;
    resumeViewportStream();
  }

  window.geomora.pauseViewportStream = pauseViewportStream;
  window.geomora.resumeViewportStream = resumeViewportStream;

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
      pauseViewportStream();
    } else {
      resumeViewportStreamIfWanted();
    }
  });

  window.addEventListener('blur', function () {
    pauseViewportStream();
  });

  window.addEventListener('focus', function () {
    resumeViewportStreamIfWanted();
  });

  enhanceInspector();
  if (els.treeReviewOnly) els.treeReviewOnly.addEventListener('change', renderTree);

  document.getElementById('btn-pick-image').addEventListener('click', function () {
    sketchupCall('pick_image');
  });

  document.getElementById('btn-pick-video').addEventListener('click', function () {
    sketchupCall('pick_video');
  });

  document.getElementById('btn-pick-secondary').addEventListener('click', function () {
    sketchupCall('pick_secondary_image');
  });

  document.getElementById('btn-fuse-views').addEventListener('click', function () {
    if (!state.sourcePath) {
      setStatus('error', 'Load a primary image first.');
      return;
    }
    if (!state.secondarySourcePath) {
      setStatus('error', 'Load a secondary image first.');
      return;
    }
    sketchupCall('fuse_views', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-register-views').addEventListener('click', function () {
    if (!state.sourcePath) {
      setStatus('error', 'Load a primary image first.');
      return;
    }
    if (!state.secondarySourcePath) {
      setStatus('error', 'Load a secondary image first.');
      return;
    }
    sketchupCall('register_views', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-reset-corners').addEventListener('click', function () {
    resetCorners();
  });

  document.getElementById('btn-rectify').addEventListener('click', function () {
    if (state.activeView !== 'original') {
      setActiveView('original');
      setStatus(
        'warning',
        'Switched to Original — drag the four blue corner handles to frame the facade, then Rectify again.'
      );
      return;
    }
    if (!ensureDefaultCorners()) {
      setStatus('error', 'Image still loading — wait a moment, then drag corner handles before Rectify.');
      return;
    }
    sketchupCall('rectify', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-detect').addEventListener('click', function () {
    setWorkflowStage(1);
    if (!state.rectifiedImageUrl) {
      setStatus(
        'error',
        'Rectify Facade first (Original → drag corners → Rectify), then Detect Elements.'
      );
      return;
    }
    setStatus('', 'Analyzing facade structure, scale and architectural constraints…');
    sketchupCall('reconstruct', JSON.stringify(collectParams()));
  });

  if (els.btnExportYoloLabels) {
    els.btnExportYoloLabels.addEventListener('click', function () {
      if (!state.rectifiedImageUrl) {
        setStatus('error', 'Rectify the facade before exporting YOLO labels.');
        return;
      }
      sketchupCall('export_yolo_labels', JSON.stringify(collectYoloExportPayload()));
    });
  }

  document.getElementById('btn-load-template').addEventListener('click', function () {
    sketchupCall('load_template');
  });

  function shouldWarnBeforeRationalize() {
    if (state.windows.length < 2) {
      return null;
    }
    const sills = state.windows.map(function (win) {
      return Math.round((Number(win.sill_height) || 0) / 50);
    });
    const uniqueSills = {};
    sills.forEach(function (sill) {
      uniqueSills[sill] = true;
    });
    if (Object.keys(uniqueSills).length > 1) {
      return (
        'Multiple window rows detected (different sill heights).\n' +
        'Rationalize forces equal width/height and ONE horizontal row — it will destroy overlay positions.\n' +
        'For complex facades use Validate → Generate instead.'
      );
    }
    if (state.windows.length > 8) {
      return (
        'Many windows (' + state.windows.length + ').\n' +
        'Rationalize assumes a simple row of identical windows.\n' +
        'Continue only if this is a single-row facade.'
      );
    }
    return null;
  }

  document.getElementById('btn-rationalize').addEventListener('click', function () {
    if (!state.windows.length) {
      setStatus('error', 'Add at least one window before rationalizing.');
      return;
    }
    const warn = shouldWarnBeforeRationalize();
    if (warn) {
      const proceed = window.confirm(warn + '\n\nOK = rationalize anyway\nCancel = keep overlay positions');
      if (!proceed) {
        setStatus('', 'Rationalize cancelled — overlay positions kept.');
        return;
      }
    }
    sketchupCall('rationalize', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-solve-constraints').addEventListener('click', function () {
    if (!state.windows.length) {
      setStatus('error', 'Add at least one window before solving constraints.');
      return;
    }
    sketchupCall('solve_constraints', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-accept-observed').addEventListener('click', function () {
    reviewDecision('accepted_observed_geometry');
  });

  document.getElementById('btn-accept-adjusted').addEventListener('click', function () {
    reviewDecision('accepted_manual_adjustments');
  });

  document.getElementById('btn-retry-constraints').addEventListener('click', function () {
    reviewDecision('retry_constraints_requested');
    sketchupCall('solve_constraints', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-apply-pattern').addEventListener('click', function () {
    if (state.windows.length < 2) {
      setStatus('error', 'Add at least two windows before applying a pattern.');
      return;
    }
    sketchupCall('apply_pattern', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-validate').addEventListener('click', function () {
    sketchupCall('validate', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-generate').addEventListener('click', function () {
    if (requiresReconstructionReview() && !reconstructionReviewApproved()) {
      setStatus('error', 'Confirm the AI reconstruction result before generating the SketchUp model.');
      return;
    }
    if (state.windows.length > REVIEW_WINDOW_LIMIT) {
      setStatus(
        'error',
        'Too many windows (' + state.windows.length + '). Delete false boxes on the image, then Generate.'
      );
      return;
    }
    sketchupCall('generate', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-repair-geometry').addEventListener('click', function () {
    sketchupCall('repair_geometry', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-suggest-layout').addEventListener('click', function () {
    sketchupCall('suggest_room_layout', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-reload-catalog').addEventListener('click', function () {
    sketchupCall('reload_fixture_catalog', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-refresh-viewport').addEventListener('click', function () {
    refreshViewportSnapshot();
  });

  const viewportLiveStream = document.getElementById('viewport-live-stream');
  if (viewportLiveStream) {
    viewportLiveStream.addEventListener('change', function () {
      if (viewportLiveStream.checked) {
        startViewportStream(1.0);
      } else {
        stopViewportStream();
      }
    });
  }

  document.getElementById('btn-export-layout-report').addEventListener('click', function () {
    sketchupCall('export_layout_report', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-export-layout-pdf').addEventListener('click', function () {
    sketchupCall('export_layout_report_pdf', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-export-layout-booklet').addEventListener('click', function () {
    sketchupCall('export_layout_report_pdf_booklet', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-export-layout-booklet-html').addEventListener('click', function () {
    sketchupCall('export_layout_report_html_booklet', JSON.stringify(collectParams()));
  });

  els.btnDeleteSelected.addEventListener('click', function () {
    removeSelected();
  });

  els.btnDrawWindow.addEventListener('click', function () {
    setDrawMode(!state.drawMode);
  });

  if (els.showAiGuides) {
    els.showAiGuides.addEventListener('change', scheduleOverlayRender);
  }
  document.getElementById('btn-uncertainty-accept').addEventListener('click', function () {
    decideUncertainty('accepted_ai');
  });
  document.getElementById('btn-uncertainty-edit').addEventListener('click', editSelectedUncertainty);
  document.getElementById('btn-uncertainty-ignore').addEventListener('click', function () {
    decideUncertainty('ignored');
  });

  els.cornerSvg.addEventListener('mousedown', onCornerMouseDown);
  document.addEventListener('mousemove', onCornerMouseMove);
  document.addEventListener('mouseup', onCornerMouseUp);

  els.overlaySvg.addEventListener('mousedown', onOverlayMouseDown);
  document.addEventListener('mousemove', onOverlayMouseMove);
  document.addEventListener('mouseup', onOverlayMouseUp);

  els.image.addEventListener('load', function () {
    if (state.activeView === 'original' && state.originalImageUrl) {
      state.originalImageSize = {
        width: els.image.naturalWidth,
        height: els.image.naturalHeight
      };
      ensureDefaultCorners();
      renderCornerOverlay();
      updateViewerToolbar();
    } else {
      scheduleOverlayRender();
    }
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

  els.form.addEventListener('change', function (event) {
    const target = event.target;
    if (target && target.name === 'storey_count') {
      onStoreyCountChange();
      return;
    }
    if (target && target.name === 'repeat_openings') {
      onRepeatOpeningsChange();
      return;
    }
    renderTree();
  });

  document.addEventListener('DOMContentLoaded', function () {
    sketchupCall('ready');
  });
})();
