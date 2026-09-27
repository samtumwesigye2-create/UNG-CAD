/* UNG advanced geometry, linear algebra, dynamics and N-D projection core. */
(function(g){
 const eps=1e-10;
 const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);
 const norm=a=>Math.hypot(...a);
 const add=(a,b)=>a.map((x,i)=>x+b[i]);
 const sub=(a,b)=>a.map((x,i)=>x-b[i]);
 const scale=(a,s)=>a.map(x=>x*s);
 const transpose=A=>A[0].map((_,j)=>A.map(r=>r[j]));
 const matMul=(A,B)=>A.map(r=>transpose(B).map(c=>dot(r,c)));
 const matVec=(A,x)=>A.map(r=>dot(r,x));
 function rref(A){
   const M=A.map(r=>r.slice()); let row=0,pivots=[];
   for(let col=0;col<(M[0]?.length||0)&&row<M.length;col++){
     let p=row; for(let i=row+1;i<M.length;i++)if(Math.abs(M[i][col])>Math.abs(M[p][col]))p=i;
     if(Math.abs(M[p][col])<eps)continue;
     [M[row],M[p]]=[M[p],M[row]];
     const q=M[row][col]; M[row]=M[row].map(v=>v/q);
     for(let i=0;i<M.length;i++)if(i!==row){const f=M[i][col];M[i]=M[i].map((v,j)=>v-f*M[row][j]);}
     pivots.push(col); row++;
   } return {matrix:M,pivots};
 }
 function rank(A){return rref(A).pivots.length}
 function nullSpace(A){
   const {matrix:R,pivots}=rref(A),n=A[0]?.length||0,free=[...Array(n).keys()].filter(i=>!pivots.includes(i));
   return free.map(f=>{const x=Array(n).fill(0);x[f]=1;pivots.forEach((p,i)=>x[p]=-R[i][f]);return x});
 }
 function columnSpace(A){const piv=rref(A).pivots;return piv.map(j=>A.map(r=>r[j]))}
 function gramSchmidt(vs){
   const Q=[];for(const v0 of vs){let v=v0.slice();for(const q of Q)v=sub(v,scale(q,dot(v,q)));const n=norm(v);if(n>eps)Q.push(scale(v,1/n));}return Q;
 }
 function projectToBasis(v,basis){const Q=gramSchmidt(basis);return Q.reduce((p,q)=>add(p,scale(q,dot(v,q))),Array(v.length).fill(0))}
 function changeBasis(v,basis){const Q=gramSchmidt(basis);return Q.map(q=>dot(v,q))}
 function powerEigen(A,iters=80){
   let v=Array(A.length).fill(1/Math.sqrt(A.length));for(let k=0;k<iters;k++){let w=matVec(A,v),n=norm(w)||1;v=scale(w,1/n)}return {value:dot(v,matVec(A,v)),vector:v};
 }
 function svdApprox(A,k=Math.min(A.length,A[0]?.length||0)){
   const AT=transpose(A),B=matMul(AT,A).map(r=>r.slice()),S=[],V=[];
   for(let c=0;c<k;c++){const e=powerEigen(B);if(Math.abs(e.value)<eps)break;const s=Math.sqrt(Math.max(0,e.value));S.push(s);V.push(e.vector);for(let i=0;i<B.length;i++)for(let j=0;j<B.length;j++)B[i][j]-=e.value*e.vector[i]*e.vector[j];}
   const U=V.map((v,i)=>scale(matVec(A,v),1/(S[i]||1)));return {U:transpose(U),S,V:transpose(V)};
 }
 function rotate2D([x,y],theta){const c=Math.cos(theta),s=Math.sin(theta);return[c*x-s*y,s*x+c*y]}
 function polarToCartesian(r,theta){return[r*Math.cos(theta),r*Math.sin(theta)]}
 function cartesianToPolar(x,y){return{r:Math.hypot(x,y),theta:Math.atan2(y,x)}}
 function trigProjection(r,theta){return{x:r*Math.cos(theta),y:r*Math.sin(theta)}}
 function sweptAreaRate(r,thetaDot){return .5*r*r*thetaDot}
 function angularMomentum(m,r,thetaDot){return m*r*r*thetaDot}
 function polarAcceleration(r,rDot,rDDot,thetaDot,thetaDDot){return{radial:rDDot-r*thetaDot*thetaDot,tangential:r*thetaDDot+2*rDot*thetaDot}}
 function rk4(state,deriv,dt){const k1=deriv(state),k2=deriv(add(state,scale(k1,dt/2))),k3=deriv(add(state,scale(k2,dt/2))),k4=deriv(add(state,scale(k3,dt)));return state.map((x,i)=>x+dt*(k1[i]+2*k2[i]+2*k3[i]+k4[i])/6)}
 function perspectiveND(point,d=4){let p=point.slice();while(p.length>3){const w=p.pop(),f=d/(d-w);p=p.map(x=>x*f)}return p}
 function orthographicND(point,axes=[0,1,2]){return axes.map(i=>point[i]||0)}
 g.UNGAdvancedGeometry={dot,norm,add,sub,scale,transpose,matMul,matVec,rref,rank,nullSpace,columnSpace,gramSchmidt,projectToBasis,changeBasis,powerEigen,svdApprox,rotate2D,polarToCartesian,cartesianToPolar,trigProjection,sweptAreaRate,angularMomentum,polarAcceleration,rk4,perspectiveND,orthographicND};
})(globalThis);
