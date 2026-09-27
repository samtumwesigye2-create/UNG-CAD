/* UNG-CAD Field Visualization Layer
 * Three.js overlays for vector fields, surface normals, scalar samples,
 * streamlines and curvature/concavity inspection.
 */
(function(global){
  const state={group:null,mode:"off"};
  function group(scene){
    if(state.group) scene.remove(state.group);
    state.group=new THREE.Group(); state.group.name="UNG_FIELD_OVERLAY"; scene.add(state.group);
    return state.group;
  }
  function clear(scene){ if(state.group) scene.remove(state.group); state.group=null; state.mode="off"; }
  function bounds(mesh){
    const b=new THREE.Box3().setFromObject(mesh),s=new THREE.Vector3(); b.getSize(s);
    return {b,s,step:Math.max(s.x,s.y,s.z)/6||1};
  }
  function vectorArrows(scene,mesh,field){
    const g=group(scene),{b,s,step}=bounds(mesh),n=5;
    for(let ix=0;ix<n;ix++)for(let iy=0;iy<n;iy++)for(let iz=0;iz<n;iz++){
      const p=new THREE.Vector3(b.min.x+s.x*ix/(n-1),b.min.y+s.y*iy/(n-1),b.min.z+s.z*iz/(n-1));
      const v=field(p); if(!v||v.lengthSq()<1e-12)continue;
      const d=v.clone().normalize(),len=Math.min(step*.8,Math.max(step*.18,v.length()*step*.25));
      g.add(new THREE.ArrowHelper(d,p,len,0x22d3ee,Math.min(len*.3,.25),Math.min(len*.15,.12)));
    } state.mode="vectors"; return g;
  }
  function normals(scene,mesh){
    const g=group(scene),geo=mesh.geometry;if(!geo?.attributes?.position)return g;
    const pos=geo.attributes.position,norm=geo.attributes.normal; if(!norm)geo.computeVertexNormals();
    const na=geo.attributes.normal,skip=Math.max(1,Math.floor(pos.count/180));
    mesh.updateMatrixWorld(true);
    for(let i=0;i<pos.count;i+=skip){
      const p=new THREE.Vector3().fromBufferAttribute(pos,i).applyMatrix4(mesh.matrixWorld);
      const d=new THREE.Vector3().fromBufferAttribute(na,i).transformDirection(mesh.matrixWorld).normalize();
      g.add(new THREE.ArrowHelper(d,p,.35,0x4ade80,.12,.06));
    } state.mode="normals";return g;
  }
  function radialField(center=new THREE.Vector3()){
    return p=>p.clone().sub(center).normalize();
  }
  function vortexField(center=new THREE.Vector3()){
    return p=>{const q=p.clone().sub(center);return new THREE.Vector3(-q.z,.15*q.y,q.x).normalize()};
  }
  function streamlines(scene,mesh,field){
    const g=group(scene),{b,s,step}=bounds(mesh);
    for(let k=0;k<12;k++){
      let p=new THREE.Vector3(b.min.x+s.x*(k%4)/3,b.min.y+s.y*Math.floor(k/4)/2,b.min.z),pts=[p.clone()];
      for(let i=0;i<80;i++){const v=field(p);if(!v||v.lengthSq()<1e-12)break;p=p.clone().add(v.clone().normalize().multiplyScalar(step*.12));pts.push(p.clone())}
      g.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),new THREE.LineBasicMaterial({color:0x38bdf8})));
    } state.mode="streamlines";return g;
  }
  function curvature(scene,mesh){
    const g=group(scene),geo=mesh.geometry;if(!geo?.attributes?.position)return g;
    if(!geo.attributes.normal)geo.computeVertexNormals();
    const pos=geo.attributes.position,n=geo.attributes.normal,pts=[],cols=[],c=new THREE.Color();
    mesh.updateMatrixWorld(true);
    for(let i=0;i<pos.count;i++){
      const p=new THREE.Vector3().fromBufferAttribute(pos,i).applyMatrix4(mesh.matrixWorld);
      const nn=new THREE.Vector3().fromBufferAttribute(n,i).transformDirection(mesh.matrixWorld);
      const score=Math.min(1,Math.abs(nn.y)); c.setHSL((1-score)*.62,1,.5);
      pts.push(p.x,p.y,p.z);cols.push(c.r,c.g,c.b);
    }
    const bg=new THREE.BufferGeometry();bg.setAttribute("position",new THREE.Float32BufferAttribute(pts,3));bg.setAttribute("color",new THREE.Float32BufferAttribute(cols,3));
    g.add(new THREE.Points(bg,new THREE.PointsMaterial({size:.055,vertexColors:true})));state.mode="curvature";return g;
  }
  global.UNGFieldViz={clear,vectorArrows,normals,streamlines,curvature,radialField,vortexField,state};
})(window);
