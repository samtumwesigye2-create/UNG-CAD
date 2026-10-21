// Checks the strength engine against textbook beam formulas.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const ctx={window:{},TextDecoder,TextEncoder,ArrayBuffer,DataView,Uint8Array,Math,console};ctx.globalThis=ctx.window;vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname,'..','csg-engine.js'),'utf8'),ctx);
const C=ctx.window.CSGEngine,A=require('../analyze-engine.js'),S=require('../strength-engine.js');
const tris=p=>A.trianglesFromPolygons(p);
const rel=(got,want,tol,msg)=>assert.ok(Math.abs(got-want)/Math.abs(want)<=tol,`${msg}: expected ${want}, got ${got}`);
let passed=0;const t=(name,fn)=>{fn();passed++;console.log('ok -',name);};

// Solid bar 100 (x) x 10 (y) x 10 (z), centred at x=50 so it spans x 0..100.
const bar=tris(C.cube({x:50,y:0,z:0},{x:100,y:10,z:10}));

t('square section: area, I = b*h^3/12, c = h/2',()=>{
  const sp=S.sectionProperties(bar,'x',37,'z');
  rel(sp.area,100,1e-6,'area');rel(sp.I,10*1000/12,1e-4,'I');rel(sp.c,5,1e-6,'c');
});

t('rectangle 20 wide x 10 tall: I depends on load direction',()=>{
  const flat=tris(C.cube({x:50,y:0,z:0},{x:100,y:20,z:10}));
  rel(S.sectionProperties(flat,'x',50,'z').I,20*1000/12,1e-4,'I (load down)');
  rel(S.sectionProperties(flat,'x',50,'y').I,10*8000/12,1e-4,'I (load sideways)');
});

t('hollow tube: hole is subtracted (even-odd fill)',()=>{
  const outer=C.cube({x:50,y:0,z:0},{x:100,y:20,z:20}),inner=C.cube({x:50,y:0,z:0},{x:120,y:12,z:12});
  const tube=tris(C.csgSubtract(outer,inner)),sp=S.sectionProperties(tube,'x',50,'z');
  rel(sp.area,400-144,1e-4,'area');rel(sp.I,(20*8000-12*1728)/12,1e-3,'I');rel(sp.c,10,1e-6,'c');
});

t('round rod: I = pi*d^4/64 (within faceting error)',()=>{
  const rod=tris(C.cylinder({x:0,y:0,z:0},{x:100,y:0,z:0},5,64));
  const sp=S.sectionProperties(rod,'x',50,'z',{rows:800});
  rel(sp.I,Math.PI*Math.pow(10,4)/64,.01,'I');
});

t('cantilever: root stress = F*L*c/I and tip deflection = F*L^3/(3*E*I)',()=>{
  const r=S.stressCheck(bar,{material:'PLA',axis:'x',loadDir:'z',fixed:'min',loadN:10,slices:200});
  const I=10*1000/12,E=S.MATERIALS.PLA.modulus;
  rel(r.weakest.sigma,10*(100-r.weakest.s)*5/I,1e-4,'stress at weakest slice');
  rel(r.weakest.sigma,6,0.01,'root stress ~6 MPa');
  assert.ok(r.weakest.s<1,'weakest point is at the held end');
  rel(r.deflection,10*1e6/(3*E*I),1e-3,'tip deflection');
  rel(r.safetyFactor,50/r.weakest.sigma,1e-9,'safety factor uses in-plane strength');
  assert.equal(r.verdict,'OK');assert.equal(r.acrossLayers,false);
});

t('holding the other end flips where it is weakest',()=>{
  const r=S.stressCheck(bar,{material:'PLA',axis:'x',loadDir:'z',fixed:'max',loadN:10});
  assert.ok(r.weakest.coord>99,'weakest near x=100');
});

t('kg load converts with g = 9.80665',()=>{
  const a=S.stressCheck(bar,{material:'PLA',axis:'x',loadKg:1}),b=S.stressCheck(bar,{material:'PLA',axis:'x',loadN:9.80665});
  rel(a.weakest.sigma,b.weakest.sigma,1e-12,'same stress');
});

t('a part standing upright is checked against weaker layer strength',()=>{
  const post=tris(C.cube({x:0,y:0,z:50},{x:10,y:10,z:100}));
  const r=S.stressCheck(post,{material:'PLA',loadDir:'x',loadN:10});
  assert.equal(r.axis,'z');assert.equal(r.acrossLayers,true);rel(r.strengthUsed,25,1e-12,'Z strength');
});

// notch leaves only 2 mm of material at x=30: sigma there = 70F*1/6.67 > root 100F*5/833
t('a deep notch becomes the weakest point and is highlighted',()=>{
  const notched=tris(C.csgSubtract(C.cube({x:50,y:0,z:0},{x:100,y:10,z:10}),C.cube({x:30,y:0,z:2},{x:4,y:20,z:10})));
  const r=S.stressCheck(notched,{material:'PLA',axis:'x',loadDir:'z',loadN:10,slices:100});
  assert.ok(r.weakest.coord>27&&r.weakest.coord<33,'weakest at the notch, got '+r.weakest.coord);
  assert.ok(r.highlight.length>0);
});

t('heavy load is flagged',()=>{
  assert.equal(S.stressCheck(bar,{material:'PLA',axis:'x',loadN:500}).verdict,'LIKELY TO BREAK');
});

t('bad inputs give clear errors',()=>{
  assert.throws(()=>S.stressCheck(bar,{material:'TPU',loadN:1}),/TPU/);
  assert.throws(()=>S.stressCheck(bar,{material:'PLA',axis:'x',loadDir:'x',loadN:1}),/across/);
  assert.throws(()=>S.stressCheck(bar,{material:'PLA',loadN:0}),/greater than zero/);
});

t('explode: parts move away from centre, scaled by factor',()=>{
  const parts=[{name:'L',tris:tris(C.cube({x:-10,y:0,z:0},{x:4,y:4,z:4}))},{name:'R',tris:tris(C.cube({x:10,y:0,z:0},{x:4,y:4,z:4}))}];
  const o=S.explodeOffsets(parts,.5);rel(o[0].x,-5,1e-9,'L');rel(o[1].x,5,1e-9,'R');
  const z=S.explodeOffsets(parts,0);assert.ok(z.every(p=>p.x===0&&p.y===0&&p.z===0));
});

t('explode: a centred part still lifts away',()=>{
  const parts=[{name:'shell',tris:tris(C.cube({x:0,y:0,z:0},{x:40,y:40,z:40}))},{name:'board',tris:tris(C.cube({x:0,y:0,z:0},{x:10,y:10,z:2}))}];
  const o=S.explodeOffsets(parts,1);assert.ok(o[1].z>o[0].z,'inner part separates');
});

console.log(`strength-engine: ${passed} tests passed`);
