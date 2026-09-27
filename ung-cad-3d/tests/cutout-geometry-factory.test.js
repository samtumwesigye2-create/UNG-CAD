const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
class Shape{constructor(){this.ops=[]}moveTo(...a){this.ops.push(['M',...a])}lineTo(...a){this.ops.push(['L',...a])}absarc(...a){this.ops.push(['A',...a])}quadraticCurveTo(...a){this.ops.push(['Q',...a])}bezierCurveTo(...a){this.ops.push(['B',...a])}closePath(){this.ops.push(['Z'])}}
class ExtrudeGeometry{constructor(shape,settings){this.shape=shape;this.settings=settings}translate(...a){this.translation=a}}
class MeshBasicMaterial{constructor(o){Object.assign(this,o)}}class Mesh{constructor(g,m){this.geometry=g;this.material=m;this.position={set:(...a)=>this.pos=a};this.rotation={z:0};this.userData={}}}
const window={THREE:{Shape,ExtrudeGeometry,MeshBasicMaterial,Mesh}};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'..','cutout-geometry-factory.js'),'utf8'),{window});
const base={component_id:'x',position:{x_mm:2,y_mm:3},rotation:90,clearance_mm:.2,depth_mm:-1};
let m=window.UngCadGeometryFactory.createCutoutMesh({...base,type:'rectangular',geometry_payload:{width_mm:10,height_mm:5,corner_radius_mm:1}},4);
assert.equal(m.geometry.settings.depth,6);assert.equal(m.pos[0],2);
m=window.UngCadGeometryFactory.createCutoutMesh({...base,type:'arbitrary_custom',geometry_payload:{vertices:[[0,0],[10,0],[10,10],[0,10]],segments:[{start_idx:0,end_idx:1,type:'linear'},{start_idx:1,end_idx:2,type:'arc',arc_bulge:1},{start_idx:2,end_idx:3,type:'bezier',control_points:[[5,12]]},{start_idx:3,end_idx:0,type:'linear'}]}},4);
assert(m.geometry.shape.ops.some(x=>x[0]==='A'));assert(m.geometry.shape.ops.some(x=>x[0]==='Q'));
console.log('cutout geometry factory tests passed');
