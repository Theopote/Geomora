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
    doorBbox: null
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

  function interactiveOverlayEnabled() {
    return (
      (state.activeView === 'rectified' || state.activeView === 'overlay') &&
      state.rectifiedImageUrl &&
      (state.windows.some(function (win) { return win.bbox_norm; }) || state.doorBbox)
    );
  }

  function renderDetectionOverlay() {
    const svg = els.overlaySvg;
    if (!interactiveOverlayEnabled() || !els.image.complete || !els.image.naturalWidth) {
      svg.innerHTML = '';
      return;
    }

    const nw = els.image.naturalWidth;
    const nh = els.image.naturalHeight;
    svg.setAttribute('viewBox', '0 0 ' + nw + ' ' + nh);

    let markup = '';
    state.windows.forEach(function (win, index) {
      if (!win.bbox_norm || win.bbox_norm.length !== 4) return;
      const x1 = win.bbox_norm[0] * nw;
      const y1 = win.bbox_norm[1] * nh;
      const w = (win.bbox_norm[2] - win.bbox_norm[0]) * nw;
      const h = (win.bbox_norm[3] - win.bbox_norm[1]) * nh;
      const selected = state.selectedWindowIndex === index;
      markup +=
        '<rect class="det-box' + (selected ? ' selected' : '') + '" data-kind="window" data-index="' + index +
        '" x="' + x1 + '" y="' + y1 + '" width="' + w + '" height="' + h + '" />' +
        '<text class="det-label" x="' + (x1 + 4) + '" y="' + (y1 + 16) + '">' + (index + 1) + '</text>';
    });

    const doorWidth = Number(els.form.elements.namedItem('door_width').value) || 0;
    if (state.doorBbox && state.doorBbox.length === 4 && doorWidth > 0) {
      const x1 = state.doorBbox[0] * nw;
      const y1 = state.doorBbox[1] * nh;
      const w = (state.doorBbox[2] - state.doorBbox[0]) * nw;
      const h = (state.doorBbox[3] - state.doorBbox[1]) * nh;
      const selected = state.selectedDoor;
      markup +=
        '<rect class="det-box door' + (selected ? ' selected' : '') + '" data-kind="door" x="' +
        x1 + '" y="' + y1 + '" width="' + w + '" height="' + h + '" />' +
        '<text class="det-label" x="' + (x1 + 4) + '" y="' + (y1 + 16) + '">D</text>';
    }

    svg.innerHTML = markup;
    svg.querySelectorAll('.det-box').forEach(function (box) {
      box.addEventListener('click', onOverlayBoxClick);
    });
  }

  function onOverlayBoxClick(event) {
    event.stopPropagation();
    const kind = event.target.getAttribute('data-kind');
    if (kind === 'door') {
      selectDoor();
    } else {
      const index = parseInt(event.target.getAttribute('data-index'), 10);
      if (!Number.isNaN(index)) {
        selectWindow(index);
      }
    }
  }

  function updateViewerToolbar() {
    const enabled = interactiveOverlayEnabled();
    els.viewerToolbar.hidden = !enabled;
    if (enabled) {
      els.viewerHint.textContent = 'Click a box to select · Del or button to remove';
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
        els.placeholder.textContent = 'Run Detect Elements to see interactive boxes';
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

  els.image.addEventListener('load', function () {
    renderDetectionOverlay();
  });

  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Delete' && event.key !== 'Backspace') return;
    const tag = (event.target && event.target.tagName) || '';
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    if (!interactiveOverlayEnabled()) return;
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
