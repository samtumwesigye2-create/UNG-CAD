const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
class G{translate(){return this}rotateX(){return this}}
class Shape{moveTo(){}lineTo(){}closePath(){}}
class BoxGeometry extends G{constructor(...a){super();this.args=a}}
class ExtrudeGeometry extends G{constructor(s,o){super();this.opts=o}}
class Mat{constructor(o){Object.assign(this,o)}}
class Mesh{constructor(g,m){this.geometry=g;this.material=m;this.position={set:(...v)=>this.pos=v};this.rotation={z:0};this.userData={}}}
const window={THREE:{Shape,BoxGeometry,ExtrudeGeometry,MeshBasicMaterial:Mat,Mesh}};
const ctx={window,Math,Number};vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'..','rib-geometry-factory.js'),'utf8'),ctx);
const R=window.UngCadRibFactory;
let m=R.createRibMesh({rib_id:'r',start_point:{x:10,y:10},end_point:{x:50,y:10},thickness_mm:3,height_mm:6,profile_type:'rectangular'},2);
assert.deepStrictEqual(m.geometry.args,[40,3,6]);assert.deepStrictEqual(m.pos,[30,10,-3]);assert(m.userData.ungStructuralRib);
assert.throws(()=>R.createRibMesh({rib_id:'z',start_point:{x:1,y:1},end_point:{x:1,y:1},thickness_mm:3,height_mm:6},2),/differ/);
console.log('rib-geometry-factory tests passed');
