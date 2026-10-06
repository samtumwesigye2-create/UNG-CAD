// Node smoke tests for the front-end files (no browser needed). Run: node tests/js_smoke.js
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '..');
const read = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8');

function fakeElement(id) {
  const ctx = new Proxy({}, { get: (t, k) => (k in t ? t[k] : () => {}), set: (t, k, v) => { t[k] = v; return true; } });
  return {
    id, value: '', textContent: '', innerHTML: '', disabled: false, checked: false, style: {}, files: [],
    children: [], listeners: {}, attrs: {},
    classList: { add() {}, remove() {} },
    setAttribute(k, v) { this.attrs[k] = v; },
    appendChild(c) { this.children.push(c); return c; },
    prepend(c) { this.children.unshift(c); },
    addEventListener(t, f) { this.listeners[t] = f; },
    getContext() { return ctx; },
  };
}

function fakeStorage() {
  const m = new Map();
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k) };
}

async function testPreviewViewer() {
  const ctx = { console, Math, Number, String, Object, Array, isFinite, parseInt };
  ctx.globalThis = ctx;
  ctx.window = ctx;
  ctx.document = { createElement: (t) => fakeElement(t) };
  vm.createContext(ctx);
  vm.runInContext(read('public/preview_viewer.js'), ctx);
  const ring = [[-5, -5], [5, -5], [5, 5], [-5, 5], [-5, -5]];
  const data = {
    line_width: 0.45, layer_count: 2, layer_stride: 1, warnings: [{ message: 'hello' }],
    layers: [
      { index: 1, z: 0.2, thickness: 0.2, paths: [{ type: 'perimeter', points: ring }, { type: 'travel', points: [[0, 0], [1, 1]] }] },
      { index: 2, z: 0.4, thickness: 0.2, paths: [{ type: 'infill', points: [[-4, 0], [4, 0]] }] },
    ],
  };
  const cells = ctx.UNGPreview.crossSection(data, 'y', 0);
  // layer 1: the ring crosses Y=0 twice; layer 2: the infill line runs along the plane
  assert.strictEqual(cells.length, 3);
  assert.ok(cells.some((c) => c.type === 'infill' && c.to - c.from > 8));
  const host = fakeElement('host');
  const viewer = ctx.UNGPreview.mount(host);
  viewer.setData(data);
  viewer.setLayer(1);
  assert.ok(host.children.length >= 4);
}

async function testAuthHelper() {
  const calls = [];
  let jobsStatus = 401;
  const storage = fakeStorage();
  const win = {
    location: { href: 'https://app.example/drafting.html', origin: 'https://app.example' },
    prompt: () => 'tok123',
    alert: () => {},
    fetch: async (url, init) => {
      const headers = new Headers((init && init.headers) || {});
      calls.push({ url: String(url), headers });
      if (String(url) === '/api/login') return { ok: true, status: 200 };
      if (String(url) === '/api/jobs') {
        const ok = headers.get('Authorization') === 'Bearer tok123';
        return { ok, status: ok ? 200 : jobsStatus };
      }
      if (String(url).startsWith('http://127.0.0.1:8765')) {
        return { ok: true, status: headers.get('X-UNG-Bridge-Token') ? 200 : 401 };
      }
      return { ok: true, status: 200 };
    },
  };
  const ctx = { window: win, localStorage: storage, Headers, URL, console, JSON, Object, String, Promise };
  vm.createContext(ctx);
  vm.runInContext(read('public/ung-auth.js'), ctx);
  const r = await win.fetch('/api/jobs');
  assert.strictEqual(r.status, 200);
  assert.strictEqual(storage.getItem('ung-cad-dashboard-token'), 'tok123');
  assert.ok(calls.some((c) => c.url === '/api/login'));
  calls.length = 0;
  await win.fetch('https://other.example/api/jobs');
  assert.strictEqual(calls[0].headers.get('Authorization'), null);   // never leak the token cross-origin
  await win.fetch('/health');
  assert.strictEqual(calls[1].headers.get('Authorization'), null);
  const b = await win.UNG.bridgeFetch('/serial/ports');
  assert.strictEqual(b.status, 200);
  assert.strictEqual(calls[2].headers.get('X-UNG-Bridge-Token'), 'tok123');
}

async function testDraftingSection() {
  const els = {};
  const ids = ['cnc-mode', 'cnc-scale', 'cnc-feed', 'cnc-safez', 'cnc-depth-pass', 'cnc-total-depth', 'cnc-spindle',
    'cnc-power', 'cnc-max-s', 'cnc-generate', 'cnc-status', 'cnc-refresh-ports', 'cnc-port', 'cnc-baud', 'cnc-send',
    'cnc-stop', 'cnc-send-status', 'cnc-bridge-token', 'drawing-name'];
  ids.forEach((id) => { els[id] = fakeElement(id); });
  Object.assign(els['cnc-mode'], { value: 'laser' });
  Object.assign(els['cnc-scale'], { value: '0.5' });
  Object.assign(els['cnc-feed'], { value: '900' });
  Object.assign(els['cnc-spindle'], { value: '15000' });
  Object.assign(els['cnc-power'], { value: '60' });
  Object.assign(els['cnc-port'], { value: 'COM3' });
  Object.assign(els['cnc-baud'], { value: '115200' });
  const bridgeCalls = [];
  const confirms = [];
  const win = {
    confirm: (msg) => { confirms.push(msg); return true; },
    UNG: {
      BRIDGE_URL: 'http://127.0.0.1:8765',
      bridgeFetch: async (p, init) => {
        bridgeCalls.push({ p, init });
        if (p === '/serial/send') return { ok: true, status: 202, json: async () => ({ ok: true, job_id: 'j1', total_lines: 10 }) };
        if (p === '/serial/stop') return { ok: true, status: 200, json: async () => ({ stopped: true }) };
        return { ok: true, status: 200, json: async () => ({ job: { state: 'running', sent_lines: 1, total_lines: 10, progress: 0.1, active: true } }) };
      },
      bridgeToken: () => 'x',
    },
  };
  const timers = [];
  const ctx = {
    window: win, console, JSON, Math, Number, parseFloat, encodeURIComponent,
    document: { getElementById: (id) => els[id], querySelectorAll: () => [], createElement: (t) => fakeElement(t) },
    fetch: async (url, init) => ({ ok: true, status: 200, text: async () => 'G0 X0\n', json: async () => ({ download: '/api/manufacturing/download/a.gcode', machine_file: 'a.gcode', stats: { paths: 1, estimated_seconds: 5 } }) }),
    setInterval: (f) => { timers.push(f); return timers.length; },
    clearInterval: () => {},
  };
  vm.createContext(ctx);
  vm.runInContext('let shapes=[{t:"rect",a:{x:0,y:0},b:{x:10,y:10}}];\n' + read('drafting_cnc_section.js') +
    '\nthis.cncSettings = cncSettings;', ctx);
  const s = ctx.cncSettings();
  assert.strictEqual(s.spindle_speed, 15000);
  assert.strictEqual(s.laser_power_percent, 60);
  assert.strictEqual(s.max_s, 1000);
  assert.strictEqual(s.scale_mm_per_px, 0.5);
  await els['cnc-generate'].onclick();
  assert.ok(els['cnc-status'].textContent.startsWith('G-CODE READY'));
  await els['cnc-send'].onclick();
  assert.strictEqual(confirms.length, 1);
  const send = bridgeCalls.find((c) => c.p === '/serial/send');
  assert.ok(send && send.init.headers['X-Port'] === 'COM3' && send.init.headers['X-Machine-Mode'] === 'laser');
  assert.strictEqual(timers.length, 1);           // status polling started
  await timers[0]();
  assert.ok(bridgeCalls.some((c) => c.p.startsWith('/serial/status?job_id=j1')));
  await els['cnc-stop'].onclick();
  assert.ok(bridgeCalls.some((c) => c.p === '/serial/stop'));
  assert.ok(els['cnc-send-status'].textContent.startsWith('STOPPED'));
  // declining the confirm sends nothing
  win.confirm = () => false;
  const before = bridgeCalls.length;
  await els['cnc-send'].onclick();
  assert.strictEqual(bridgeCalls.length, before);
}

(async () => {
  await testPreviewViewer();
  await testAuthHelper();
  await testDraftingSection();
  console.log('js smoke tests: OK');
})().catch((e) => { console.error(e); process.exit(1); });
