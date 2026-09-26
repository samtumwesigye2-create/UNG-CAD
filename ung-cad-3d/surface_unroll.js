/* UNG-CAD surface development / unroll */
(function(g){
 function develop(s,nu=48,nv=48){
  if(s.meta&&s.meta.type==="cylinder"){let r=s.meta.r,h=s.meta.h;return {kind:"developed-surface",source:s,outline:[[0,-h/2],[2*Math.PI*r,-h/2],[2*Math.PI*r,h/2],[0,h/2]],map:(u,v)=>[r*u,v]};}
  // Generic sampled UV development preserves source mapping for manufacturing/inspection.
  const pts=[];for(let j=0;j<=nv;j++)for(let i=0;i<=nu;i++){let u=s.u[0]+(s.u[1]-s.u[0])*i/nu,v=s.v[0]+(s.v[1]-s.v[0])*j/nv;pts.push({uv:[u,v],xyz:s.fn(u,v)});}
  return {kind:"uv-development",source:s,points:pts,warning:"Generic UV development is parametric; distortion must be checked before fabrication."};
 }
 function distortion(dev){if(dev.kind==="developed-surface")return {developable:true,maxEstimatedStrain:0};return {developable:false,requiresStrainAnalysis:true};}
 g.UNGUnroll={develop,distortion};
})(window);
