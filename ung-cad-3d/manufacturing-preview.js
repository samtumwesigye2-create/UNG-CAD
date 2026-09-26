import * as THREE from 'three';
import { OrbitControls } from 'https://cdn.jsdelivr.net/npm/three@0.140.0/examples/jsm/controls/OrbitControls.js';
const A=window.UNGAnalyze,previewEl=document.getElementById('preview3d'),placeholder=document.getElementById('previewPlaceholder'),previewStats=document.getElementById('previewStats');
const scene=new THREE.Scene();scene.background=new THREE.Color(0x0f1b4d);
const camera=new THREE.PerspectiveCamera(50,1,.1,4000);camera.up.set(0,0,1);
const renderer=new THREE.WebGLRenderer({antialias:true});previewEl.appendChild(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);
scene.add(new THREE.AmbientLight(0xffffff,.75));const dl=new THREE.DirectionalLight(0xffffff,.9);dl.position.set(150,-180,220);scene.add(dl);
const grid=new THREE.GridHelper(220,22,0x475569,0x1e293b);grid.rotation.x=Math.PI/2;scene.add(grid);scene.add(new THREE.AxesHelper(40));
let current={label:null,original:null,tris:null,mesh:null,changed:false,overhangs:null},assemblyMeshes=[],assemblyParts=[],assemblyMode=false,measureMode=false,picks=[],measureObjects=[];
const palette=[0x3b82f6,0x8b5cf6,0x10b981,0xf59e0b,0xec4899,0x22c55e];

function resize(){const w=previewEl.clientWidth,h=previewEl.clientHeight||320;camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h);}
window.addEventListener('resize',resize);(function frame(){requestAnimationFrame(frame);controls.update();renderer.render(scene,camera);})();
function clearMesh(m){if(m){scene.remove(m);m.geometry?.dispose();m.material?.dispose();}}
let openEdgeLines=null;
function drawOpenEdges(segments){clearMesh(openEdgeLines);openEdgeLines=null;if(!segments||!segments.length)return;const pos=[];for(const [a,b] of segments)pos.push(a.x,a.y,a.z,b.x,b.y,b.z);const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));openEdgeLines=new THREE.LineSegments(g,new THREE.LineBasicMaterial({color:0xff0000,linewidth:3}));scene.add(openEdgeLines);}
function geomFromTris(tris,redSet=null,color=0x3b82f6){
 const pos=[],col=[];const c0=new THREE.Color(color),cr=new THREE.Color(0xef4444);
 tris.forEach((t,i)=>{const cc=redSet&&redSet.has(i)?cr:c0;for(const p of[t.a,t.b,t.c]){pos.push(p.x,p.y,p.z);col.push(cc.r,cc.g,cc.b);}});
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('color',new THREE.Float32BufferAttribute(col,3));g.computeVertexNormals();return g;
}
function meshFromTris(tris,redSet=null,color=0x3b82f6){return new THREE.Mesh(geomFromTris(tris,redSet,color),new THREE.MeshStandardMaterial({vertexColors:true,side:THREE.DoubleSide}));}
function statsText(label,tris){const b=A.bounds(tris),vol=A.volume(tris),fits=A.fitsBed(tris);return label+'\n\nDimensions (W × D × H):\n'+b.size.x.toFixed(1)+' × '+b.size.y.toFixed(1)+' × '+b.size.z.toFixed(1)+' mm\n\nVolume: '+(vol/1000).toFixed(2)+' cm³\nTriangles: '+tris.length+'\n\n'+(fits?'✓ Fits Adventurer 5M bed':'⚠ Exceeds Adventurer 5M 220 × 220 × 220 mm');}
function frameCurrent(){
 const b=A.bounds(current.tris),d=Math.max(b.size.x,b.size.y,b.size.z,10)*1.8;camera.position.set(d,-d,d);controls.target.set(0,0,b.size.z/2);controls.update();
}
function redraw(red=false){
 if(!current.tris)return;clearMesh(current.mesh);const set=red&&current.overhangs?new Set(current.overhangs.indices):null;current.mesh=meshFromTris(current.tris,set);scene.add(current.mesh);previewStats.textContent=statsText(current.label,current.tris);if(window.__refreshAnalyzeEstimate)window.__refreshAnalyzeEstimate();resize();
}
function setCurrent(label,tris,remember=true){if(remember)current.original=tris.map(t=>({a:{...t.a},b:{...t.b},c:{...t.c}}));current.label=label;current.tris=A.placeOnBed(tris);current.changed=false;current.overhangs=null;placeholder.style.display='none';redraw();frameCurrent();runManufacturingPreflight();if(window.__analyzeReady)window.__analyzeReady();}
function runManufacturingPreflight(){
 const gate=window.__setManufacturingPreflight;if(!gate||!current.tris||!current.tris.length)return;
 try{
  const b=A.bounds(current.tris),finite=[b.min.x,b.min.y,b.min.z,b.max.x,b.max.y,b.max.z].every(Number.isFinite);
  if(!finite||current.tris.length<4){gate('BLOCKED','invalid or empty printable geometry.');return;}
  if(!A.fitsBed(current.tris)){gate('BLOCKED','model exceeds the Adventurer 5M 220 × 220 × 220 mm build volume.');return;}
  const manifold=A.checkManifold(current.tris);current.manifold=manifold;drawOpenEdges(manifold.watertight?[]:manifold.openSegments.concat(manifold.nonManifoldSegments));
  if(!manifold.watertight){gate('BLOCKED','geometry is not watertight — '+manifold.openEdges+' open edge(s) and '+manifold.nonManifoldEdges+' non-manifold edge(s) found (highlighted in red).');return;}
  const oh=A.findOverhangs(current.tris),area=A.surfaceArea(current.tris),ratio=area?oh.area/area:0;
  if(ratio>.35){gate('PASS','geometry is valid and fits the printer; heavy overhangs detected — supports/orientation required.');return;}
  gate('PASS','geometry is valid, fits the printer and may proceed to Auto Prepare.');
 }catch(e){gate('BLOCKED','geometry validation failed: '+e.message);}
}
window.__runManufacturingPreflight=runManufacturingPreflight;
window.__previewSTL=function(label,arrayBuffer){try{const polys=window.CSGEngine.parseSTL(arrayBuffer),tris=A.trianglesFromPolygons(polys);if(!tris.length)throw Error('Could not read geometry');assemblyMode=false;for(const m of assemblyMeshes)clearMesh(m);assemblyMeshes=[];setCurrent(label,tris,true);}catch(e){previewStats.textContent='Preview failed — '+e.message;}};
window.__analyzeGetCurrent=()=>current.tris;
window.__analyzeGetOriginal=()=>current.original;
window.__analyzeApplyMatrix=function(M){if(!current.tris)return null;current.tris=A.placeOnBed(A.applyMatrix(current.tris,M));current.changed=true;current.overhangs=null;redraw();if(window.__analyzeChanged)window.__analyzeChanged(true);return A.bounds(current.tris);};
window.__analyzeReset=function(){if(!current.original)return;current.tris=A.placeOnBed(current.original.map(t=>({a:{...t.a},b:{...t.b},c:{...t.c}})));current.changed=false;current.overhangs=null;redraw();if(window.__analyzeChanged)window.__analyzeChanged(false);};
window.__analyzeSupport=function(show=true){if(!current.tris)return null;current.overhangs=A.findOverhangs(current.tris);redraw(show);return current.overhangs;};
window.__analyzeHideSupport=()=>redraw(false);
window.__analyzeRepair=function(){if(!current.tris)return null;const before=A.checkManifold(current.tris);if(before.watertight)return{...before,patched:0,alreadyOk:true};const result=A.repairMesh(current.tris);current.tris=result.tris;current.changed=true;current.overhangs=null;redraw();if(window.__analyzeChanged)window.__analyzeChanged(true);runManufacturingPreflight();return{...A.checkManifold(current.tris),patched:result.patched,loopsFilled:result.loopsFilled,before};};
window.__analyzeBestPosition=function(){if(!current.tris)return null;const r=A.autoOrient(current.tris),before=r.overhangAreaBefore;current.tris=A.placeOnBed(A.applyMatrix(current.tris,r.matrix));current.changed=true;current.overhangs=A.findOverhangs(current.tris);redraw(true);if(window.__analyzeChanged)window.__analyzeChanged(true);return{...r,overhangAreaBefore:before,overhangArea:current.overhangs.area,size:A.bounds(current.tris).size,fits:A.fitsBed(current.tris)};};

function clearMeasure(){for(const o of measureObjects)scene.remove(o);measureObjects=[];picks=[];if(window.__measureResult)window.__measureResult(null);}
window.__analyzeSetMeasure=function(on){measureMode=!!on;if(!on)clearMeasure();renderer.domElement.style.cursor=on?'crosshair':'grab';};
window.__analyzeClearMeasure=clearMeasure;
let pointerDown=null;renderer.domElement.addEventListener('pointerdown',e=>pointerDown={x:e.clientX,y:e.clientY});
renderer.domElement.addEventListener('pointerup',e=>{if(!measureMode||!pointerDown||Math.hypot(e.clientX-pointerDown.x,e.clientY-pointerDown.y)>6)return;const rect=renderer.domElement.getBoundingClientRect(),mouse=new THREE.Vector2((e.clientX-rect.left)/rect.width*2-1,-((e.clientY-rect.top)/rect.height)*2+1),ray=new THREE.Raycaster();ray.setFromCamera(mouse,camera);const targets=assemblyMode?assemblyMeshes:(current.mesh?[current.mesh]:[]),hit=ray.intersectObjects(targets,false)[0];if(!hit)return;picks.push(hit.point.clone());const dotg=new THREE.SphereGeometry(1.5,12,8),mat=new THREE.MeshBasicMaterial({color:0xfacc15}),dm=new THREE.Mesh(dotg,mat);dm.position.copy(hit.point);scene.add(dm);measureObjects.push(dm);if(picks.length===2){const pts=[picks[0],picks[1]],g=new THREE.BufferGeometry().setFromPoints(pts),line=new THREE.Line(g,new THREE.LineBasicMaterial({color:0xfacc15}));scene.add(line);measureObjects.push(line);const r=A.measure({x:pts[0].x,y:pts[0].y,z:pts[0].z},{x:pts[1].x,y:pts[1].y,z:pts[1].z});if(window.__measureResult)window.__measureResult(r);picks=[];}});

window.__showAssembly=async function(parts,frames){
 assemblyMode=true;const gate=window.__setManufacturingPreflight;if(gate)gate('RUNNING','validating complete assembly for collisions and minimum clearance…');clearMesh(current.mesh);current.mesh=null;for(const m of assemblyMeshes)clearMesh(m);assemblyMeshes=[];assemblyParts=[];clearMeasure();
 let all=[];for(let i=0;i<parts.length;i++){const p=parts[i],polys=window.CSGEngine.parseSTL(p.bytes),tris=A.trianglesFromPolygons(polys),M=A.worldMatrix(frames,p.name),world=A.applyMatrix(tris,M),m=meshFromTris(world,null,palette[i%palette.length]);scene.add(m);assemblyMeshes.push(m);assemblyParts.push({name:p.name,tris:world,mesh:m});all=all.concat(world);}
 const b=A.bounds(all),d=Math.max(b.size.x,b.size.y,b.size.z,10)*1.6;camera.position.set(d,-d,d);controls.target.set((b.min.x+b.max.x)/2,(b.min.y+b.max.y)/2,(b.min.z+b.max.z)/2);controls.update();previewStats.textContent='Assembly view\n\nOverall size:\n'+b.size.x.toFixed(1)+' × '+b.size.y.toFixed(1)+' × '+b.size.z.toFixed(1)+' mm\n\n'+parts.map((p,i)=>'● '+p.name).join('\n');resize();const threshold=Math.max(0,Number(document.getElementById('clearanceMm')?.value)||0.40);const result=window.__runAssemblyManufacturingPreflight?window.__runAssemblyManufacturingPreflight(threshold):null;return {...b,preflight:result};
};
window.__checkAssemblyClashes=function(){
 const hits=A.pairwiseClashes(assemblyParts);
 const hitNames=new Set(hits.flatMap(h=>[h.a,h.b]));
 assemblyParts.forEach((part,i)=>{part.mesh.material.color.setHex(hitNames.has(part.name)?0xef4444:palette[i%palette.length]);});
 return hits;
};
window.__checkAssemblyGeometryClashes=function(){
 const hits=A.pairwiseGeometryClashes(assemblyParts,{limitPerPair:128});
 const hitNames=new Set(hits.flatMap(h=>[h.a,h.b]));
 assemblyParts.forEach((part,i)=>{part.mesh.material.color.setHex(hitNames.has(part.name)?0xff7a18:palette[i%palette.length]);});
 return hits;
};
window.__checkAssemblyClearance=function(threshold){
 const hits=A.pairwiseClearances(assemblyParts,threshold);
 const hitNames=new Set(hits.flatMap(h=>[h.a,h.b]));
 assemblyParts.forEach((part,i)=>{part.mesh.material.color.setHex(hitNames.has(part.name)?0xfacc15:palette[i%palette.length]);});
 return hits;
};
window.__assemblyFitReport=function(){return A.pairwiseDistances(assemblyParts);};\nwindow.__assemblyEstimate=function(options={}){if(!assemblyMode||!assemblyParts.length)return null;return A.assemblyEstimate(assemblyParts,options);};
window.__runAssemblyManufacturingPreflight=function(threshold=0.40){
 const gate=window.__setManufacturingPreflight;
 if(!gate)return{pass:false,reason:'Manufacturing gate unavailable'};
 if(!assemblyMode||assemblyParts.length<2){gate('BLOCKED','assembly validation requires at least two loaded assembly parts.');return{pass:false,reason:'assembly not loaded'};}
 try{
  const clashes=A.pairwiseGeometryClashes(assemblyParts,{limitPerPair:128});
  if(clashes.length){const h=clashes[0];gate('BLOCKED','assembly collision: '+h.a+' intersects '+h.b+'.');return{pass:false,clashes};}
  const enclosure=/lid|cover|top|chassis|case|shell|base/i, internal=/pcb|board|pico|pi|camera|sensor|radio|network|power|battery|fan|cable|connector|post/i;
  const enclosureParts=assemblyParts.filter(p=>enclosure.test(p.name)),internalParts=assemblyParts.filter(p=>internal.test(p.name));
  if(enclosureParts.length&&internalParts.length){
   const mating=A.pairwiseGeometryClashes([...enclosureParts,...internalParts],{limitPerPair:128}).filter(h=>enclosure.test(h.a)&&internal.test(h.b)||enclosure.test(h.b)&&internal.test(h.a));
   if(mating.length){const h=mating[0];gate('BLOCKED','enclosure/lid fit failure: '+h.a+' interferes with '+h.b+'.');return{pass:false,mating};}
  }
  const clearances=A.pairwiseClearances(assemblyParts,threshold);
  if(clearances.length){const h=clearances[0];gate('BLOCKED','minimum '+threshold.toFixed(2)+' mm clearance failed between '+h.a+' and '+h.b+' ('+h.distance.toFixed(3)+' mm).');return{pass:false,clearances};}
  const connector=/usb|ethernet|rj45|ffc|fpc|camera.?cable|power.?jack|connector|port/i, keepout=/keepout|insertion|plug.?clearance|cable.?exit|service.?space/i;
  const connectors=assemblyParts.filter(p=>connector.test(p.name)),keepouts=assemblyParts.filter(p=>keepout.test(p.name));
  if(connectors.length&&!keepouts.length){gate('BLOCKED','connector hardware is present but no verified insertion/cable-exit clearance geometry is defined.');return{pass:false,unverifiedConnectors:connectors.map(p=>p.name)};}
  if(keepouts.length){
   const obstacles=assemblyParts.filter(p=>!keepout.test(p.name));
   for(const zone of keepouts){
    const conflicts=A.pairwiseGeometryClashes([zone,...obstacles],{limitPerPair:64}).filter(h=>h.a===zone.name||h.b===zone.name);
    if(conflicts.length){const h=conflicts[0],other=h.a===zone.name?h.b:h.a;gate('BLOCKED','connector/cable access blocked: '+zone.name+' intersects '+other+'.');return{pass:false,connectorClearance:conflicts};}
   }
  }
  const board=/pcb|board|pico|raspberry.?pi|camera|radio|network|power/i, mount=/mount|standoff|post|boss|support/i, hole=/mount.?hole|screw.?hole|fastener.?hole/i;
  const boards=assemblyParts.filter(p=>board.test(p.name)),mounts=assemblyParts.filter(p=>mount.test(p.name)),holes=assemblyParts.filter(p=>hole.test(p.name));
  for(const b of boards){
   const bb=A.bounds(b.tris),nearMounts=mounts.filter(m=>{const mb=A.bounds(m.tris),cx=(mb.min.x+mb.max.x)/2,cy=(mb.min.y+mb.max.y)/2;return cx>=bb.min.x-threshold&&cx<=bb.max.x+threshold&&cy>=bb.min.y-threshold&&cy<=bb.max.y+threshold&&mb.max.z<=bb.max.z+threshold;});
   if(!nearMounts.length){gate('BLOCKED','unsupported board: '+b.name+' has no verified mounting post/standoff beneath its footprint.');return{pass:false,unsupportedBoard:b.name};}
   const relatedHoles=holes.filter(h=>h.name.toLowerCase().includes(b.name.toLowerCase())||b.name.toLowerCase().includes(h.name.toLowerCase().replace(/mount.?hole|screw.?hole|fastener.?hole/ig,'').trim()));
   if(relatedHoles.length){
    for(const h of relatedHoles){const hb=A.bounds(h.tris),hc={x:(hb.min.x+hb.max.x)/2,y:(hb.min.y+hb.max.y)/2};const aligned=nearMounts.some(m=>{const mb=A.bounds(m.tris),mc={x:(mb.min.x+mb.max.x)/2,y:(mb.min.y+mb.max.y)/2};return Math.hypot(mc.x-hc.x,mc.y-hc.y)<=threshold;});if(!aligned){gate('BLOCKED','mounting alignment failure: '+h.name+' has no post/standoff center within '+threshold.toFixed(2)+' mm.');return{pass:false,misalignedHole:h.name};}}
   }
  }
  gate('PASS','assembly geometry has no intersections and meets '+threshold.toFixed(2)+' mm minimum clearance.');
  return{pass:true,clashes:[],clearances:[]};
 }catch(e){gate('BLOCKED','assembly validation failed: '+e.message);return{pass:false,error:e.message};}
};
window.__backSingle=function(){assemblyMode=false;for(const m of assemblyMeshes)clearMesh(m);assemblyMeshes=[];assemblyParts=[];if(current.tris)redraw();};
resize();