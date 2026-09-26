/* UNG-CAD parametric surface engine */
(function(g){
 function surface(fn,u=[0,1],v=[0,1],meta={}){return {kind:"parametric-surface",fn,u,v,meta};}
 function tessellate(s,nu=48,nv=48){const vertices=[],triangles=[];for(let j=0;j<=nv;j++)for(let i=0;i<=nu;i++){let u=s.u[0]+(s.u[1]-s.u[0])*i/nu,v=s.v[0]+(s.v[1]-s.v[0])*j/nv;vertices.push(s.fn(u,v));}for(let j=0;j<nv;j++)for(let i=0;i<nu;i++){let a=j*(nu+1)+i,b=a+1,c=a+nu+1,d=c+1;triangles.push([a,b,d],[a,d,c]);}return {vertices,triangles};}
 const cylinder=(r=1,h=1)=>surface((u,v)=>({x:r*Math.cos(u),y:r*Math.sin(u),z:v}),[0,2*Math.PI],[-h/2,h/2],{type:"cylinder",r,h});
 const sphere=(r=1)=>surface((u,v)=>({x:r*Math.cos(u)*Math.sin(v),y:r*Math.sin(u)*Math.sin(v),z:r*Math.cos(v)}),[0,2*Math.PI],[0,Math.PI],{type:"sphere",r});
 const revolution=(profile)=>surface((u,v)=>{let p=profile(v);return {x:p.r*Math.cos(u),y:p.r*Math.sin(u),z:p.z};},[0,2*Math.PI],[0,1],{type:"revolution"});
 g.UNGSurfaces={surface,tessellate,cylinder,sphere,revolution};
})(window);
