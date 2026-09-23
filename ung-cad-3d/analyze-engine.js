(function(root,factory){
  const api=factory();
  if(typeof module!=='undefined'&&module.exports) module.exports=api;
  if(root) root.UNGAnalyze=api;
})(typeof window!=='undefined'?window:globalThis,function(){
  const EPS=1e-9;
  const v=(x=0,y=0,z=0)=>({x:+x,y:+y,z:+z});
  const sub=(a,b)=>v(a.x-b.x,a.y-b.y,a.z-b.z), mulv=(a,s)=>v(a.x*s,a.y*s,a.z*s);
  const dot=(a,b)=>a.x*b.x+a.y*b.y+a.z*b.z;
  const cross=(a,b)=>v(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x);
  const len=a=>Math.hypot(a.x,a.y,a.z), norm=a=>{const l=len(a);return l<EPS?v():mulv(a,1/l)};
  const triArea=t=>len(cross(sub(t.b,t.a),sub(t.c,t.a)))/2;
  const signedVolume=tris=>tris.reduce((s,t)=>s+dot(t.a,cross(t.b,t.c))/6,0);
  function trianglesFromPolygons(polys){const out=[];for(const p of polys||[]){const vs=p.vertices||[];for(let i=1;i<vs.length-1;i++)out.push({a:{...vs[0].pos},b:{...vs[i].pos},c:{...vs[i+1].pos}});}return out;}
  function measure(p1,p2){const dx=p2.x-p1.x,dy=p2.y-p1.y,dz=p2.z-p1.z;return{distance:Math.hypot(dx,dy,dz),dx,dy,dz};}
  function bounds(tris){if(!tris||!tris.length)return{min:v(),max:v(),size:v()};let min=v(Infinity,Infinity,Infinity),max=v(-Infinity,-Infinity,-Infinity);for(const t of tris)for(const p of[t.a,t.b,t.c]){min=v(Math.min(min.x,p.x),Math.min(min.y,p.y),Math.min(min.z,p.z));max=v(Math.max(max.x,p.x),Math.max(max.y,p.y),Math.max(max.z,p.z));}return{min,max,size:v(max.x-min.x,max.y-min.y,max.z-min.z)};}
  const volume=tris=>Math.abs(signedVolume(tris));
  const surfaceArea=tris=>tris.reduce((s,t)=>s+triArea(t),0);
  const MATERIALS={PLA:{density:1.24,price:25},PETG:{density:1.27,price:28}};
  const PROFILES={fast:{infill:.10,walls:2,flow:14},balanced:{infill:.15,walls:2,flow:10},quality:{infill:.20,walls:3,flow:6}};
  function printEstimate(tris,{material='PLA',quality='balanced'}={}){const mat=MATERIALS[material]||MATERIALS.PLA,p=PROFILES[quality]||PROFILES.balanced,vol=volume(tris),area=surfaceArea(tris),shell=Math.min(vol,area*p.walls*.42),plastic=shell+(vol-shell)*p.infill,grams=plastic/1000*mat.density,filamentM=plastic/(Math.PI*.875*.875)/1000,minutes=plastic/p.flow/60*1.35+3,cost=grams/1000*mat.price;return{volumeCm3:vol/1000,areaCm2:area/100,plasticCm3:plastic/1000,grams,filamentM,minutes,cost};}
  const identity=()=>[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
  function multiply(A,B){const C=Array(16).fill(0);for(let r=0;r<4;r++)for(let c=0;c<4;c++)for(let k=0;k<4;k++)C[r*4+c]+=A[r*4+k]*B[k*4+c];return C;}
  const rad=d=>d*Math.PI/180;
  function rotationX(d){const c=Math.cos(rad(d)),s=Math.sin(rad(d));return[1,0,0,0,0,c,-s,0,0,s,c,0,0,0,0,1];}
  function rotationY(d){const c=Math.cos(rad(d)),s=Math.sin(rad(d));return[c,0,s,0,0,1,0,0,-s,0,c,0,0,0,0,1];}
  function rotationZ(d){const c=Math.cos(rad(d)),s=Math.sin(rad(d));return[c,-s,0,0,s,c,0,0,0,0,1,0,0,0,0,1];}
  const scaling=(sx,sy,sz)=>[sx,0,0,0,0,sy,0,0,0,0,sz,0,0,0,0,1];
  const mirror=axis=>scaling(axis==='x'?-1:1,axis==='y'?-1:1,axis==='z'?-1:1);
  const translation=(tx,ty,tz)=>[1,0,0,tx,0,1,0,ty,0,0,1,tz,0,0,0,1];
  function determinant3(M){return M[0]*(M[5]*M[10]-M[6]*M[9])-M[1]*(M[4]*M[10]-M[6]*M[8])+M[2]*(M[4]*M[9]-M[5]*M[8]);}
  function transformPoint(M,p){const x=M[0]*p.x+M[1]*p.y+M[2]*p.z+M[3],y=M[4]*p.x+M[5]*p.y+M[6]*p.z+M[7],z=M[8]*p.x+M[9]*p.y+M[10]*p.z+M[11],w=M[12]*p.x+M[13]*p.y+M[14]*p.z+M[15]||1;return v(x/w,y/w,z/w);}
  function applyMatrix(tris,M){const flip=determinant3(M)<0;return tris.map(t=>{const a=transformPoint(M,t.a),b=transformPoint(M,t.b),c=transformPoint(M,t.c);return flip?{a,b:c,c:b}:{a,b,c};});}
  function placeOnBed(tris){const b=bounds(tris);return applyMatrix(tris,translation(-(b.min.x+b.max.x)/2,-(b.min.y+b.max.y)/2,-b.min.z));}
  const triangleNormal=t=>norm(cross(sub(t.b,t.a),sub(t.c,t.a)));
  function findOverhangs(tris,limitDeg=45){if(!tris.length)return{indices:[],area:0,bedArea:0};const minZ=bounds(tris).min.z,threshold=-Math.sin(rad(limitDeg)),indices=[];let area=0,bedArea=0;tris.forEach((t,i)=>{const n=triangleNormal(t),a=triArea(t),resting=Math.max(t.a.z,t.b.z,t.c.z)-minZ<=.05;if(resting&&n.z<-.99){bedArea+=a;return;}if(n.z<threshold){indices.push(i);area+=a;}});return{indices,area,bedArea};}
  function rodrigues(a,th){const{x,y,z}=a,c=Math.cos(th),s=Math.sin(th),q=1-c;return[x*x*q+c,x*y*q-z*s,x*z*q+y*s,0,y*x*q+z*s,y*y*q+c,y*z*q-x*s,0,z*x*q-y*s,z*y*q+x*s,z*z*q+c,0,0,0,0,1];}
  function rotationBetween(from,to){const f=norm(from),t=norm(to),c=Math.max(-1,Math.min(1,dot(f,t)));if(c>1-1e-10)return identity();if(c<-1+1e-10){let axis=Math.abs(f.x)<.9?cross(f,v(1,0,0)):cross(f,v(0,1,0));return rodrigues(norm(axis),Math.PI);}return rodrigues(norm(cross(f,t)),Math.acos(c));}
  function fitsBed(tris){const s=bounds(tris).size;return s.x<=220+1e-8&&s.y<=220+1e-8&&s.z<=220+1e-8;}
  function autoOrient(tris){const before=findOverhangs(placeOnBed(tris)).area,groups=new Map();for(const t of tris){const n=triangleNormal(t),key=[n.x,n.y,n.z].map(x=>Math.round(x*100)/100).join(','),g=groups.get(key)||{normal:n,area:0};g.area+=triArea(t);groups.set(key,g);}const normals=[v(1,0,0),v(-1,0,0),v(0,1,0),v(0,-1,0),v(0,0,1),v(0,0,-1),...[...groups.values()].sort((a,b)=>b.area-a.area).slice(0,24).map(g=>g.normal)];let best=null;for(const n of normals){const R=rotationBetween(n,v(0,0,-1)),placed=placeOnBed(applyMatrix(tris,R)),oh=findOverhangs(placed),a=surfaceArea(placed),s=bounds(placed).size,fit=fitsBed(placed),score=(a?oh.area/a:0)*100-(a?oh.bedArea/a:0)*20+s.z/1000+(fit?0:1000);if(!best||score<best.score)best={score,matrix:R,faceDown:n,overhangArea:oh.area,overhangAreaBefore:before,bedArea:oh.bedArea,size:s,fits:fit};}delete best.score;return best;}
  function frameMatrix({x=0,y=0,z=0,rx=0,ry=0,rz=0}={}){return multiply(translation(x,y,z),multiply(rotationZ(rz),multiply(rotationY(ry),rotationX(rx))));}
  function invertRigid(T){const Rt=[T[0],T[4],T[8],T[1],T[5],T[9],T[2],T[6],T[10]],d=v(T[3],T[7],T[11]),q=v(-(Rt[0]*d.x+Rt[1]*d.y+Rt[2]*d.z),-(Rt[3]*d.x+Rt[4]*d.y+Rt[5]*d.z),-(Rt[6]*d.x+Rt[7]*d.y+Rt[8]*d.z));return[Rt[0],Rt[1],Rt[2],q.x,Rt[3],Rt[4],Rt[5],q.y,Rt[6],Rt[7],Rt[8],q.z,0,0,0,1];}
  const toParent=(frame,point)=>transformPoint(frameMatrix(frame),point),fromParent=(frame,point)=>transformPoint(invertRigid(frameMatrix(frame)),point);
  function worldMatrix(frames,name){const visiting=new Set(),memo={};function go(n){if(memo[n])return memo[n];if(visiting.has(n))throw new Error('loop in frame attachments');visiting.add(n);const f=frames[n];if(!f)throw new Error('Unknown frame: '+n);const local=frameMatrix(f),parent=f.parent,world=(!parent||parent==='F'||parent==='Base frame (F)')?local:multiply(go(parent),local);visiting.delete(n);return memo[n]=world;}return go(name);}
  function explainTransform(frame,x){const T=frameMatrix(frame),R=[T[0],T[1],T[2],T[4],T[5],T[6],T[8],T[9],T[10]],d=v(frame.x||0,frame.y||0,frame.z||0),X=transformPoint(T,x),moved=Math.abs(d.x)+Math.abs(d.y)+Math.abs(d.z)>EPS,rotated=Math.abs(frame.rx||0)+Math.abs(frame.ry||0)+Math.abs(frame.rz||0)>EPS;const kind=moved&&rotated?'both':moved?'translation':rotated?'rotation':'none',R2=(!frame.rx&&!frame.ry)?[R[0],R[1],R[3],R[4]]:null;return{kind,flat:[...T],R,R2,Rx:v(R[0]*x.x+R[1]*x.y+R[2]*x.z,R[3]*x.x+R[4]*x.y+R[5]*x.z,R[6]*x.x+R[7]*x.y+R[8]*x.z),d,X};}
  function boundsOverlap(a,b,tol=0){return !(a.max.x<=b.min.x+tol||b.max.x<=a.min.x+tol||a.max.y<=b.min.y+tol||b.max.y<=a.min.y+tol||a.max.z<=b.min.z+tol||b.max.z<=a.min.z+tol);}
  function pairwiseClashes(parts,tol=0){const out=[];for(let i=0;i<parts.length;i++)for(let j=i+1;j<parts.length;j++){const A=parts[i],B=parts[j],ba=bounds(A.tris),bb=bounds(B.tris);if(boundsOverlap(ba,bb,tol))out.push({a:A.name,b:B.name,boxA:ba,boxB:bb});}return out;}
  function triBounds(t){const xs=[t.a.x,t.b.x,t.c.x],ys=[t.a.y,t.b.y,t.c.y],zs=[t.a.z,t.b.z,t.c.z];return{min:v(Math.min(...xs),Math.min(...ys),Math.min(...zs)),max:v(Math.max(...xs),Math.max(...ys),Math.max(...zs))};}
  function mergeBox(a,b){return{min:v(Math.min(a.min.x,b.min.x),Math.min(a.min.y,b.min.y),Math.min(a.min.z,b.min.z)),max:v(Math.max(a.max.x,b.max.x),Math.max(a.max.y,b.max.y),Math.max(a.max.z,b.max.z))};}
  function makeBVH(tris,items=null,leaf=16){
    const arr=items||tris.map((t,i)=>({i,t,b:triBounds(t),c:v((t.a.x+t.b.x+t.c.x)/3,(t.a.y+t.b.y+t.c.y)/3,(t.a.z+t.b.z+t.c.z)/3)}));
    if(!arr.length)return null;let box=arr[0].b;for(let k=1;k<arr.length;k++)box=mergeBox(box,arr[k].b);
    if(arr.length<=leaf)return{box,items:arr};
    const sx=box.max.x-box.min.x,sy=box.max.y-box.min.y,sz=box.max.z-box.min.z,axis=sx>=sy&&sx>=sz?'x':sy>=sz?'y':'z';
    arr.sort((a,b)=>a.c[axis]-b.c[axis]);const mid=Math.floor(arr.length/2);
    return{box,left:makeBVH(tris,arr.slice(0,mid),leaf),right:makeBVH(tris,arr.slice(mid),leaf)};
  }
  function proj3(t,axis){const p=[dot(t.a,axis),dot(t.b,axis),dot(t.c,axis)];return[Math.min(...p),Math.max(...p)];}
  function sepIntervals(a,b,eps=1e-8){return a[1]<b[0]-eps||b[1]<a[0]-eps;}
  function dominantDrop(n){const ax=Math.abs(n.x),ay=Math.abs(n.y),az=Math.abs(n.z);return ax>=ay&&ax>=az?'x':ay>=az?'y':'z';}
  function to2(p,drop){return drop==='x'?[p.y,p.z]:drop==='y'?[p.x,p.z]:[p.x,p.y];}
  function tri2Overlap(A,B,eps=1e-8){
    const axes=[];for(const T of[A,B])for(let i=0;i<3;i++){const p=T[i],q=T[(i+1)%3],dx=q[0]-p[0],dy=q[1]-p[1],l=Math.hypot(dx,dy);if(l>eps)axes.push([-dy/l,dx/l]);}
    for(const a of axes){const pa=A.map(p=>p[0]*a[0]+p[1]*a[1]),pb=B.map(p=>p[0]*a[0]+p[1]*a[1]);if(Math.max(...pa)<Math.min(...pb)-eps||Math.max(...pb)<Math.min(...pa)-eps)return false;}return true;
  }
  function trianglesIntersect(t1,t2,eps=1e-8){
    if(!boundsOverlap(triBounds(t1),triBounds(t2),-eps))return false;
    const e1=[sub(t1.b,t1.a),sub(t1.c,t1.b),sub(t1.a,t1.c)],e2=[sub(t2.b,t2.a),sub(t2.c,t2.b),sub(t2.a,t2.c)],n1=cross(e1[0],sub(t1.c,t1.a)),n2=cross(e2[0],sub(t2.c,t2.a));
    if(len(n1)<eps||len(n2)<eps)return false;
    const nn1=norm(n1),nn2=norm(n2),parallel=len(cross(nn1,nn2))<1e-7,planeGap=Math.abs(dot(sub(t2.a,t1.a),nn1));
    if(parallel&&planeGap<1e-7){const d=dominantDrop(nn1);return tri2Overlap([to2(t1.a,d),to2(t1.b,d),to2(t1.c,d)],[to2(t2.a,d),to2(t2.b,d),to2(t2.c,d)],eps);}
    const axes=[n1,n2];for(const a of e1)for(const b of e2){const x=cross(a,b);if(len(x)>eps)axes.push(x);}
    for(const axis of axes)if(sepIntervals(proj3(t1,axis),proj3(t2,axis),eps))return false;
    return true;
  }
  function bvhIntersections(a,b,limit=64,out=[]){
    if(!a||!b||out.length>=limit||!boundsOverlap(a.box,b.box,0))return out;
    if(a.items&&b.items){for(const x of a.items)for(const y of b.items){if(out.length>=limit)return out;if(boundsOverlap(x.b,y.b,0)&&trianglesIntersect(x.t,y.t))out.push([x.i,y.i]);}return out;}
    if(a.items){bvhIntersections(a,b.left,limit,out);bvhIntersections(a,b.right,limit,out);return out;}
    if(b.items){bvhIntersections(a.left,b,limit,out);bvhIntersections(a.right,b,limit,out);return out;}
    bvhIntersections(a.left,b.left,limit,out);bvhIntersections(a.left,b.right,limit,out);bvhIntersections(a.right,b.left,limit,out);bvhIntersections(a.right,b.right,limit,out);return out;
  }
  function pointSegDist2(p,a,b){const ab=sub(b,a),d=dot(ab,ab);if(d<EPS)return dot(sub(p,a),sub(p,a));const q=Math.max(0,Math.min(1,dot(sub(p,a),ab)/d)),c=v(a.x+ab.x*q,a.y+ab.y*q,a.z+ab.z*q),r=sub(p,c);return dot(r,r);}
  function segSegDist2(p1,q1,p2,q2){
    const d1=sub(q1,p1),d2=sub(q2,p2),r=sub(p1,p2),a=dot(d1,d1),E=dot(d2,d2),f=dot(d2,r);let s,t;
    if(a<=EPS&&E<=EPS)return dot(r,r);
    if(a<=EPS){s=0;t=Math.max(0,Math.min(1,f/E));}
    else{const c=dot(d1,r);if(E<=EPS){t=0;s=Math.max(0,Math.min(1,-c/a));}else{const b=dot(d1,d2),den=a*E-b*b;s=den?Math.max(0,Math.min(1,(b*f-c*E)/den)):0;t=(b*s+f)/E;if(t<0){t=0;s=Math.max(0,Math.min(1,-c/a));}else if(t>1){t=1;s=Math.max(0,Math.min(1,(b-c)/a));}}}
    const c1=v(p1.x+d1.x*s,p1.y+d1.y*s,p1.z+d1.z*s),c2=v(p2.x+d2.x*t,p2.y+d2.y*t,p2.z+d2.z*t),rr=sub(c1,c2);return dot(rr,rr);
  }
  function pointTriDist2(p,t){
    const ab=sub(t.b,t.a),ac=sub(t.c,t.a),ap=sub(p,t.a),d1=dot(ab,ap),d2=dot(ac,ap);if(d1<=0&&d2<=0)return dot(ap,ap);
    const bp=sub(p,t.b),d3=dot(ab,bp),d4=dot(ac,bp);if(d3>=0&&d4<=d3)return dot(bp,bp);
    const vc=d1*d4-d3*d2;if(vc<=0&&d1>=0&&d3<=0){const q=d1/(d1-d3),c=v(t.a.x+ab.x*q,t.a.y+ab.y*q,t.a.z+ab.z*q),r=sub(p,c);return dot(r,r);}
    const cp=sub(p,t.c),d5=dot(ab,cp),d6=dot(ac,cp);if(d6>=0&&d5<=d6)return dot(cp,cp);
    const vb=d5*d2-d1*d6;if(vb<=0&&d2>=0&&d6<=0){const q=d2/(d2-d6),c=v(t.a.x+ac.x*q,t.a.y+ac.y*q,t.a.z+ac.z*q),r=sub(p,c);return dot(r,r);}
    const va=d3*d6-d5*d4;if(va<=0&&(d4-d3)>=0&&(d5-d6)>=0){const bc=sub(t.c,t.b),q=(d4-d3)/((d4-d3)+(d5-d6)),c=v(t.b.x+bc.x*q,t.b.y+bc.y*q,t.b.z+bc.z*q),r=sub(p,c);return dot(r,r);}
    const n=norm(cross(ab,ac)),dist=dot(ap,n);return dist*dist;
  }
  function triangleDistance(t1,t2){if(trianglesIntersect(t1,t2))return 0;let m=Infinity;for(const p of[t1.a,t1.b,t1.c])m=Math.min(m,pointTriDist2(p,t2));for(const p of[t2.a,t2.b,t2.c])m=Math.min(m,pointTriDist2(p,t1));const e1=[[t1.a,t1.b],[t1.b,t1.c],[t1.c,t1.a]],e2=[[t2.a,t2.b],[t2.b,t2.c],[t2.c,t2.a]];for(const a of e1)for(const b of e2)m=Math.min(m,segSegDist2(a[0],a[1],b[0],b[1]));return Math.sqrt(m);}
  function boxDistance(a,b){const dx=Math.max(0,a.min.x-b.max.x,b.min.x-a.max.x),dy=Math.max(0,a.min.y-b.max.y,b.min.y-a.max.y),dz=Math.max(0,a.min.z-b.max.z,b.min.z-a.max.z);return Math.hypot(dx,dy,dz);}
  function bvhMinDistance(a,b,best=Infinity){
    if(!a||!b||boxDistance(a.box,b.box)>=best)return best;
    if(a.items&&b.items){for(const x of a.items)for(const y of b.items){if(boxDistance(x.b,y.b)>=best)continue;best=Math.min(best,triangleDistance(x.t,y.t));if(best<=EPS)return 0;}return best;}
    const pairs=[];if(a.items){pairs.push([a,b.left],[a,b.right]);}else if(b.items){pairs.push([a.left,b],[a.right,b]);}else{pairs.push([a.left,b.left],[a.left,b.right],[a.right,b.left],[a.right,b.right]);}
    pairs.sort((u,w)=>boxDistance(u[0].box,u[1].box)-boxDistance(w[0].box,w[1].box));for(const pair of pairs)best=bvhMinDistance(pair[0],pair[1],best);return best;
  }
  function pairwiseClearances(parts,threshold=0.4){
    const out=[],prepared=parts.map(p=>({...p,box:bounds(p.tris),bvh:makeBVH(p.tris)}));
    for(let i=0;i<prepared.length;i++)for(let j=i+1;j<prepared.length;j++){const A=prepared[i],B=prepared[j],lower=boxDistance(A.box,B.box);if(lower>threshold)continue;const d=bvhMinDistance(A.bvh,B.bvh,Infinity);if(d<=threshold+1e-9)out.push({a:A.name,b:B.name,distance:d,threshold});}
    return out.sort((x,y)=>x.distance-y.distance);
  }
  function rayTri(p,dir,t,eps=1e-9){
    const e1=sub(t.b,t.a),e2=sub(t.c,t.a),h=cross(dir,e2),a=dot(e1,h);if(Math.abs(a)<eps)return null;const inv=1/a,s=sub(p,t.a),u=inv*dot(s,h);if(u<-eps||u>1+eps)return null;const q=cross(s,e1),vv=inv*dot(dir,q);if(vv<-eps||u+vv>1+eps)return null;const d=inv*dot(e2,q);return d>eps?d:null;
  }
  function pointInMesh(point,tris){
    const dir=norm(v(1,0.371390676,0.529));const hits=[];for(const t of tris){const d=rayTri(point,dir,t);if(d!==null)hits.push(d);}hits.sort((a,b)=>a-b);let unique=0,last=-Infinity;for(const d of hits){if(Math.abs(d-last)>1e-6){unique++;last=d;}}return unique%2===1;
  }
  function pairwiseGeometryClashes(parts,{limitPerPair=64}={}){
    const out=[],prepared=parts.map(p=>({...p,box:bounds(p.tris),bvh:makeBVH(p.tris)}));
    for(let i=0;i<prepared.length;i++)for(let j=i+1;j<prepared.length;j++){const A=prepared[i],B=prepared[j];if(!boundsOverlap(A.box,B.box,0))continue;const hits=bvhIntersections(A.bvh,B.bvh,limitPerPair,[]);let containment=null;
      if(!hits.length&&A.tris.length&&B.tris.length){if(pointInMesh(A.tris[0].a,B.tris))containment='A-in-B';else if(pointInMesh(B.tris[0].a,A.tris))containment='B-in-A';}
      if(hits.length||containment)out.push({a:A.name,b:B.name,trianglePairs:hits,intersectionCount:hits.length,containment});
    }return out;
  }
  function toBinarySTL(tris,name='UNG-CAD'){const buf=new ArrayBuffer(84+50*tris.length),dv=new DataView(buf),u8=new Uint8Array(buf),enc=new TextEncoder().encode(name.slice(0,80));u8.set(enc.slice(0,80));dv.setUint32(80,tris.length,true);let off=84;for(const t of tris){const n=triangleNormal(t);for(const q of[n.x,n.y,n.z]){dv.setFloat32(off,q,true);off+=4;}for(const p of[t.a,t.b,t.c])for(const q of[p.x,p.y,p.z]){dv.setFloat32(off,q,true);off+=4;}dv.setUint16(off,0,true);off+=2;}return buf;}
  function mat4TransformPoint(m,p){const q=[0,0,0,0],vv=[p[0],p[1],p[2],1];for(let i=0;i<4;i++)for(let j=0;j<4;j++)q[i]+=m[i][j]*vv[j];const w=q[3]||1;return[q[0]/w,q[1]/w,q[2]/w];}
  function composeMat4(a,b){return a.map((r,i)=>r.map((_,j)=>a[i].reduce((sum,__,k)=>sum+a[i][k]*b[k][j],0)));}
  function cadFrameProduct(position,transform,sourceFrame="part",destinationFrame="assembly"){return{position:mat4TransformPoint(transform,position),source_frame:sourceFrame,destination_frame:destinationFrame,provenance:"DERIVED"};}
  return{trianglesFromPolygons,measure,bounds,volume,surfaceArea,printEstimate,identity,multiply,rotationX,rotationY,rotationZ,scaling,mirror,translation,determinant3,transformPoint,applyMatrix,placeOnBed,triangleNormal,findOverhangs,rotationBetween,fitsBed,autoOrient,frameMatrix,invertRigid,toParent,fromParent,worldMatrix,explainTransform,boundsOverlap,pairwiseClashes,trianglesIntersect,makeBVH,bvhIntersections,pointInMesh,pairwiseGeometryClashes,triangleDistance,boxDistance,bvhMinDistance,pairwiseClearances,toBinarySTL,mat4TransformPoint,composeMat4,cadFrameProduct};
});