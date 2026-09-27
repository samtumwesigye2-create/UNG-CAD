/* UNG shared advanced mathematics core
   Vector/matrix geometry, differential fields, section-plane math,
   diffusion/advection helpers, Euler-Lagrange numerical primitives,
   and lightweight KNN/Random-Forest-style inference utilities.
*/
(function(g){
 const V={
  add:(a,b)=>a.map((x,i)=>x+b[i]), sub:(a,b)=>a.map((x,i)=>x-b[i]),
  scale:(a,s)=>a.map(x=>x*s), dot:(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0),
  norm:a=>Math.hypot(...a), unit:a=>{const n=Math.hypot(...a)||1;return a.map(x=>x/n)},
  cross:(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],
  project:(a,b)=>{const d=V.dot(b,b)||1;return V.scale(b,V.dot(a,b)/d)}
 };
 const M={
  mulVec:(A,x)=>A.map(r=>V.dot(r,x)),
  transpose:A=>A[0].map((_,j)=>A.map(r=>r[j]))
 };
 function grad(f,p,h=1e-4){return p.map((_,i)=>{let a=[...p],b=[...p];a[i]+=h;b[i]-=h;return(f(a)-f(b))/(2*h)})}
 function divergence(F,p,h=1e-4){let s=0;for(let i=0;i<p.length;i++){let a=[...p],b=[...p];a[i]+=h;b[i]-=h;s+=(F(a)[i]-F(b)[i])/(2*h)}return s}
 function curl(F,p,h=1e-4){if(p.length!==3)throw Error('curl requires 3D');const d=(comp,axis)=>{let a=[...p],b=[...p];a[axis]+=h;b[axis]-=h;return(F(a)[comp]-F(b)[comp])/(2*h)};return[d(2,1)-d(1,2),d(0,2)-d(2,0),d(1,0)-d(0,1)]}
 function laplacian(f,p,h=1e-3){const c=f(p);return p.reduce((s,_,i)=>{let a=[...p],b=[...p];a[i]+=h;b[i]-=h;return s+(f(a)-2*c+f(b))/(h*h)},0)}
 function planeSignedDistance(p,origin,normal){return V.dot(V.sub(p,origin),V.unit(normal))}
 function segmentPlane(a,b,origin,normal){const da=planeSignedDistance(a,origin,normal),db=planeSignedDistance(b,origin,normal);if(da*db>0||Math.abs(da-db)<1e-12)return null;const t=da/(da-db);return V.add(a,V.scale(V.sub(b,a),t))}
 function diffusionStep(grid,w,h,alpha,dt,dx=1){const out=grid.slice(),k=alpha*dt/(dx*dx);for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){const i=y*w+x;out[i]=grid[i]+k*(grid[i-1]+grid[i+1]+grid[i-w]+grid[i+w]-4*grid[i])}return out}
 function advectionDiffusionStep(grid,w,h,vx,vy,D,dt,dx=1){let d=diffusionStep(grid,w,h,D,dt,dx);const o=d.slice();for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){const i=y*w+x, gx=(grid[i+1]-grid[i-1])/(2*dx),gy=(grid[i+w]-grid[i-w])/(2*dx);o[i]=d[i]-dt*(vx*gx+vy*gy)}return o}
 function eulerLagrange({dLdq,dLdqdot,q,qdot,dt=1e-3}){const n=q.length,a=[];for(let i=0;i<n;i++){const qp=[...q],qm=[...q];qp[i]+=qdot[i]*dt;qm[i]-=qdot[i]*dt;const ddt=(dLdqdot(qp,qdot)[i]-dLdqdot(qm,qdot)[i])/(2*dt);a.push(ddt-dLdq(q,qdot)[i])}return a}
 function knn(train,labels,x,k=3){return train.map((p,i)=>({i,d:V.norm(V.sub(p,x))})).sort((a,b)=>a.d-b.d).slice(0,k).reduce((m,o)=>(m[labels[o.i]]=(m[labels[o.i]]||0)+1,m),{})}
 function forestVote(predictions){const m={};predictions.forEach(v=>m[v]=(m[v]||0)+1);return Object.entries(m).sort((a,b)=>b[1]-a[1])[0]?.[0]}
 g.UNGMathCore={V,M,grad,divergence,curl,laplacian,planeSignedDistance,segmentPlane,diffusionStep,advectionDiffusionStep,eulerLagrange,knn,forestVote};
})(globalThis);
