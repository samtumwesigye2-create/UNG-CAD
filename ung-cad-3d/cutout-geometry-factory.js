/* UNG-CAD parametric cutout -> Three.js cutter mesh. Global build: THREE must be loaded first. */
(function(root){
class UngCadGeometryFactory {
 static createCutoutMesh(data,panelThickness){
  if(!root.THREE)throw new Error("THREE runtime required");
  if(!data||!Number.isFinite(panelThickness)||panelThickness<=0)throw new Error("valid cutout and panel thickness required");
  const THREE=root.THREE,shape=new THREE.Shape(),g=data.geometry_payload||data.dimensions||{},clearance=Number(data.clearance_mm)||0;
  const depth=data.depth_mm===-1?panelThickness+2:Number(data.depth_mm);
  if(!(depth>0))throw new Error("cut depth must be positive or -1");
  switch(data.type){
   case "circular":{
    const radius=Number(g.diameter_mm)/2+clearance;if(!(radius>0))throw new Error("invalid circle");
    shape.absarc(0,0,radius,0,Math.PI*2,false);break;
   }
   case "rectangular":case "usb_c":case "ethernet":{
    const w=Number(g.width_mm)+2*clearance,h=Number(g.height_mm)+2*clearance;
    let r=Math.max(0,Number(g.corner_radius_mm)||0);r=Math.min(r,w/2,h/2);
    if(!(w>0&&h>0))throw new Error("invalid rectangle");
    shape.moveTo(-w/2+r,-h/2);shape.lineTo(w/2-r,-h/2);
    if(r)shape.absarc(w/2-r,-h/2+r,r,-Math.PI/2,0,false);else shape.lineTo(w/2,-h/2);
    shape.lineTo(w/2,h/2-r);if(r)shape.absarc(w/2-r,h/2-r,r,0,Math.PI/2,false);
    shape.lineTo(-w/2+r,h/2);if(r)shape.absarc(-w/2+r,h/2-r,r,Math.PI/2,Math.PI,false);
    shape.lineTo(-w/2,-h/2+r);if(r)shape.absarc(-w/2+r,-h/2+r,r,Math.PI,Math.PI*1.5,false);
    shape.closePath();break;
   }
   case "arbitrary_custom":{
    const vertices=g.vertices||[],segments=g.segments||[];if(vertices.length<3||segments.length<3)throw new Error("invalid custom boundary");
    const first=vertices[segments[0].start_idx];shape.moveTo(first[0],first[1]);
    for(const seg of segments){
     const p1=vertices[seg.start_idx],p2=vertices[seg.end_idx];if(!p1||!p2)throw new Error("segment index out of range");
     if(seg.type==="linear"){shape.lineTo(p2[0],p2[1]);continue;}
     if(seg.type==="bezier"){
      const cp=seg.control_points||[];
      if(cp.length===1)shape.quadraticCurveTo(cp[0][0],cp[0][1],p2[0],p2[1]);
      else if(cp.length===2)shape.bezierCurveTo(cp[0][0],cp[0][1],cp[1][0],cp[1][1],p2[0],p2[1]);
      else throw new Error("Bezier requires one or two control points");
      continue;
     }
     if(seg.type==="arc"){
      const b=Number(seg.arc_bulge);if(!Number.isFinite(b)||Math.abs(b)<1e-12){shape.lineTo(p2[0],p2[1]);continue;}
      const dx=p2[0]-p1[0],dy=p2[1]-p1[1],chord=Math.hypot(dx,dy);if(chord<=0)throw new Error("zero-length arc");
      const mx=(p1[0]+p2[0])/2,my=(p1[1]+p2[1])/2;
      const signedOffset=chord*(1-b*b)/(4*b),cx=mx-dy/chord*signedOffset,cy=my+dx/chord*signedOffset;
      const radius=chord*(1+b*b)/(4*Math.abs(b)),a0=Math.atan2(p1[1]-cy,p1[0]-cx),a1=Math.atan2(p2[1]-cy,p2[0]-cx);
      shape.absarc(cx,cy,radius,a0,a1,b<0);continue;
     }
     throw new Error("unsupported custom segment");
    }
    shape.closePath();break;
   }
   default:throw new Error("unsupported cutout type: "+data.type);
  }
  const geometry=new THREE.ExtrudeGeometry(shape,{depth,bevelEnabled:false,steps:1,curveSegments:48});
  if(data.depth_mm===-1)geometry.translate(0,0,-1);
  const mesh=new THREE.Mesh(geometry,new THREE.MeshBasicMaterial({color:0xff3344,wireframe:true}));
  mesh.name="UNG_CUTOUT_"+data.component_id;mesh.userData={ungCutout:true,componentId:data.component_id};
  mesh.position.set(Number(data.position?.x_mm)||0,Number(data.position?.y_mm)||0,0);
  mesh.rotation.z=(Number(data.rotation)||0)*Math.PI/180;return mesh;
 }
}
root.UngCadGeometryFactory=UngCadGeometryFactory;
})(window);
