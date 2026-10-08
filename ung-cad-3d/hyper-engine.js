/* UNG-CAD Hyper engine — 4D/5D shapes made printable.
 *
 * A printer moves in 3 directions, so a 4D or 5D shape cannot be printed as-is.
 * This engine turns one into a real, printable 3D solid in one of two ways:
 *   - SHADOW: rotate the shape in its extra directions, then project it down to 3D
 *             (like a 3D cube casting a 2D shadow). Printed as a strut/node frame.
 *   - SLICE:  cut the shape with a flat 3D "knife" and print the solid piece.
 *
 * Pure math, no DOM. Works in the browser (window.HyperEngine) and in Node (module.exports).
 * The frame union for SHADOW uses the manifold-3d WASM module when given one.
 */
(function (root) {
  'use strict';

  // ---------- small vector helpers ----------
  const dot = (a, b) => { let s = 0; for (let i = 0; i < a.length; i++) s += a[i] * b[i]; return s; };
  const sub = (a, b) => a.map((v, i) => v - b[i]);
  const add = (a, b) => a.map((v, i) => v + b[i]);
  const scl = (a, k) => a.map(v => v * k);
  const len = a => Math.sqrt(dot(a, a));
  const cross3 = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const norm = a => { const l = len(a) || 1; return scl(a, 1 / l); };

  // ---------- the shapes ----------
  // Each shape: verts (circumradius 1), edges [i,j], planes [{a, b}] meaning a·x <= b (the solid).
  const SHAPES = [
    { id: 'cube', name: 'Hypercube', dims: [4, 5], blurb: '4D: tesseract (cube of cubes). 5D: penteract.' },
    { id: 'simplex', name: 'Hyper-pyramid (simplex)', dims: [4, 5], blurb: 'The simplest shape in each dimension: 5 or 6 corners, all joined.' },
    { id: 'cross', name: 'Hyper-octahedron', dims: [4, 5], blurb: 'Corners on every axis, both ways (the "cross-polytope").' },
    { id: 'cell24', name: '24-cell', dims: [4], blurb: 'A 4D shape with no 3D twin: 24 octahedral cells.' },
  ];

  function signCombos(n) {
    const out = [];
    for (let m = 0; m < (1 << n); m++) { const v = []; for (let i = 0; i < n; i++) v.push(m & (1 << i) ? 1 : -1); out.push(v); }
    return out;
  }

  function polytope(id, n) {
    if (id === 'cube') {
      const k = 1 / Math.sqrt(n);
      const verts = signCombos(n).map(v => scl(v, k));
      const edges = [];
      for (let i = 0; i < verts.length; i++) for (let j = i + 1; j < verts.length; j++) {
        let d = 0; for (let t = 0; t < n; t++) if (verts[i][t] !== verts[j][t]) d++;
        if (d === 1) edges.push([i, j]);
      }
      const planes = [];
      for (let t = 0; t < n; t++) for (const s of [1, -1]) { const a = new Array(n).fill(0); a[t] = s; planes.push({ a, b: k }); }
      return { verts, edges, planes };
    }
    if (id === 'cross') {
      const verts = [];
      for (let t = 0; t < n; t++) for (const s of [1, -1]) { const v = new Array(n).fill(0); v[t] = s; verts.push(v); }
      const edges = [];
      for (let i = 0; i < verts.length; i++) for (let j = i + 1; j < verts.length; j++) if (Math.abs(dot(verts[i], verts[j]) + 1) > 1e-9) edges.push([i, j]);
      const planes = signCombos(n).map(s => ({ a: s, b: 1 }));
      return { verts, edges, planes };
    }
    if (id === 'simplex') {
      // n+1 points of R^(n+1) basis, centred, expressed in an orthonormal basis of the hyperplane sum = 0
      const m = n + 1, c = 1 / m;
      const pts = []; for (let i = 0; i < m; i++) { const p = new Array(m).fill(-c); p[i] += 1; pts.push(p); }
      const basis = [];
      for (let i = 0; i < m && basis.length < n; i++) {
        let v = new Array(m).fill(0); v[i] = 1; v = v.map(x => x - 1 / m);
        for (const b of basis) v = sub(v, scl(b, dot(v, b)));
        if (len(v) > 1e-9) basis.push(norm(v));
      }
      let verts = pts.map(p => basis.map(b => dot(p, b)));
      const r = len(verts[0]); verts = verts.map(v => scl(v, 1 / r));
      const edges = []; for (let i = 0; i < m; i++) for (let j = i + 1; j < m; j++) edges.push([i, j]);
      const planes = verts.map(v => ({ a: scl(v, -1), b: 1 / n }));
      return { verts, edges, planes };
    }
    if (id === 'cell24') {
      if (n !== 4) throw new Error('The 24-cell only exists in 4D');
      const raw = [];
      for (let i = 0; i < 4; i++) for (let j = i + 1; j < 4; j++) for (const si of [1, -1]) for (const sj of [1, -1]) {
        const v = [0, 0, 0, 0]; v[i] = si; v[j] = sj; raw.push(v);
      }
      const k = 1 / Math.SQRT2;
      const verts = raw.map(v => scl(v, k));
      const edges = [];
      for (let i = 0; i < raw.length; i++) for (let j = i + 1; j < raw.length; j++) if (Math.abs(len(sub(raw[i], raw[j])) - Math.SQRT2) < 1e-9) edges.push([i, j]);
      const planes = [];
      for (let t = 0; t < 4; t++) for (const s of [1, -1]) { const a = [0, 0, 0, 0]; a[t] = s; planes.push({ a, b: k }); }
      for (const s of signCombos(4)) planes.push({ a: scl(s, 0.5), b: k });
      return { verts, edges, planes };
    }
    throw new Error('Unknown shape: ' + id);
  }

  // ---------- rotations in n dimensions ----------
  // In n dimensions you rotate "in a plane" (a pair of axes), not around an axis.
  const AXES = ['X', 'Y', 'Z', 'W', 'V'];
  function rotationPlanes(n) {
    const out = [];
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) out.push({ i, j, label: AXES[i] + AXES[j], extra: j >= 3 });
    return out;
  }
  function identity(n) { return Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => (i === j ? 1 : 0))); }
  function matMul(A, B) {
    const n = A.length; const C = identity(n).map(r => r.fill(0));
    for (let i = 0; i < n; i++) for (let k = 0; k < n; k++) { const a = A[i][k]; if (a) for (let j = 0; j < n; j++) C[i][j] += a * B[k][j]; }
    return C;
  }
  // angles: { 'XW': degrees, ... }
  function rotation(n, angles) {
    let R = identity(n);
    for (const p of rotationPlanes(n)) {
      const deg = (angles && angles[p.label]) || 0; if (!deg) continue;
      const t = deg * Math.PI / 180, c = Math.cos(t), s = Math.sin(t);
      const G = identity(n); G[p.i][p.i] = c; G[p.i][p.j] = -s; G[p.j][p.i] = s; G[p.j][p.j] = c;
      R = matMul(G, R);
    }
    return R;
  }
  const apply = (R, v) => R.map(row => dot(row, v));

  // ---------- SHADOW: project n-D down to 3-D ----------
  // perspective: each extra direction is viewed from a "camera" at distance `eye` along it.
  function projectPoint(y, opts) {
    let p = y.slice();
    const eye = (opts && opts.eye) || 3;
    const persp = !opts || opts.perspective !== false;
    while (p.length > 3) {
      const w = p.pop();
      const f = persp ? eye / (eye - w) : 1;
      p = p.map(v => v * f);
    }
    return p;
  }
  function shadow(shapeId, n, angles, opts) {
    const P = polytope(shapeId, n), R = rotation(n, angles);
    const pts = P.verts.map(v => projectPoint(apply(R, v), opts));
    return { points: pts, edges: P.edges };
  }

  // ---------- SLICE: cut with a flat 3D "knife" ----------
  // After rotating, keep the points whose extra coordinates (W, V) equal `offsets`.
  function solve3(A, b) {
    const d = dot(A[0], cross3(A[1], A[2]));
    if (Math.abs(d) < 1e-10) return null;
    const c12 = cross3(A[1], A[2]), c20 = cross3(A[2], A[0]), c01 = cross3(A[0], A[1]);
    return [0, 1, 2].map(k => (b[0] * c12[k] + b[1] * c20[k] + b[2] * c01[k]) / d);
  }
  function slice(shapeId, n, angles, offsets) {
    const P = polytope(shapeId, n), R = rotation(n, angles);
    const off = offsets || [];
    // a·x <= b with x = R^T y  ->  (R a)·y <= b
    let planes = P.planes.map(pl => {
      const ra = apply(R, pl.a);
      let rhs = pl.b; for (let k = 3; k < n; k++) rhs -= ra[k] * (off[k - 3] || 0);
      const nn = ra.slice(0, 3), l = len(nn);
      return l < 1e-12 ? { n: null, d: rhs } : { n: scl(nn, 1 / l), d: rhs / l };
    });
    if (planes.some(p => !p.n && p.d < -1e-9)) return null;            // a whole constraint fails: knife misses
    planes = planes.filter(p => p.n);
    // de-duplicate identical planes
    const uniq = [];
    for (const p of planes) if (!uniq.some(q => len(sub(p.n, q.n)) < 1e-7 && Math.abs(p.d - q.d) < 1e-7)) uniq.push(p);
    const eps = 1e-7, verts = [];
    for (let i = 0; i < uniq.length; i++) for (let j = i + 1; j < uniq.length; j++) for (let k = j + 1; k < uniq.length; k++) {
      const x = solve3([uniq[i].n, uniq[j].n, uniq[k].n], [uniq[i].d, uniq[j].d, uniq[k].d]);
      if (!x) continue;
      if (uniq.every(p => dot(p.n, x) <= p.d + eps) && !verts.some(v => len(sub(v, x)) < 1e-6)) verts.push(x);
    }
    if (verts.length < 4) return null;
    // faces: the vertices lying on each plane, ordered around their centre
    const faces = [];
    for (const p of uniq) {
      const on = verts.map((v, i) => i).filter(i => Math.abs(dot(p.n, verts[i]) - p.d) < 1e-6);
      if (on.length < 3) continue;
      const c = scl(on.reduce((s, i) => add(s, verts[i]), [0, 0, 0]), 1 / on.length);
      let u = sub(verts[on[0]], c); u = norm(u); const w = cross3(p.n, u);
      on.sort((a, b) => Math.atan2(dot(sub(verts[a], c), w), dot(sub(verts[a], c), u)) - Math.atan2(dot(sub(verts[b], c), w), dot(sub(verts[b], c), u)));
      faces.push({ n: p.n, idx: on });
    }
    if (faces.length < 4) return null;
    return { verts, faces };
  }

  // ---------- turning results into printable triangles (millimetres) ----------
  function bbox(points) {
    const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
    for (const p of points) for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], p[k]); hi[k] = Math.max(hi[k], p[k]); }
    return { lo, hi, size: hi.map((v, k) => v - lo[k]) };
  }

  // Slice -> watertight triangle list, sitting on its biggest face, largest side = sizeMM
  function sliceTriangles(sl, sizeMM) {
    let best = null, bestA = -1;
    for (const f of sl.faces) {
      let a = 0; const p0 = sl.verts[f.idx[0]];
      for (let t = 1; t + 1 < f.idx.length; t++) a += len(cross3(sub(sl.verts[f.idx[t]], p0), sub(sl.verts[f.idx[t + 1]], p0))) / 2;
      if (a > bestA) { bestA = a; best = f; }
    }
    // rotate so the biggest face's outward normal points straight down (-Z)
    const from = best.n, to = [0, 0, -1];
    const Rm = rotBetween(from, to);
    let verts = sl.verts.map(v => mat3(Rm, v));
    const b = bbox(verts), k = sizeMM / Math.max(...b.size);
    verts = verts.map(v => [(v[0] - (b.lo[0] + b.hi[0]) / 2) * k, (v[1] - (b.lo[1] + b.hi[1]) / 2) * k, (v[2] - b.lo[2]) * k]);
    const tris = [];
    for (const f of sl.faces) for (let t = 1; t + 1 < f.idx.length; t++) {
      let a = verts[f.idx[0]], bb = verts[f.idx[t]], c = verts[f.idx[t + 1]];
      const nrm = mat3(Rm, f.n);
      if (dot(cross3(sub(bb, a), sub(c, a)), nrm) < 0) { const tmp = bb; bb = c; c = tmp; }
      tris.push([a, bb, c]);
    }
    return tris;
  }
  function mat3(M, v) { return [dot(M[0], v), dot(M[1], v), dot(M[2], v)]; }
  function rotBetween(a, b) {   // rotation matrix taking unit vector a onto unit vector b
    const v = cross3(a, b), c = dot(a, b);
    if (c < -0.999999) { // opposite: turn 180 degrees about any perpendicular axis
      const ax = norm(Math.abs(a[0]) < 0.9 ? cross3(a, [1, 0, 0]) : cross3(a, [0, 1, 0]));
      return [0, 1, 2].map(i => [0, 1, 2].map(j => 2 * ax[i] * ax[j] - (i === j ? 1 : 0)));
    }
    const K = [[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]];
    const K2 = matMul(K, K), f = 1 / (1 + c);
    return [0, 1, 2].map(i => [0, 1, 2].map(j => (i === j ? 1 : 0) + K[i][j] + K2[i][j] * f));
  }

  // Shadow -> scaled points (mm), largest side = sizeMM, resting on Z = 0 (struts included)
  function shadowLayout(sh, sizeMM, strutMM) {
    const b = bbox(sh.points);
    const k = (sizeMM - strutMM * 1.6) / Math.max(...b.size);
    const r = strutMM * 0.8;
    const pts = sh.points.map(p => [(p[0] - (b.lo[0] + b.hi[0]) / 2) * k, (p[1] - (b.lo[1] + b.hi[1]) / 2) * k, (p[2] - b.lo[2]) * k + r]);
    return { points: pts, edges: sh.edges };
  }

  // A closed prism (strut) between two points, as shared-vertex mesh arrays
  function strutMesh(p, q, radius, sides) {
    const axis = sub(q, p), L = len(axis); if (L < 1e-9) return null;
    const z = scl(axis, 1 / L);
    const x = norm(Math.abs(z[0]) < 0.9 ? cross3(z, [1, 0, 0]) : cross3(z, [0, 1, 0])), y = cross3(z, x);
    const verts = [];
    for (const end of [p, q]) for (let s = 0; s < sides; s++) {
      const t = 2 * Math.PI * s / sides;
      verts.push(add(end, add(scl(x, radius * Math.cos(t)), scl(y, radius * Math.sin(t)))));
    }
    verts.push(p.slice(), q.slice());
    const cp = 2 * sides, cq = 2 * sides + 1, tri = [];
    for (let s = 0; s < sides; s++) {
      const a = s, b = (s + 1) % sides, a2 = a + sides, b2 = b + sides;
      tri.push([a, b, b2], [a, b2, a2], [cp, b, a], [cq, a2, b2]);
    }
    return { verts, tri };
  }

  // Build the printable frame. With a manifold-3d module -> one clean, watertight solid.
  // Without one -> overlapping closed pieces (fine for viewing, most slicers merge them).
  function shadowSolid(layout, strutMM, wasm) {
    const rS = strutMM / 2, rN = strutMM * 0.8, sides = 12;
    if (wasm && wasm.Manifold) {
      const { Manifold, Mesh } = wasm, parts = [];
      for (const [i, j] of layout.edges) {
        const m = strutMesh(layout.points[i], layout.points[j], rS, sides); if (!m) continue;
        const mesh = new Mesh({ numProp: 3, vertProperties: Float32Array.from(m.verts.flat()), triVerts: Uint32Array.from(m.tri.flat()) });
        mesh.merge();
        parts.push(new Manifold(mesh));
      }
      for (const p of layout.points) parts.push(Manifold.sphere(rN, 20).translate(p));
      const solid = Manifold.union(parts);
      const out = solid.getMesh(), tris = [];
      const vp = out.vertProperties, np = out.numProp, tv = out.triVerts;
      const V = i => [vp[i * np], vp[i * np + 1], vp[i * np + 2]];
      for (let t = 0; t < tv.length; t += 3) tris.push([V(tv[t]), V(tv[t + 1]), V(tv[t + 2])]);
      const parts1 = solid.decompose(); const pieces = parts1.length; parts1.forEach(m => m.delete && m.delete());
      const info = { watertight: true, volume: solid.volume(), genus: solid.genus(), pieces, triVerts: Array.from(tv) };
      parts.forEach(m => m.delete && m.delete()); solid.delete && solid.delete();
      return { tris, info };
    }
    const tris = [];
    for (const [i, j] of layout.edges) {
      const m = strutMesh(layout.points[i], layout.points[j], rS, sides); if (!m) continue;
      for (const t of m.tri) tris.push(t.map(k => m.verts[k]));
    }
    for (const p of layout.points) for (const t of icoSphere(p, rN)) tris.push(t);
    return { tris, info: { watertight: false } };
  }

  function icoSphere(c, r) {
    const t = (1 + Math.sqrt(5)) / 2;
    let V = [[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]].map(norm);
    let F = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]];
    const nf = [], mid = {};
    const m = (a, b) => { const k = a < b ? a + '_' + b : b + '_' + a; if (mid[k] === undefined) { mid[k] = V.length; V.push(norm(add(V[a], V[b]))); } return mid[k]; };
    for (const [a, b, c2] of F) { const ab = m(a, b), bc = m(b, c2), ca = m(c2, a); nf.push([a, ab, ca], [b, bc, ab], [c2, ca, bc], [ab, bc, ca]); }
    return nf.map(f => f.map(i => add(c, scl(V[i], r))));
  }

  // ---------- STL ----------
  function toBinarySTL(tris, name) {
    const buf = new ArrayBuffer(84 + tris.length * 50), dv = new DataView(buf);
    const label = ('UNG-CAD Hyper ' + (name || '')).slice(0, 79);
    for (let i = 0; i < label.length; i++) dv.setUint8(i, label.charCodeAt(i) & 127);
    dv.setUint32(80, tris.length, true);
    let o = 84;
    for (const [a, b, c] of tris) {
      const n = norm(cross3(sub(b, a), sub(c, a)));
      for (const v of [n, a, b, c]) { dv.setFloat32(o, v[0], true); dv.setFloat32(o + 4, v[1], true); dv.setFloat32(o + 8, v[2], true); o += 12; }
      dv.setUint16(o, 0, true); o += 2;
    }
    return buf;
  }

  const api = { SHAPES, polytope, rotationPlanes, rotation, apply, projectPoint, shadow, slice,
                sliceTriangles, shadowLayout, shadowSolid, strutMesh, toBinarySTL, bbox, _solve3: solve3 };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.HyperEngine = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
