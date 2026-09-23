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
function setCurrent(label,tris,remember=true){if(remember)current.original=tris.map(t=>({a:{...t.a},b:{...t.b},c:{...t.c}}));current.label=label;current.tris=A.placeOnBed(tris);current.changed=false;current.overhangs=null;placeholder.style.display='none';redraw();frameCurrent();if(window.__analyzeReady)window.__analyzeReady();}
window.__previewSTL=function(label,arrayBuffer){try{const polys=window.CSGEngine.parseSTL(arrayBuffer),tris=A.trianglesFromPolygons(polys);if(!tris.length)throw Error('Could not read geometry');assemblyMode=false;for(const m of assemblyMeshes)clearMesh(m);assemblyMeshes=[];setCurrent(label,tris,true);}catch(e){previewStats.textContent='Preview failed — '+e.message;}};
window.__analyzeGetCurrent=()=>current.tris;
window.__analyzeGetOriginal=()=>current.original;
window.__analyzeApplyMatrix=function(M){if(!current.tris)return null;current.tris=A.placeOnBed(A.applyMatrix(current.tris,M));current.changed=true;current.overhangs=null;redraw();if(window.__analyzeChanged)window.__analyzeChanged(true);return A.bounds(current.tris);};
window.__analyzeReset=function(){if(!current.original)return;current.tris=A.placeOnBed(current.original.map(t=>({a:{...t.a},b:{...t.b},c:{...t.c}})));current.changed=false;current.overhangs=null;redraw();if(window.__analyzeChanged)window.__analyzeChanged(false);};
window.__analyzeSupport=function(show=true){if(!current.tris)return null;current.overhangs=A.findOverhangs(current.tris);redraw(show);return current.overhangs;};
window.__analyzeHideSupport=()=>redraw(false);
window.__analyzeBestPosition=function(){if(!current.tris)return null;const r=A.autoOrient(current.tris),before=r.overhangAreaBefore;current.tris=A.placeOnBed(A.applyMatrix(current.tris,r.matrix));current.changed=true;current.overhangs=A.findOverhangs(current.tris);redraw(true);if(window.__analyzeChanged)window.__analyzeChanged(true);return{...r,overhangAreaBefore:before,overhangArea:current.overhangs.area,size:A.bounds(current.tris).size,fits:A.fitsBed(current.tris)};};

function clearMeasure(){for(const o of measureObjects)scene.remove(o);measureObjects=[];picks=[];if(window.__measureResult)window.__measureResult(null);}
window.__analyzeSetMeasure=function(on){measureMode=!!on;if(!on)clearMeasure();renderer.domElement.style.cursor=on?'crosshair':'grab';};
window.__analyzeClearMeasure=clearMeasure;
let pointerDown=null;renderer.domElement.addEventListener('pointerdown',e=>pointerDown={x:e.clientX,y:e.clientY});
renderer.domElement.addEventListener('pointerup',e=>{if(!measureMode||!pointerDown||Math.hypot(e.clientX-pointerDown.x,e.clientY-pointerDown.y)>6)return;const rect=renderer.domElement.getBoundingClientRect(),mouse=new THREE.Vector2((e.clientX-rect.left)/rect.width*2-1,-((e.clientY-rect.top)/rect.height)*2+1),ray=new THREE.Raycaster();ray.setFromCamera(mouse,camera);const targets=assemblyMode?assemblyMeshes:(current.mesh?[current.mesh]:[]),hit=ray.intersectObjects(targets,false)[0];if(!hit)return;picks.push(hit.point.clone());const dotg=new THREE.SphereGeometry(1.5,12,8),mat=new THREE.MeshBasicMaterial({color:0xfacc15}),dm=new THREE.Mesh(dotg,mat);dm.position.copy(hit.point);scene.add(dm);measureObjects.push(dm);if(picks.length===2){const pts=[picks[0],picks[1]],g=new THREE.BufferGeometry().setFromPoints(pts),line=new THREE.Line(g,new THREE.LineBasicMaterial({color:0xfacc15}));scene.add(line);measureObjects.push(line);const r=A.measure({x:pts[0].x,y:pts[0].y,z:pts[0].z},{x:pts[1].x,y:pts[1].y,z:pts[1].z});if(window.__measureResult)window.__measureResult(r);picks=[];}});

window.__showAssembly=async function(parts,frames){
 assemblyMode=true;clearMesh(current.mesh);current.mesh=null;for(const m of assemblyMeshes)clearMesh(m);assemblyMeshes=[];assemblyParts=[];clearMeasure();
 let all=[];for(let i=0;i<parts.length;i++){const p=parts[i],polys=window.CSGEngine.parseSTL(p.bytes),tris=A.trianglesFromPolygons(polys),M=A.worldMatrix(frames,p.name),world=A.applyMatrix(tris,M),m=meshFromTris(world,null,palette[i%palette.length]);scene.add(m);assemblyMeshes.push(m);assemblyParts.push({name:p.name,tris:world,mesh:m});all=all.concat(world);}
 const b=A.bounds(all),d=Math.max(b.size.x,b.size.y,b.size.z,10)*1.6;camera.position.set(d,-d,d);controls.target.set((b.min.x+b.max.x)/2,(b.min.y+b.max.y)/2,(b.min.z+b.max.z)/2);controls.update();previewStats.textContent='Assembly view\n\nOverall size:\n'+b.size.x.toFixed(1)+' × '+b.size.y.toFixed(1)+' × '+b.size.z.toFixed(1)+' mm\n\n'+parts.map((p,i)=>'● '+p.name).join('\n');resize();return b;
};
window.__checkAssemblyClashes=function(){
 const hits=A.pairwiseClashes(assemblyParts);
 const hitNames=new Set(hits.flatMap(h=>[h.a,h.b]));
 assemblyParts.forEach((part,i)=>{part.mesh.material.color.setHex(hitNames.has(part.name)?0xef4444:palette[i%palette.length]);});
 return hits;
};
window.__backSingle=function(){assemblyMode=false;for(const m of assemblyMeshes)clearMesh(m);assemblyMeshes=[];assemblyParts=[];if(current.tris)redraw();};
resize();