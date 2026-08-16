(function () {
  'use strict';

  const state = {
    rooms: [],
    activeRoomIndex: 0,
    drag: null
  };

  function initLayoutEditor(deps) {
    const canvas = document.getElementById('layout-editor-canvas');
    const roomSelect = document.getElementById('layout-editor-room');
    const panel = document.getElementById('layout-editor-panel');
    if (!canvas || !roomSelect || !panel) return;

    const ctx = canvas.getContext('2d');
    const openBtn = document.getElementById('btn-open-layout-editor');
    const syncBtn = document.getElementById('btn-sync-layout-field');
    const previewBtn = document.getElementById('btn-preview-catalog-diff');

    if (openBtn) {
      openBtn.addEventListener('click', function () {
        panel.hidden = !panel.hidden;
        if (!panel.hidden) {
          deps.requestPreview();
        }
      });
    }

    if (syncBtn) {
      syncBtn.addEventListener('click', function () {
        deps.syncLayoutField(serializeAllRooms());
        deps.setStatus('success', 'Room furniture layouts updated from editor.');
      });
    }

    if (previewBtn) {
      previewBtn.addEventListener('click', function () {
        deps.requestCatalogDiff();
      });
    }

    roomSelect.addEventListener('change', function () {
      state.activeRoomIndex = Number(roomSelect.value) || 0;
      render();
    });

    canvas.addEventListener('mousedown', function (event) {
      const hit = hitTest(event);
      if (!hit) return;
      state.drag = {
        itemIndex: hit.index,
        offsetX: hit.localX - hit.item.position[0],
        offsetY: hit.localY - hit.item.position[1]
      };
    });

    window.addEventListener('mousemove', function (event) {
      if (!state.drag) return;
      const room = currentRoom();
      if (!room) return;
      const point = canvasToModel(event, room);
      const item = room.items[state.drag.itemIndex];
      item.position = [
        Math.round(point.x - state.drag.offsetX),
        Math.round(point.y - state.drag.offsetY),
        0
      ];
      render();
    });

    window.addEventListener('mouseup', function () {
      state.drag = null;
    });

    function setPreview(rooms) {
      state.rooms = (rooms || []).map(function (room) {
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
              orientation: item.orientation || null
            };
          })
        };
      });
      state.activeRoomIndex = 0;
      roomSelect.innerHTML = '';
      state.rooms.forEach(function (room, index) {
        const option = document.createElement('option');
        option.value = String(index);
        option.textContent = room.name + ' (#' + room.room_number + ')';
        roomSelect.appendChild(option);
      });
      panel.hidden = false;
      render();
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

    function currentRoom() {
      return state.rooms[state.activeRoomIndex] || null;
    }

    function serializeAllRooms() {
      return state.rooms.map(function (room) {
        const items = room.items.map(function (item) {
          return serializeItem(item);
        }).join('|');
        return room.room_number + ':' + items;
      }).join(';');
    }

    function serializeItem(item) {
      let base = item.kind + '@' + Math.round(item.position[0]) + ',' + Math.round(item.position[1]);
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

      ctx.fillStyle = '#1f2430';
      ctx.strokeStyle = '#5f6b7c';
      ctx.lineWidth = 1;
      const roomWidth = (room.bounds.x_max - room.bounds.x_min) * scale;
      const roomHeight = (room.bounds.y_max - room.bounds.y_min) * scale;
      ctx.fillRect(offsetX, offsetY, roomWidth, roomHeight);
      ctx.strokeRect(offsetX, offsetY, roomWidth, roomHeight);

      room.items.forEach(function (item, index) {
        const x = offsetX + (item.position[0] - room.bounds.x_min) * scale;
        const y = offsetY + (item.position[1] - room.bounds.y_min) * scale;
        const w = item.width * scale;
        const h = item.depth * scale;
        ctx.fillStyle = index === (state.drag && state.drag.itemIndex) ? '#f28b82' : '#8ab4f8';
        ctx.fillRect(x, y, w, h);
        ctx.strokeStyle = '#202124';
        ctx.strokeRect(x, y, w, h);
        ctx.fillStyle = '#111';
        ctx.font = '10px sans-serif';
        ctx.fillText(item.kind, x + 4, y + 12);
      });
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
      setCatalogDiff: setCatalogDiff
    };
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (!window.geomoraLayoutBootstrap) return;
    initLayoutEditor(window.geomoraLayoutBootstrap);
  });
})();
