/* UNG-CAD structural rib -> Three.js reinforcement mesh. Global build. */
(function(root){
class UngCadRibFactory {
 static createRibMesh(ribData,panelThickness){
  if(!root.THREE)throw new Error("THREE runtime required");
  if(!ribData||!Number.isFinite(panelThickness)||panelThickness<=0)throw new Error("valid rib and panel thickness required");
  const THREE=root.THREE,p1=ribData.start_point,p2=ribData.end_point;
  const thickness=Number(ribData.thickness_mm),height=Number(ribData.height_mm);
  if(!(thickness>0&&height>0))throw new Error("rib thickness and height must be positive");
  const dx=Number(p2.x)-Number(p1.x),dy=Number(p2.y)-Number(p1.y),length=Math.hypot(dx,dy);
  if(!(length>0))throw new Error("rib start and end points must differ");
  const midX=(Number(p1.x)+Number(p2.x))/2,midY=(Number(p1.y)+Number(p2.y))/2,angle=Math.atan2(dy,dx);
  let geometry;
  if((ribData.profile_type||"rectangular")==="tapered_draft"){
   // Cross-section is length (X) by height (Z); extrusion supplies rib width.
   // End taper is bounded so short ribs cannot invert.
   const inset=Math.min(1,length/4),shape=new THREE.Shape();
   shape.moveTo(-length/2,0);shape.lineTo(length/2,0);shape.lineTo(length/2-inset,height);shape.lineTo(-length/2+inset,height);shape.closePath();
   geometry=new THREE.ExtrudeGeometry(shape,{depth:thickness,bevelEnabled:false,steps:1});
   geometry.translate(0,0,-thickness/2);
   // ExtrudeGeometry height currently lies in local Y. Rotate it into local Z,
   // leaving extrusion depth as local Y (rib thickness).
   geometry.rotateX(Math.PI/2);
  } else if((ribData.profile_type||"rectangular")==="rectangular"){
   // local X=length, local Y=thickness, local Z=height
   geometry=new THREE.BoxGeometry(length,thickness,height);
  } else throw new Error("unsupported rib profile");
  const material=new THREE.MeshBasicMaterial({color:0x1a73e8,wireframe:false,transparent:true,opacity:.8});
  const mesh=new THREE.Mesh(geometry,material);
  // Contract: panel occupies Z=0..panelThickness; backside is negative Z.
  // Rib touches Z=0 and grows into negative Z.
  mesh.position.set(midX,midY,-height/2);mesh.rotation.z=angle;
  mesh.name="UNG_RIB_"+ribData.rib_id;mesh.userData={ungStructuralRib:true,ribId:ribData.rib_id,panelThickness};
  return mesh;
 }
}
root.UngCadRibFactory=UngCadRibFactory;
})(window);
