// Tests for hyper-engine.js — run: node hyper-engine.test.js
// Optional: MANIFOLD_PATH=/abs/path/to/manifold-3d/manifold.js to also test the solid frame union.
const H = require('./hyper-engine.js');
let pass = 0, fail = 0;
function ok(cond, msg) { if (cond) { pass++; } else { fail++; console.log('FAIL:', msg); } }
const near = (a, b, e = 1e-6) => Math.abs(a - b) < e;
const dist = (a, b) => Math.sqrt(a.reduce((s, v, i) => s + (v - b[i]) ** 2, 0));
const dot = (a, b) => a.reduce((s, v, i) => s + v * b[i], 0);

// 1-3: known corner/edge counts, circumradius 1, equal edges, every corner inside every face
const COUNTS = { 'cube4': [16, 32], 'cube5': [32, 80], 'simplex4': [5, 10], 'simplex5': [6, 15],
                 'cross4': [8, 24], 'cross5': [10, 40], 'cell244': [24, 96] };
for (const key in COUNTS) {
  const n = +key.slice(-1), id = key.slice(0, -1);
  const P = H.polytope(id, n);
  ok(P.verts.length === COUNTS[key][0], `${key} corners ${P.verts.length}`);
  ok(P.edges.length === COUNTS[key][1], `${key} edges ${P.edges.length}`);
  ok(P.verts.every(v => near(Math.hypot(...v), 1)), `${key} circumradius 1`);
  const L = P.edges.map(([i, j]) => dist(P.verts[i], P.verts[j]));
  ok(L.every(l => near(l, L[0])), `${key} all edges equal`);
  ok(P.verts.every(v => P.planes.every(p => dot(p.a, v) <= p.b + 1e-9)), `${key} corners inside all faces`);
  ok(P.planes.every(p => P.verts.filter(v => near(dot(p.a, v), p.b)).length >= n), `${key} every face touches >= n corners`);
}

// 4: rotations are proper (orthonormal) in 4D and 5D
for (const n of [4, 5]) {
  const angles = {}; H.rotationPlanes(n).forEach((p, k) => angles[p.label] = 17 * (k + 1));
  const R = H.rotation(n, angles);
  let worst = 0;
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) worst = Math.max(worst, Math.abs(dot(R[i], R[j]) - (i === j ? 1 : 0)));
  ok(worst < 1e-12, `${n}D rotation orthonormal (${worst})`);
}
ok(H.rotationPlanes(4).length === 6 && H.rotationPlanes(5).length === 10, '6 rotation planes in 4D, 10 in 5D');

// volume of a closed slice (divergence theorem over its fan triangles)
function sliceVolume(sl) {
  let v = 0;
  for (const f of sl.faces) { const p = f.idx.map(i => sl.verts[i]);
    for (let t = 1; t + 1 < p.length; t++) { const a = p[0], b = p[t], c = p[t + 1];
      const cr = [b[1]*c[2]-b[2]*c[1], b[2]*c[0]-b[0]*c[2], b[0]*c[1]-b[1]*c[0]];
      v += Math.abs(dot(a, cr)) / 6 * Math.sign(dot(cr, f.n) || 1) * Math.sign(dot(a, f.n) || 1); } }
  return v;
}
// 5-9: slices with known answers
const k4 = 0.5, k5 = 1 / Math.sqrt(5);
let s = H.slice('cube', 4, {}, [0]);
ok(s && s.verts.length === 8 && near(sliceVolume(s), (2 * k4) ** 3, 1e-9), 'tesseract cut at W=0 is a cube of the right size');
s = H.slice('cross', 4, {}, [0]);
ok(s && s.verts.length === 6 && near(sliceVolume(s), 4 / 3, 1e-9), '16-cell cut at W=0 is an octahedron (vol 4/3)');
ok(H.slice('cube', 4, {}, [0.9]) === null, 'knife outside the shape gives nothing');
s = H.slice('cube', 5, {}, [0, 0]);
ok(s && s.verts.length === 8 && near(sliceVolume(s), (2 * k5) ** 3, 1e-9), 'penteract cut at W=V=0 is a cube');
s = H.slice('cube', 4, { XW: 45 }, [0]);
ok(s && near(sliceVolume(s), (2 * k4) ** 3 * Math.SQRT2, 1e-9), 'tesseract turned 45 deg in XW, cut at W=0: box stretched by sqrt 2');
s = H.slice('cube', 4, { XW: 30, YW: 40, ZW: 50 }, [0.05]);
ok(s && s.faces.length > 6, `tesseract turned in all three W planes gives a new solid (${s && s.faces.length} faces)`);

// 10: printable slice mesh is closed, outward, on the bed, the asked size
function edgeCheck(tris) {
  const key = (a, b) => a.map(x => x.toFixed(5)).join(',') + '|' + b.map(x => x.toFixed(5)).join(',');
  const m = new Map();
  for (const t of tris) for (let e = 0; e < 3; e++) { const k = key(t[e], t[(e + 1) % 3]); m.set(k, (m.get(k) || 0) + 1); }
  for (const [k, c] of m) { const [a, b] = k.split('|'); if (c !== 1 || m.get(b + '|' + a) !== 1) return false; }
  return true;
}
function signedVol(tris) { let v = 0; for (const [a, b, c] of tris) v += dot(a, [b[1]*c[2]-b[2]*c[1], b[2]*c[0]-b[0]*c[2], b[0]*c[1]-b[1]*c[0]]) / 6; return v; }
for (const [id, n, ang, off] of [['cube', 4, { XW: 30, YW: 40, ZW: 50 }, [0.05]], ['simplex', 5, { XW: 20, YV: 35, ZW: 10 }, [0.02, -0.03]], ['cell24', 4, { XW: 25, ZW: 60 }, [0.1]], ['cross', 5, { XV: 40, YW: 15 }, [0.1, 0]]]) {
  const sl = H.slice(id, n, ang, off);
  const tris = H.sliceTriangles(sl, 40);
  const zs = tris.flat().map(p => p[2]);
  const b = H.bbox(tris.flat());
  ok(edgeCheck(tris), `${id}${n} slice mesh is closed (watertight)`);
  ok(signedVol(tris) > 0, `${id}${n} slice faces point outward`);
  ok(near(Math.min(...zs), 0, 1e-9), `${id}${n} slice sits on the bed`);
  ok(near(Math.max(...b.size), 40, 1e-6), `${id}${n} slice largest side = 40 mm`);
  const bottomA = tris.filter(t => t.every(p => Math.abs(p[2]) < 1e-6)).length;
  ok(bottomA > 0, `${id}${n} slice has a flat face on the bed`);
}

// 11: shadow layout fits the size and rests on the bed
const lay = H.shadowLayout(H.shadow('cube', 5, { XW: 20, YV: 30 }), 60, 2.4);
const lb = H.bbox(lay.points);
ok(Math.max(...lb.size) <= 60 - 2.4 * 1.6 + 1e-9 && near(lb.lo[2], 2.4 * 0.8), 'shadow fits 60 mm and its nodes rest on the bed');

// 12: STL size
const buf = H.toBinarySTL([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], 't');
ok(buf.byteLength === 84 + 50, 'binary STL length');

(async () => {
  if (process.env.MANIFOLD_PATH) {
    const Module = (await import(process.env.MANIFOLD_PATH)).default;
    const wasm = await Module(); wasm.setup();
    for (const [id, n, E, V] of [['cube', 4, 32, 16], ['cube', 5, 80, 32], ['simplex', 5, 15, 6], ['cell24', 4, 96, 24]]) {
      const L = H.shadowLayout(H.shadow(id, n, { XW: 20, YW: 15, ZW: 10 }), 60, 2.4);
      const { tris, info } = H.shadowSolid(L, 2.4, wasm);
      ok(info.watertight && tris.length > 100, `${id}${n} shadow frame unions into one solid (${tris.length} triangles)`);
      ok(info.pieces === 1, `${id}${n} frame is one connected piece (${info.pieces})`);
      const m = new Map(), tv = info.triVerts;
      for (let t = 0; t < tv.length; t += 3) for (let e = 0; e < 3; e++) { const k = tv[t + e] + ',' + tv[t + (e + 1) % 3]; m.set(k, (m.get(k) || 0) + 1); }
      let closed = true; for (const [k, c] of m) { const [a, b] = k.split(','); if (c !== 1 || m.get(b + ',' + a) !== 1) closed = false; }
      ok(closed, `${id}${n} shadow frame mesh closed (every edge shared by exactly 2 triangles)`);
    }
  } else console.log('(manifold not given: skipped frame-union tests)');
  console.log(`${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
