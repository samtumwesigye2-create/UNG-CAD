/*
 * UNG-CAD slice preview viewer (self-contained, no dependencies).
 *
 *   const viewer = UNGPreview.mount(document.getElementById('slice-preview'));
 *   const data = await UNGPreview.fetchPreview(formData);   // POST /api/manufacturing/preview
 *   viewer.setData(data);
 *
 * Shows: a top view of one layer (layer slider, colours by path type, optional
 * ghost of the layer below) and a cross-section (X-Z or Y-Z cut at an adjustable
 * position) so internal walls, infill and hollow cavities are visible.
 */
(function (root) {
  'use strict';

  var COLORS = {
    perimeter: '#ef4444',
    infill: '#22c55e',
    solid: '#3b82f6',
    travel: '#94a3b8'
  };

  function boundsOf(data) {
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity, maxZ = 0;
    data.layers.forEach(function (layer) {
      maxZ = Math.max(maxZ, layer.z);
      layer.paths.forEach(function (p) {
        if (p.type === 'travel') {
          return;
        }
        p.points.forEach(function (pt) {
          minX = Math.min(minX, pt[0]);
          maxX = Math.max(maxX, pt[0]);
          minY = Math.min(minY, pt[1]);
          maxY = Math.max(maxY, pt[1]);
        });
      });
    });
    if (!isFinite(minX)) {
      minX = minY = -10;
      maxX = maxY = 10;
    }
    return { minX: minX, minY: minY, maxX: maxX, maxY: maxY, maxZ: maxZ };
  }

  /*
   * Cross-section: every extrusion segment that crosses the cut plane becomes a
   * small rectangle (line width x layer thickness) at (along, z).
   * axis 'y' = cut at Y=pos, showing X horizontally (X-Z view); axis 'x' = cut at X=pos (Y-Z view).
   */
  function crossSection(data, axis, pos) {
    var lw = data.line_width || 0.45;
    var cells = [];
    var a = axis === 'x' ? 0 : 1;   // coordinate compared with the plane
    var b = axis === 'x' ? 1 : 0;   // coordinate drawn horizontally
    data.layers.forEach(function (layer) {
      layer.paths.forEach(function (p) {
        if (p.type === 'travel') {
          return;
        }
        for (var i = 1; i < p.points.length; i++) {
          var p0 = p.points[i - 1], p1 = p.points[i];
          var d0 = p0[a] - pos, d1 = p1[a] - pos;
          if (Math.abs(d0) < lw / 2 && Math.abs(d1) < lw / 2) {
            // segment runs along the plane: draw its whole span
            cells.push({ from: Math.min(p0[b], p1[b]) - lw / 2, to: Math.max(p0[b], p1[b]) + lw / 2,
                         z: layer.z, h: layer.thickness, type: p.type });
          } else if (d0 * d1 <= 0 && d0 !== d1) {
            var t = d0 / (d0 - d1);
            var c = p0[b] + t * (p1[b] - p0[b]);
            cells.push({ from: c - lw / 2, to: c + lw / 2, z: layer.z, h: layer.thickness, type: p.type });
          }
        }
      });
    });
    return cells;
  }

  function el(tag, attrs, text) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      e.setAttribute(k, attrs[k]);
    });
    if (text) {
      e.textContent = text;
    }
    return e;
  }

  function mount(container, opts) {
    opts = opts || {};
    var size = opts.size || 420;
    var state = { data: null, bounds: null, layer: 0, axis: 'y', pos: 0, ghost: true,
                  show: { perimeter: true, infill: true, solid: true, travel: false } };

    container.innerHTML = '';
    container.classList.add('ung-preview');
    var controls = el('div', { 'class': 'ung-preview-controls' });
    var layerLabel = el('span', {}, 'Layer');
    var layerSlider = el('input', { type: 'range', min: '0', max: '0', value: '0', step: '1' });
    var axisSel = el('select', {});
    axisSel.appendChild(el('option', { value: 'y' }, 'Cut X-Z (at Y)'));
    axisSel.appendChild(el('option', { value: 'x' }, 'Cut Y-Z (at X)'));
    var posSlider = el('input', { type: 'range', min: '0', max: '1000', value: '500', step: '1' });
    var ghostBox = el('input', { type: 'checkbox' });
    ghostBox.checked = true;
    controls.appendChild(layerLabel);
    controls.appendChild(layerSlider);
    controls.appendChild(axisSel);
    controls.appendChild(posSlider);
    var ghostLabel = el('label', {}, ' ghost layer below ');
    ghostLabel.prepend(ghostBox);
    controls.appendChild(ghostLabel);
    Object.keys(state.show).forEach(function (type) {
      var box = el('input', { type: 'checkbox' });
      box.checked = state.show[type];
      box.addEventListener('change', function () {
        state.show[type] = box.checked;
        render();
      });
      var lab = el('label', { style: 'color:' + COLORS[type] + ';margin-left:6px' }, ' ' + type);
      lab.prepend(box);
      controls.appendChild(lab);
    });
    var info = el('div', { 'class': 'ung-preview-info', style: 'font:12px monospace;margin:4px 0' });
    var views = el('div', { style: 'display:flex;flex-wrap:wrap;gap:8px' });
    var top = el('canvas', { width: String(size), height: String(size), style: 'background:#0f172a;border-radius:6px' });
    var side = el('canvas', { width: String(size), height: String(size), style: 'background:#0f172a;border-radius:6px' });
    views.appendChild(top);
    views.appendChild(side);
    var warnings = el('ul', { 'class': 'ung-preview-warnings', style: 'font:12px sans-serif;color:#f59e0b' });
    container.appendChild(controls);
    container.appendChild(info);
    container.appendChild(views);
    container.appendChild(warnings);

    layerSlider.addEventListener('input', function () {
      state.layer = parseInt(layerSlider.value, 10) || 0;
      render();
    });
    axisSel.addEventListener('change', function () {
      state.axis = axisSel.value;
      updatePos();
      render();
    });
    posSlider.addEventListener('input', function () {
      updatePos();
      render();
    });
    ghostBox.addEventListener('change', function () {
      state.ghost = ghostBox.checked;
      render();
    });

    function updatePos() {
      if (!state.bounds) {
        return;
      }
      var lo = state.axis === 'x' ? state.bounds.minX : state.bounds.minY;
      var hi = state.axis === 'x' ? state.bounds.maxX : state.bounds.maxY;
      state.pos = lo + (hi - lo) * (parseInt(posSlider.value, 10) / 1000);
    }

    function topTransform() {
      var b = state.bounds;
      var pad = 10;
      var span = Math.max(b.maxX - b.minX, b.maxY - b.minY) || 1;
      var s = (size - 2 * pad) / span;
      return function (x, y) {
        return [pad + (x - b.minX) * s, size - pad - (y - b.minY) * s];
      };
    }

    function drawLayer(ctx, layer, tf, alpha) {
      layer.paths.forEach(function (p) {
        if (!state.show[p.type]) {
          return;
        }
        ctx.globalAlpha = alpha * (p.type === 'travel' ? 0.6 : 1);
        ctx.strokeStyle = COLORS[p.type] || '#fff';
        ctx.lineWidth = p.type === 'travel' ? 0.5 : 1.2;
        ctx.beginPath();
        p.points.forEach(function (pt, i) {
          var q = tf(pt[0], pt[1]);
          if (i === 0) {
            ctx.moveTo(q[0], q[1]);
          } else {
            ctx.lineTo(q[0], q[1]);
          }
        });
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    }

    function renderTop() {
      var ctx = top.getContext('2d');
      ctx.clearRect(0, 0, size, size);
      var tf = topTransform();
      var layers = state.data.layers;
      if (state.ghost && state.layer > 0) {
        drawLayer(ctx, layers[state.layer - 1], tf, 0.2);
      }
      drawLayer(ctx, layers[state.layer], tf, 1);
      // cut plane marker
      var b = state.bounds;
      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = '#facc15';
      ctx.beginPath();
      var p0 = state.axis === 'x' ? tf(state.pos, b.minY) : tf(b.minX, state.pos);
      var p1 = state.axis === 'x' ? tf(state.pos, b.maxY) : tf(b.maxX, state.pos);
      ctx.moveTo(p0[0], p0[1]);
      ctx.lineTo(p1[0], p1[1]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    function renderSide() {
      var ctx = side.getContext('2d');
      ctx.clearRect(0, 0, size, size);
      var b = state.bounds;
      var lo = state.axis === 'x' ? b.minY : b.minX;
      var hi = state.axis === 'x' ? b.maxY : b.maxX;
      var pad = 10;
      var span = Math.max(hi - lo, b.maxZ) || 1;
      var s = (size - 2 * pad) / span;
      var currentZ = state.data.layers[state.layer].z;
      crossSection(state.data, state.axis, state.pos).forEach(function (c) {
        if (!state.show[c.type]) {
          return;
        }
        ctx.globalAlpha = c.z <= currentZ + 1e-6 ? 1 : 0.15;
        ctx.fillStyle = COLORS[c.type];
        var x = pad + (c.from - lo) * s;
        var w = Math.max(1, (c.to - c.from) * s);
        var y = size - pad - c.z * s;
        var h = Math.max(1, c.h * s);
        ctx.fillRect(x, y, w, h);
      });
      ctx.globalAlpha = 1;
      ctx.strokeStyle = '#facc15';
      ctx.beginPath();
      ctx.moveTo(pad, size - pad - currentZ * s);
      ctx.lineTo(size - pad, size - pad - currentZ * s);
      ctx.stroke();
    }

    function render() {
      if (!state.data || !state.data.layers.length) {
        return;
      }
      var layer = state.data.layers[state.layer];
      info.textContent = 'Layer ' + layer.index + '/' + state.data.layer_count + '  Z ' + layer.z.toFixed(3) +
        ' mm  |  cut ' + (state.axis === 'x' ? 'X' : 'Y') + ' = ' + state.pos.toFixed(2) + ' mm' +
        (state.data.layer_stride > 1 ? '  (every ' + state.data.layer_stride + ' layers shown)' : '');
      renderTop();
      renderSide();
    }

    function setData(data) {
      state.data = data;
      state.bounds = boundsOf(data);
      layerSlider.max = String(Math.max(0, data.layers.length - 1));
      state.layer = Math.min(state.layer, data.layers.length - 1);
      layerSlider.value = String(state.layer);
      updatePos();
      warnings.innerHTML = '';
      (data.warnings || []).forEach(function (w) {
        warnings.appendChild(el('li', {}, w.message || String(w)));
      });
      render();
    }

    return {
      setData: setData,
      setLayer: function (i) {
        state.layer = i;
        layerSlider.value = String(i);
        render();
      },
      destroy: function () {
        container.innerHTML = '';
      }
    };
  }

  async function fetchPreview(formData) {
    var r = await fetch('/api/manufacturing/preview', { method: 'POST', body: formData });
    var j = await r.json();
    if (!r.ok) {
      var err = new Error(typeof j.detail === 'string' ? j.detail : 'Preview failed');
      err.response = j;
      throw err;
    }
    return j;
  }

  root.UNGPreview = { mount: mount, fetchPreview: fetchPreview, crossSection: crossSection, boundsOf: boundsOf };
})(typeof window !== 'undefined' ? window : globalThis);
