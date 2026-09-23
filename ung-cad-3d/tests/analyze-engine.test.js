const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
function close(a,b,t=1e-6,msg=''){assert.ok(Math.abs(a-b)<=t,`${msg} expected ${b}, got ${a}`)}
const ctx={window:{},TextDecoder,TextEncoder,ArrayBuffer,DataView,Uint8Array,Math,console};ctx.globalThis=ctx.window;vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname,'..','csg-engine.js'),'utf8'),ctx);
const C=ctx.window.CSGEngine,A=require('../analyze-engine.js');
const tris=p=>A.trianglesFromPolygons(p);
const box=(x,y,z,c={x:0,y:0,z:0})=>tris(C.cube(c,{x,y,z}));

close(A.measure({x:0,y:0,z:0},{x:3,y:4,z:0}).distance,5);
close(A.measure({x:1,y:2,z:3},{x:4,y:6,z:15}).distance,13);
let base=box(100,80,40),bs=A.bounds(base).size;close(bs.x,100);close(bs.y,80);close(bs.z,40);
close(A.volume(base),320000,1e-6);close(A.surfaceArea(base),30400,1e-6);
close(A.volume(A.applyMatrix(base,A.translation(12,-7,33))),A.volume(base),1e-6);
let sphere=tris(C.sphere({x:0,y:0,z:0},10,96,48)),sv=A.volume(sphere),exact=4/3*Math.PI*1000;assert.ok(Math.abs(sv-exact)/exact<.01);
let e=A.printEstimate(base,{material:'PLA',quality:'balanced'});close(e.grams,e.plasticCm3*1.24,1e-9);
assert.ok(A.printEstimate(base,{material:'PLA',quality:'quality'}).plasticCm3>A.printEstimate(base,{material:'PLA',quality:'fast'}).plasticCm3);

let rz=A.applyMatrix(base,A.rotationZ(90)),rs=A.bounds(rz).size;close(rs.x,80);close(rs.y,100);
close(A.volume(A.applyMatrix(base,A.scaling(.5,.5,.5))),A.volume(base)/8);
close(A.volume(A.applyMatrix(base,A.mirror('x'))),A.volume(base));
let r37=A.applyMatrix(A.applyMatrix(base,A.rotationZ(37)),A.rotationZ(-37)),r37s=A.bounds(r37).size;close(r37s.x,100,1e-5);close(r37s.y,80,1e-5);
let on=A.placeOnBed(A.applyMatrix(base,A.translation(30,-20,10))),ob=A.bounds(on);close(ob.min.z,0);close((ob.min.x+ob.max.x)/2,0);close((ob.min.y+ob.max.y)/2,0);

let bed=A.findOverhangs(A.placeOnBed(base));close(bed.area,0);close(bed.bedArea,8000);
let post=C.cube({x:0,y:0,z:15},{x:20,y:20,z:30}),bar=C.cube({x:0,y:0,z:35},{x:80,y:20,z:10}),tshape=tris(C.csgUnion(post,bar)),toh=A.findOverhangs(A.placeOnBed(tshape));close(toh.area,1200,1e-4);
function tiltedDownFace(degFromDown){const a={x:0,y:0,z:10},b={x:0,y:10,z:10},c={x:10,y:0,z:10};return A.applyMatrix([{a,b,c}],A.rotationX(degFromDown))[0];}
assert.equal(A.findOverhangs([tiltedDownFace(50)]).indices.length,0);
assert.equal(A.findOverhangs([tiltedDownFace(20)]).indices.length,1);

for(const d of[{x:1,y:0,z:0},{x:0,y:1,z:0},{x:0,y:0,z:1},{x:-1,y:0,z:0}]){const R=A.rotationBetween(d,{x:0,y:0,z:-1}),p=A.transformPoint(R,d);close(p.x,0,1e-6);close(p.y,0,1e-6);close(p.z,-1,1e-6);}
close(A.determinant3(A.rotationZ(32)),1,1e-9);
let ao=A.autoOrient(tshape);close(ao.overhangArea,0,1e-4);
let sa=A.autoOrient(box(10,60,100));close(sa.size.z,10,1e-5);
assert.equal(A.fitsBed(box(250,10,10)),false);

let p=A.toParent({x:3,y:2},{x:1,y:-1,z:0});close(p.x,4);close(p.y,1);
let p90=A.toParent({rz:90},{x:1,y:0,z:0});close(p90.x,0,1e-9);close(p90.y,1,1e-9);
let both=A.toParent({x:3,y:1,rz:90},{x:1,y:0,z:0});close(both.x,3,1e-9);close(both.y,2,1e-9);
let orig={x:2.4,y:-1.2,z:5},f={x:3,y:1,z:2,rx:7,ry:11,rz:29},fw=A.toParent(f,orig),back=A.fromParent(f,fw);close(back.x,orig.x,1e-8);close(back.y,orig.y,1e-8);close(back.z,orig.z,1e-8);
let T=A.frameMatrix({x:3,y:1,z:2,rz:23}),I=A.multiply(T,A.invertRigid(T));[0,5,10,15].forEach(i=>close(I[i],1,1e-8));
let frames={Joint:{parent:'F',z:40},Carrier:{parent:'Joint',x:10,rz:90}},wp=A.transformPoint(A.worldMatrix(frames,'Carrier'),{x:5,y:0,z:0});close(wp.x,10,1e-8);close(wp.y,5,1e-8);close(wp.z,40,1e-8);
assert.throws(()=>A.worldMatrix({A:{parent:'B'},B:{parent:'A'}},'A'),/loop/i);

let bin=A.toBinarySTL(base,'base'),round=tris(C.parseSTL(bin));assert.equal(round.length,base.length);close(A.volume(round),A.volume(base),1e-3);
let c1={name:'A',tris:box(10,10,10,{x:0,y:0,z:0})},c2={name:'B',tris:box(10,10,10,{x:4,y:0,z:0})},c3={name:'C',tris:box(10,10,10,{x:30,y:0,z:0})};
assert.equal(A.pairwiseClashes([c1,c2,c3]).length,1);
assert.equal(A.pairwiseClashes([c1,c3]).length,0);
assert.equal(A.pairwiseGeometryClashes([c1,c2]).length,1);
assert.equal(A.pairwiseGeometryClashes([c1,c3]).length,0);
let inner={name:'Inner',tris:box(2,2,2,{x:0,y:0,z:0})},outer={name:'Outer',tris:box(20,20,20,{x:0,y:0,z:0})};
assert.equal(A.pairwiseGeometryClashes([inner,outer]).length,1);
let ta={a:{x:0,y:0,z:0},b:{x:3,y:0,z:0},c:{x:0,y:3,z:0}},tb={a:{x:1,y:1,z:-1},b:{x:1,y:1,z:1},c:{x:2,y:1,z:0}};
assert.equal(A.trianglesIntersect(ta,tb),true);
console.log('analyze-engine: all required tests passed');