/* UNG field, transform, constraint, N-D and tensor integration core. */
(function(g){
 const V={
  add:(a,b)=>a.map((x,i)=>x+b[i]), sub:(a,b)=>a.map((x,i)=>x-b[i]),
  scale:(a,s)=>a.map(x=>x*s), dot:(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0),
  norm:a=>Math.hypot(...a), unit:a=>{const n=Math.hypot(...a)||1;return a.map(x=>x/n)}
 };
 function surfaceNormals(vertices,faces){const out=vertices.map(()=>[0,0,0]);for(const f of faces){const a=vertices[f[0]],b=vertices[f[1]],c=vertices[f[2]],u=V.sub(b,a),v=V.sub(c,a),n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];for(const i of f)out[i]=V.add(out[i],n)}return out.map(V.unit)}
 function sampleVectorField(fn,bounds=[[-1,1],[-1,1],[-1,1]],steps=5){const o=[];for(let i=0;i<steps;i++)for(let j=0;j<steps;j++)for(let k=0;k<steps;k++){const p=[0,1,2].map((q)=>bounds[q][0]+(bounds[q][1]-bounds[q][0])*[i,j,k][q]/Math.max(1,steps-1));o.push({position:p,vector:fn(...p)})}return o}
 const I=n=>Array.from({length:n},(_,r)=>Array.from({length:n},(_,c)=>r===c?1:0));
 function matMul(A,B){return A.map(r=>B[0].map((_,j)=>r.reduce((s,x,k)=>s+x*B[k][j],0)))}
 function matVec(A,v){return A.map(r=>V.dot(r,v))}
 function rotationND(n,i,j,t){const M=I(n),c=Math.cos(t),s=Math.sin(t);M[i][i]=c;M[j][j]=c;M[i][j]=-s;M[j][i]=s;return M}
 function composeTransforms(...Ms){return Ms.reduce((a,b)=>matMul(a,b))}
 function hypercube(n=4,size=2){const count=1<<n,vertices=[];for(let m=0;m<count;m++)vertices.push(Array.from({length:n},(_,i)=>(m>>i&1?1:-1)*size/2));const edges=[];for(let m=0;m<count;m++)for(let i=0;i<n;i++){const q=m^(1<<i);if(m<q)edges.push([m,q])}return{vertices,edges}}
 function projectND(points,{distance=4,axes=[0,1,2]}={}){return points.map(p=>g.UNGAdvancedGeometry?.perspectiveND?g.UNGAdvancedGeometry.perspectiveND(p,distance):axes.map(i=>p[i]||0))}
 function sliceND(points,axis,value,tol=.05){return points.filter(p=>Math.abs((p[axis]||0)-value)<=tol)}
 function tensorShape(t){const s=[];let x=t;while(Array.isArray(x)){s.push(x.length);x=x[0]}return s}
 function tensorMap(t,fn,path=[]){return Array.isArray(t)?t.map((x,i)=>tensorMap(x,fn,path.concat(i))):fn(t,path)}
 function tensorZip(a,b,fn){return Array.isArray(a)?a.map((x,i)=>tensorZip(x,b[i],fn)):fn(a,b)}
 function tensorAdd(a,b){return tensorZip(a,b,(x,y)=>x+y)}
 function tensorScale(a,s){return tensorMap(a,x=>x*s)}
 function transformSensorPoint(point,T){const p=[...point,1],q=matVec(T,p);return q.slice(0,3).map(x=>x/(q[3]||1))}
 function constraintResidual(type,a,b,target=0){if(type==='distance')return V.norm(V.sub(a,b))-target;if(type==='coincident')return V.norm(V.sub(a,b));if(type==='parallel')return 1-Math.abs(V.dot(V.unit(a),V.unit(b)));if(type==='perpendicular')return V.dot(V.unit(a),V.unit(b));throw Error('Unknown constraint '+type)}
 function solveConstraints(state,constraints,{iterations=80,step=.15,tol=1e-6}={}){let x=state.slice();const loss=y=>constraints.reduce((s,c)=>{const r=c(y);return s+r*r},0);for(let it=0;it<iterations;it++){const base=loss(x);if(base<tol)return{state:x,loss:base,iterations:it};const h=1e-5,gx=x.map((_,i)=>{const y=x.slice();y[i]+=h;return(loss(y)-base)/h});x=x.map((v,i)=>v-step*gx[i])}return{state:x,loss:loss(x),iterations}}
 g.UNGGeometryIntegration={surfaceNormals,sampleVectorField,rotationND,composeTransforms,hypercube,projectND,sliceND,tensorShape,tensorMap,tensorAdd,tensorScale,transformSensorPoint,constraintResidual,solveConstraints};
})(globalThis);
