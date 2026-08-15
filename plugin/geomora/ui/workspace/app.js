(function () {
  const state = {
    sourcePath: null,
    sourceId: null,
    windows: []
  };

  const els = {
    status: document.getElementById('status'),
    sourceMeta: document.getElementById('source-meta'),
    image: document.getElementById('reference-image'),
    placeholder: document.getElementById('viewer-placeholder'),
    tree: document.getElementById('element-tree'),
    form: document.getElementById('facade-form'),
    windowsContainer: document.getElementById('windows-container')
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

  function renderWindows(windows) {
    state.windows = windows || [];
    els.windowsContainer.innerHTML = '';

    state.windows.forEach(function (win, index) {
      const row = document.createElement('div');
      row.className = 'window-row';
      row.innerHTML =
        '<h3>Window ' + (index + 1) + '</h3>' +
        '<label>Offset (mm)<input data-win="' + index + '" data-field="offset" type="number" step="1" value="' + win.offset + '"></label>' +
        '<label>Width (mm)<input data-win="' + index + '" data-field="width" type="number" step="1" value="' + win.width + '"></label>' +
        '<label>Height (mm)<input data-win="' + index + '" data-field="height" type="number" step="1" value="' + win.height + '"></label>' +
        '<label>Sill height (mm)<input data-win="' + index + '" data-field="sill_height" type="number" step="1" value="' + win.sill_height + '"></label>';
      els.windowsContainer.appendChild(row);
    });

    els.windowsContainer.querySelectorAll('input').forEach(function (input) {
      input.addEventListener('change', onWindowFieldChange);
    });

    renderTree();
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

  function loadPayload(payload) {
    els.form.elements.namedItem('project_name').value = payload.project_name || 'Manual Facade';
    els.form.elements.namedItem('wall_length').value = payload.wall_length || 10000;
    els.form.elements.namedItem('wall_height').value = payload.wall_height || 3300;
    els.form.elements.namedItem('wall_thickness').value = payload.wall_thickness || 240;

    renderWindows(payload.windows || []);

    const door = payload.door || {};
    els.form.elements.namedItem('door_offset').value = door.offset || 8500;
    els.form.elements.namedItem('door_width').value = door.width || 900;
    els.form.elements.namedItem('door_height').value = door.height || 2100;

    if (payload.source_path) {
      setImage('file:///' + payload.source_path.replace(/\\/g, '/'), payload.source_path);
    }

    if (payload.ir_preview) {
      setIrPreview(payload.ir_preview);
    }

    renderTree();
    setStatus('', 'Template loaded');
  }

  function setImage(fileUrl, sourcePath) {
    state.sourcePath = sourcePath;
    state.sourceId = sourcePath ? 'source_image_001' : null;
    els.image.src = fileUrl;
    els.image.hidden = false;
    els.placeholder.hidden = true;
    els.sourceMeta.textContent = sourcePath || 'Image loaded';
    renderTree();
  }

  function setIrPreview(ir) {
    if (!ir || !ir.openings) return;
    renderTree();
  }

  window.geomora = {
    loadPayload: loadPayload,
    setImage: setImage,
    setIrPreview: setIrPreview,
    setStatus: setStatus
  };

  document.getElementById('btn-pick-image').addEventListener('click', function () {
    sketchupCall('pick_image');
  });

  document.getElementById('btn-load-template').addEventListener('click', function () {
    sketchupCall('load_template');
  });

  document.getElementById('btn-validate').addEventListener('click', function () {
    sketchupCall('validate', JSON.stringify(collectParams()));
  });

  document.getElementById('btn-generate').addEventListener('click', function () {
    sketchupCall('generate', JSON.stringify(collectParams()));
  });

  els.form.addEventListener('change', renderTree);

  document.addEventListener('DOMContentLoaded', function () {
    sketchupCall('ready');
  });
})();
