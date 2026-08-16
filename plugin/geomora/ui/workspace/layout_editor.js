(function () {
  'use strict';

  const GRID_MM = 100;
  const MAGNET_MM = 80;
  const WALL_INSET = 600;

  const state = {
    storeys: [],
    activeStoreyIndex: 0,
    activeRoomIndex: 0,
    palette: [],
    paletteFilter: '',
    drag: null,
    paletteDrag: null,
    selectedItemIndex: null,
    snapGrid: true,
    wallMagnet: true
  };

  function initLayoutEditor(deps) {
    const canvas = document.getElementById('layout-editor-canvas');
    const canvas3d = document.getElementById('layout-preview-3d-canvas');
    const roomSelect = document.getElementById('layout-editor-room');
    const storeySelect = document.getElementById('layout-editor-storey');
    const panel = document.getElementById('layout-editor-panel');
    const paletteEl = document.getElementById('layout-catalog-palette');
    const paletteSearch = document.getElementById('layout-palette-search');
    const itemSizePanel = document.getElementById('layout-item-size');
    const snapGridInput = document.getElementById('layout-snap-grid');
    const wallMagnetInput = document.getElementById('layout-wall-magnet');
    if (!canvas || !roomSelect || !panel) return;

    const ctx = canvas.getContext('2d');
    const ctx3d = canvas3d ? canvas3d.getContext('2d') : null;
    const openBtn = document.getElementById('btn-open-layout-editor');
    const syncBtn = document.getElementById('btn-sync-layout-field');
    const previewBtn = document.getElementById('btn-preview-catalog-diff');
    const rotateBtn = document.getElementById('btn-rotate-selected');
    const applySizeBtn = document.getElementById('btn-apply-item-size');
    const widthInput = document.getElementById('layout-item-width');
    const depthInput = document.getElementById('layout-item-depth');
    const heightInput = document.getElementById('layout-item-height');

    if (snapGridInput) {
      snapGridInput.addEventListener('change', function () {
        state.snapGrid = snapGridInput.checked;
      });
    }
    if (wallMagnetInput) {
      wallMagnetInput.addEventListener('change', function () {
        state.wallMagnet = wallMagnetInput.checked;
      });
    }

    if (openBtn) {
      openBtn.addEventListener('click', function () {
        panel.hidden = !panel.hidden;
        if (!panel.hidden) {
          deps.requestPreview();
          deps.requestPalette();
        }
      });
    }

    if (syncBtn) {
      syncBtn.addEventListener('click', function () {
        deps.syncLayoutField(serializeAllStoreys());
        deps.setStatus('success', 'Room furniture layouts updated from editor.');
      });
    }

    if (previewBtn) {
      previewBtn.addEventListener('click', function () {
        deps.requestCatalogDiff();
      });
    }

    if (paletteSearch) {
      paletteSearch.addEventListener('input', function () {
        state.paletteFilter = paletteSearch.value.trim().toLowerCase();
        renderPalette();
      });
    }

    if (applySizeBtn) {
      applySizeBtn.addEventListener('click', function () {
        const item = getSelectedItem();
        if (!item) return;
        item.width = Number(widthInput.value) || item.width;
        item.depth = Number(depthInput.value) || item.depth;
        item.height = Number(heightInput.value) || item.height;
        item.customSize = true;
        render();
        render3d();
      });
    }

    if (rotateBtn) {
      rotateBtn.addEventListener('click', function () {
        const item = getSelectedItem();
        if (!item) return;
        item.rotation = ((item.rotation || 0) + 90) % 360;
        render();
        render3d();
      });
    }

    if (storeySelect) {
      storeySelect.addEventListener('change', function () {
        state.activeStoreyIndex = Number(storeySelect.value) || 0;
        state.activeRoomIndex = 0;
        state.selectedItemIndex = null;
        rebuildRoomSelect();
        updateItemSizePanel();
        render();
        render3d();
      });
    }

    roomSelect.addEventListener('change', function () {
      state.activeRoomIndex = Number(roomSelect.value) || 0;
      state.selectedItemIndex = null;
      updateItemSizePanel();
      render();
      render3d();
    });

    canvas.addEventListener('mousedown', function (event) {
      const hit = hitTest(event);
      if (!hit) {
        state.selectedItemIndex = null;
        updateItemSizePanel();
        render();
        return;
      }
      state.selectedItemIndex = hit.index;
      state.drag = {
        itemIndex: hit.index,
        offsetX: hit.localX - hit.item.position[0],
        offsetY: hit.localY - hit.item.position[1]
      };
      updateItemSizePanel();
      render();
    });

    canvas.addEventListener('dragover', function (event) {
      if (!state.paletteDrag) return;
      event.preventDefault();
    });

    canvas.addEventListener('drop', function (event) {
      event.preventDefault();
      if (!state.paletteDrag) return;
      const room = currentRoom();
      if (!room) return;
      const point = canvasToModel(event, room);
      const snapped = applySnap(point.x, point.y, room, state.paletteDrag);
      const item = {
        kind: state.paletteDrag.kind,
        width: state.paletteDrag.width,
        depth: state.paletteDrag.depth,
        height: state.paletteDrag.height,
        position: [snapped[0], snapped[1], 0],
        rotation: 0
      };
      room.items.push(item);
      state.selectedItemIndex = room.items.length - 1;
      state.paletteDrag = null;
      updateItemSizePanel();
      render();
      render3d();
    });

    window.addEventListener('mousemove', function (event) {
      if (!state.drag) return;
      const room = currentRoom();
      if (!room) return;
      const point = canvasToModel(event, room);
      const item = room.items[state.drag.itemIndex];
      const snapped = applySnap(
        point.x - state.drag.offsetX,
        point.y - state.drag.offsetY,
        room,
        item
      );
      item.position = [snapped[0], snapped[1], 0];
      render();
      render3d();
    });

    window.addEventListener('mouseup', function () {
      state.drag = null;
    });

    function setPreview(storeys) {
      const payload = normalizeStoreys(storeys);
      state.storeys = payload;
      state.activeStoreyIndex = 0;
      state.activeRoomIndex = 0;
      state.selectedItemIndex = null;
      rebuildStoreySelect();
      rebuildRoomSelect();
      panel.hidden = false;
      updateItemSizePanel();
      render();
      render3d();
    }

    function setPalette(items) {
      state.palette = items || [];
      renderPalette();
    }

    function renderPalette() {
      if (!paletteEl) return;
      paletteEl.innerHTML = '';
      const filter = state.paletteFilter;
      state.palette.forEach(function (entry) {
        const label = (entry.label || entry.kind || '').toLowerCase();
        const kind = (entry.kind || '').toLowerCase();
        if (filter && label.indexOf(filter) === -1 && kind.indexOf(filter) === -1) return;

        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'layout-palette-chip';
        chip.textContent = entry.label || entry.kind;
        chip.title = entry.kind + ' (' + entry.width + 'x' + entry.depth + ' mm)';
        chip.draggable = true;
        chip.addEventListener('dragstart', function () {
          state.paletteDrag = {
            kind: entry.kind,
            width: Number(entry.width),
            depth: Number(entry.depth),
            height: Number(entry.height)
          };
        });
        chip.addEventListener('dragend', function () {
          state.paletteDrag = null;
        });
        chip.addEventListener('click', function () {
          const room = currentRoom();
          if (!room) return;
          const snapped = applySnap(600, 600, room, {
            width: Number(entry.width),
            depth: Number(entry.depth)
          });
          const item = {
            kind: entry.kind,
            width: Number(entry.width),
            depth: Number(entry.depth),
            height: Number(entry.height),
            position: [snapped[0], snapped[1], 0],
            rotation: 0
          };
          room.items.push(item);
          state.selectedItemIndex = room.items.length - 1;
          updateItemSizePanel();
          render();
          render3d();
        });
        paletteEl.appendChild(chip);
      });
    }

    function normalizeStoreys(storeys) {
      if (!storeys) return [];
      if (storeys.storeys) return normalizeStoreys(storeys.storeys);
      if (storeys.rooms) {
        return [{
          storey_index: storeys.storey_index || 0,
          label: storeys.label || 'Ground',
          rooms: storeys.rooms
        }];
      }
      if (storeys.length && storeys[0].rooms) {
        return storeys.map(function (storey) {
          return {
            storey_index: storey.storey_index || 0,
            label: storey.label || 'Ground',
            rooms: (storey.rooms || []).map(normalizeRoom)
          };
        });
      }
      return [{
        storey_index: 0,
        label: 'Ground',
        rooms: (storeys || []).map(normalizeRoom)
      }];
    }

    function normalizeRoom(room) {
      return {
        room_number: room.room_number,
        name: room.name,
        bounds: room.bounds,
        items: (room.items || []).map(function (item) {
          return {
            kind: item.kind,
            width: Number(item.width),
            depth: Number(item.depth),
            height: Number(item.height),
            position: [
              Number((item.position || [0, 0, 0])[0]),
              Number((item.position || [0, 0, 0])[1]),
              0
            ],
            rotation: item.rotation ? Number(item.rotation) : null,
            orientation: item.orientation || null,
            customSize: !!item.customSize
          };
        })
      };
    }

    function setCatalogDiff(diff) {
      const el = document.getElementById('catalog-diff-preview');
      if (!el || !diff) return;
      const parts = [];
      if (diff.summary) parts.push(diff.summary);
      if (diff.added_sets && diff.added_sets.length) parts.push('Added: ' + diff.added_sets.join(', '));
      if (diff.removed_sets && diff.removed_sets.length) parts.push('Removed: ' + diff.removed_sets.join(', '));
      if (diff.changed_sets && diff.changed_sets.length) parts.push('Changed: ' + diff.changed_sets.join(', '));
      el.textContent = parts.join(' · ') || 'No catalog changes';
    }

    function currentStorey() {
      return state.storeys[state.activeStoreyIndex] || null;
    }

    function currentRoom() {
      const storey = currentStorey();
      if (!storey) return null;
      return storey.rooms[state.activeRoomIndex] || null;
    }

    function getSelectedItem() {
      const room = currentRoom();
      if (!room || state.selectedItemIndex === null) return null;
      return room.items[state.selectedItemIndex] || null;
    }

    function updateItemSizePanel() {
      if (!itemSizePanel) return;
      const item = getSelectedItem();
      if (!item) {
        itemSizePanel.hidden = true;
        return;
      }
      itemSizePanel.hidden = false;
      if (widthInput) widthInput.value = Math.round(item.width);
      if (depthInput) depthInput.value = Math.round(item.depth);
      if (heightInput) heightInput.value = Math.round(item.height);
    }

    function applySnap(x, y, room, item) {
      let sx = x;
      let sy = y;
      if (state.snapGrid) {
        sx = Math.round(sx / GRID_MM) * GRID_MM;
        sy = Math.round(sy / GRID_MM) * GRID_MM;
      }
      if (state.wallMagnet && room && item) {
        const bounds = room.bounds;
        const width = item.width || 0;
        const depth = item.depth || 0;
        const magnets = [
          { x: bounds.x_min + WALL_INSET, y: sy, dist: Math.abs(sx - (bounds.x_min + WALL_INSET)) },
          { x: bounds.x_max - WALL_INSET - width, y: sy, dist: Math.abs(sx - (bounds.x_max - WALL_INSET - width)) },
          { x: sx, y: bounds.y_min + WALL_INSET, dist: Math.abs(sy - (bounds.y_min + WALL_INSET)) },
          { x: sx, y: bounds.y_max - WALL_INSET - depth, dist: Math.abs(sy - (bounds.y_max - WALL_INSET - depth)) }
        ];
        const best = magnets.sort(function (a, b) { return a.dist - b.dist; })[0];
        if (best.dist <= MAGNET_MM) {
          sx = best.x;
          sy = best.y;
        }
      }
      return [Math.round(sx), Math.round(sy)];
    }

    function rebuildStoreySelect() {
      if (!storeySelect) return;
      storeySelect.innerHTML = '';
      state.storeys.forEach(function (storey, index) {
        const option = document.createElement('option');
        option.value = String(index);
        option.textContent = storey.label || ('Floor ' + (index + 1));
        storeySelect.appendChild(option);
      });
      storeySelect.hidden = state.storeys.length <= 1;
      storeySelect.value = String(state.activeStoreyIndex);
    }

    function rebuildRoomSelect() {
      const storey = currentStorey();
      roomSelect.innerHTML = '';
      (storey ? storey.rooms : []).forEach(function (room, index) {
        const option = document.createElement('option');
        option.value = String(index);
        option.textContent = room.name + ' (#' + room.room_number + ')';
        roomSelect.appendChild(option);
      });
      roomSelect.value = String(state.activeRoomIndex);
    }

    function serializeAllStoreys() {
      return state.storeys.map(function (storey) {
        const prefix = storey.storey_index > 0 ? 's' + (storey.storey_index + 1) + ':' : '';
        return (storey.rooms || []).map(function (room) {
          const items = room.items.map(serializeItem).join('|');
          return prefix + room.room_number + ':' + items;
        }).join(';');
      }).join(';');
    }

    function serializeItem(item) {
      let base = item.kind + '@' + Math.round(item.position[0]) + ',' + Math.round(item.position[1]);
      if (item.customSize) {
        base += ',' + Math.round(item.width) + 'x' + Math.round(item.depth) + 'x' + Math.round(item.height);
      }
      if (item.rotation) base += '@' + item.rotation;
      return base;
    }

    function render() {
      const room = currentRoom();
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (!room) return;
      const scale = fitScale(room.bounds, canvas.width - 24, canvas.height - 24);
      const offsetX = 12;
      const offsetY = 12;

      if (state.snapGrid) {
        drawGrid(ctx, room, scale, offsetX, offsetY);
      }

      ctx.fillStyle = '#1f2430';
      ctx.strokeStyle = '#5f6b7c';
      ctx.lineWidth = 1;
      const roomWidth = (room.bounds.x_max - room.bounds.x_min) * scale;
      const roomHeight = (room.bounds.y_max - room.bounds.y_min) * scale;
      ctx.fillRect(offsetX, offsetY, roomWidth, roomHeight);
      ctx.strokeRect(offsetX, offsetY, roomWidth, roomHeight);

      room.items.forEach(function (item, index) {
        drawPlanItem(
          ctx,
          item,
          room,
          scale,
          offsetX,
          offsetY,
          index === state.selectedItemIndex || index === (state.drag && state.drag.itemIndex)
        );
      });
    }

    function drawGrid(ctx2d, room, scale, offsetX, offsetY) {
      ctx2d.strokeStyle = 'rgba(255,255,255,0.06)';
      ctx2d.lineWidth = 1;
      for (let x = room.bounds.x_min; x <= room.bounds.x_max; x += GRID_MM) {
        const px = offsetX + (x - room.bounds.x_min) * scale;
        ctx2d.beginPath();
        ctx2d.moveTo(px, offsetY);
        ctx2d.lineTo(px, offsetY + (room.bounds.y_max - room.bounds.y_min) * scale);
        ctx2d.stroke();
      }
      for (let y = room.bounds.y_min; y <= room.bounds.y_max; y += GRID_MM) {
        const py = offsetY + (y - room.bounds.y_min) * scale;
        ctx2d.beginPath();
        ctx2d.moveTo(offsetX, py);
        ctx2d.lineTo(offsetX + (room.bounds.x_max - room.bounds.x_min) * scale, py);
        ctx2d.stroke();
      }
    }

    function drawPlanItem(ctx2d, item, room, scale, offsetX, offsetY, selected) {
      const x = offsetX + (item.position[0] - room.bounds.x_min) * scale;
      const y = offsetY + (item.position[1] - room.bounds.y_min) * scale;
      const w = item.width * scale;
      const h = item.depth * scale;
      ctx2d.save();
      if (item.rotation) {
        ctx2d.translate(x + w / 2, y + h / 2);
        ctx2d.rotate((item.rotation * Math.PI) / 180);
        ctx2d.translate(-(x + w / 2), -(y + h / 2));
      }
      ctx2d.fillStyle = selected ? '#f28b82' : '#8ab4f8';
      ctx2d.fillRect(x, y, w, h);
      ctx2d.strokeStyle = '#202124';
      ctx2d.strokeRect(x, y, w, h);
      ctx2d.fillStyle = '#111';
      ctx2d.font = '10px sans-serif';
      ctx2d.fillText(item.kind, x + 4, y + 12);
      ctx2d.restore();
    }

    function render3d() {
      if (!ctx3d || !canvas3d) return;
      const room = currentRoom();
      ctx3d.clearRect(0, 0, canvas3d.width, canvas3d.height);
      if (!room) return;

      const scale = fitScale(room.bounds, canvas3d.width - 40, canvas3d.height - 40) * 0.7;
      const originX = canvas3d.width / 2;
      const originY = canvas3d.height - 24;
      drawIsoFloor(ctx3d, room, scale, originX, originY);
      room.items.forEach(function (item) {
        drawIsoBox(ctx3d, item, room, scale, originX, originY);
      });
    }

    function drawIsoFloor(ctx2d, room, scale, originX, originY) {
      const w = (room.bounds.x_max - room.bounds.x_min) * scale;
      const d = (room.bounds.y_max - room.bounds.y_min) * scale;
      const points = isoPoints(0, 0, w, d, originX, originY);
      ctx2d.beginPath();
      ctx2d.moveTo(points[0].x, points[0].y);
      points.slice(1).forEach(function (point) { ctx2d.lineTo(point.x, point.y); });
      ctx2d.closePath();
      ctx2d.fillStyle = '#2a3140';
      ctx2d.fill();
      ctx2d.strokeStyle = '#6f7b8c';
      ctx2d.stroke();
    }

    function drawIsoBox(ctx2d, item, room, scale, originX, originY) {
      const x = (item.position[0] - room.bounds.x_min) * scale;
      const y = (item.position[1] - room.bounds.y_min) * scale;
      const w = item.width * scale;
      const d = item.depth * scale;
      const h = Math.max(8, (item.height / 3000) * 60);
      const base = isoPoints(x, y, w, d, originX, originY);
      const top = base.map(function (point) { return { x: point.x, y: point.y - h }; });
      drawIsoFace(ctx2d, base[0], base[1], top[1], top[0], '#6f9be0');
      drawIsoFace(ctx2d, base[1], base[2], top[2], top[1], '#4f7ec4');
      drawIsoFace(ctx2d, base[0], base[1], base[2], base[3], '#8ab4f8', true);
      drawIsoFace(ctx2d, top[0], top[1], top[2], top[3], '#a8c7fa', true);
    }

    function drawIsoFace(ctx2d, a, b, c, d, color, top) {
      ctx2d.beginPath();
      ctx2d.moveTo(a.x, a.y);
      ctx2d.lineTo(b.x, b.y);
      ctx2d.lineTo(c.x, c.y);
      ctx2d.lineTo(d.x, d.y);
      ctx2d.closePath();
      ctx2d.fillStyle = color;
      ctx2d.fill();
      if (top) ctx2d.stroke();
    }

    function isoPoints(x, y, w, d, originX, originY) {
      return [
        { x: originX + x - y, y: originY - ((x + y) * 0.5) },
        { x: originX + x + w - y, y: originY - ((x + w + y) * 0.5) },
        { x: originX + x + w - y - d, y: originY - ((x + w + y + d) * 0.5) },
        { x: originX + x - y - d, y: originY - ((x + y + d) * 0.5) }
      ];
    }

    function fitScale(bounds, maxWidth, maxHeight) {
      const width = bounds.x_max - bounds.x_min;
      const height = bounds.y_max - bounds.y_min;
      return Math.min(maxWidth / width, maxHeight / height);
    }

    function canvasToModel(event, room) {
      const rect = canvas.getBoundingClientRect();
      const scale = fitScale(room.bounds, canvas.width - 24, canvas.height - 24);
      const offsetX = 12;
      const offsetY = 12;
      const x = ((event.clientX - rect.left) - offsetX) / scale + room.bounds.x_min;
      const y = ((event.clientY - rect.top) - offsetY) / scale + room.bounds.y_min;
      return { x: x, y: y };
    }

    function hitTest(event) {
      const room = currentRoom();
      if (!room) return null;
      const point = canvasToModel(event, room);
      for (let index = room.items.length - 1; index >= 0; index -= 1) {
        const item = room.items[index];
        const left = item.position[0];
        const top = item.position[1];
        if (
          point.x >= left &&
          point.x <= left + item.width &&
          point.y >= top &&
          point.y <= top + item.depth
        ) {
          return { index: index, item: item, localX: point.x, localY: point.y };
        }
      }
      return null;
    }

    window.geomoraLayoutEditor = {
      setPreview: setPreview,
      setPalette: setPalette,
      setCatalogDiff: setCatalogDiff
    };
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (!window.geomoraLayoutBootstrap) return;
    initLayoutEditor(window.geomoraLayoutBootstrap);
  });
})();
