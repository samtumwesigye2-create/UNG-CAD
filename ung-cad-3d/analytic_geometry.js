/* UNG-CAD analytic solid geometry core */
(function(g){
 const V=(x=0,y=0,z=0)=>({x:+x,y:+y,z:+z});
 const primitives={
  sphere:(r=1,c=V())=>({kind:"sphere",r:+r,c}),
  cylinder:(r=1,h=1,axis:"z",c=V())=>({kind:"cylinder",r:+r,h:+h,axis,c}),
  box:(x=1,y=1,z=1,c=V())=>({kind:"box",size:V(x,y,z),c})
 };
 const csg=(op,a,b)=>({kind:"csg",op,a,b});
 function contains(s,p){
  if(s.kind==="sphere"){let x=p.x-s.c.x,y=p.y-s.c.y,z=p.z-s.c.z;return x*x+y*y+z*z<=s.r*s.r;}
  if(s.kind==="box"){return Math.abs(p.x-s.c.x)<=s.size.x/2&&Math.abs(p.y-s.c.y)<=s.size.y/2&&Math.abs(p.z-s.c.z)<=s.size.z/2;}
  if(s.kind==="cylinder"){let q={x:p.x-s.c.x,y:p.y-s.c.y,z:p.z-s.c.z},a=s.axis,u=a==="x"?q.y:q.x,v=a==="z"?q.y:q.z,w=a==="x"?q.x:a==="y"?q.y:q.z;return u*u+v*v<=s.r*s.r&&Math.abs(w)<=s.h/2;}
  if(s.kind==="csg"){let A=contains(s.a,p),B=contains(s.b,p);return s.op==="intersection"?A&&B:s.op==="union"?A||B:A&&!B;}
  return false;
 }
 g.UNGAnalytic={V,primitives,intersection:(a,b)=>csg("intersection",a,b),union:(a,b)=>csg("union",a,b),difference:(a,b)=>csg("difference",a,b),contains};
})(window);
