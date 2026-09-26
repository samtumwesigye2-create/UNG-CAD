/* UNG-CAD lightweight symbolic math helpers */
(function(g){
 const E={
  c:v=>({op:"const",v:+v}), x:n=>({op:"var",n}), add:(a,b)=>({op:"add",a,b}), mul:(a,b)=>({op:"mul",a,b}), pow:(a,b)=>({op:"pow",a,b})
 };
 function evalExpr(e,env={}){if(e.op==="const")return e.v;if(e.op==="var")return +env[e.n];if(e.op==="add")return evalExpr(e.a,env)+evalExpr(e.b,env);if(e.op==="mul")return evalExpr(e.a,env)*evalExpr(e.b,env);if(e.op==="pow")return Math.pow(evalExpr(e.a,env),evalExpr(e.b,env));throw Error("Unknown expression");}
 function diff(e,x){if(e.op==="const")return E.c(0);if(e.op==="var")return E.c(e.n===x?1:0);if(e.op==="add")return E.add(diff(e.a,x),diff(e.b,x));if(e.op==="mul")return E.add(E.mul(diff(e.a,x),e.b),E.mul(e.a,diff(e.b,x)));if(e.op==="pow"&&e.b.op==="const")return E.mul(E.mul(E.c(e.b.v),E.pow(e.a,E.c(e.b.v-1))),diff(e.a,x));throw Error("Derivative form not supported");}
 function integrateNumeric(fn,a,b,n=2048){if(n%2)n++;let h=(b-a)/n,sum=fn(a)+fn(b);for(let i=1;i<n;i++)sum+=(i%2?4:2)*fn(a+i*h);return sum*h/3;}
 function substitutePower(k){return {x:"u^"+k,dx:k+"*u^"+(k-1)+" du",power:k};}
 
// Trigonometric identity/rewrite registry for CAD constraints, kinematics and analytic geometry.
 const trigIdentities=Object.freeze({
  pythagorean:"sin(x)^2 + cos(x)^2 = 1",
  cosPowerReduction:"cos(x)^2 = (1 + cos(2x))/2",
  sinPowerReduction:"sin(x)^2 = (1 - cos(2x))/2",
  cosDoubleAngle:"cos(2x) = cos(x)^2 - sin(x)^2",
  sinDoubleAngle:"sin(2x) = 2 sin(x) cos(x)"
 });
 function trigRewrite(expr,target="simplify"){
  let s=String(expr).replace(/\\s+/g,"").replace(/²/g,"^2");
  const rules=[
   [/sin\\(([^()]+)\\)\\^2\\+cos\\(\\1\\)\\^2/g,"1"],
   [/cos\\(([^()]+)\\)\\^2\\+sin\\(\\1\\)\\^2/g,"1"]
  ];
  if(target==="power-reduction"){
   rules.push([/cos\\(([^()]+)\\)\\^2/g,"(1+cos(2*$1))/2"]);
   rules.push([/sin\\(([^()]+)\\)\\^2/g,"(1-cos(2*$1))/2"]);
  }
  if(target==="double-angle"){
   rules.push([/2\\*?sin\\(([^()]+)\\)\\*?cos\\(\\1\\)/g,"sin(2*$1)"]);
  }
  let prev; do{prev=s;for(const [r,v] of rules)s=s.replace(r,v)}while(s!==prev);
  return s;
 }
 function verifyTrigIdentity(name,x){
  const s=Math.sin(x),c=Math.cos(x),c2=Math.cos(2*x),s2=Math.sin(2*x);
  const checks={
   pythagorean:[s*s+c*c,1],
   cosPowerReduction:[c*c,(1+c2)/2],
   sinPowerReduction:[s*s,(1-c2)/2],
   cosDoubleAngle:[c2,c*c-s*s],
   sinDoubleAngle:[s2,2*s*c]
  },p=checks[name]; if(!p)throw Error("Unknown trig identity");
  return {name,lhs:p[0],rhs:p[1],error:Math.abs(p[0]-p[1]),valid:Math.abs(p[0]-p[1])<1e-12};
 }
 
 // Extended trigonometry library: exact values and transformation identities.
 const exactTrig=Object.freeze({
  "sin(0)":0,"cos(0)":1,"sin(pi/6)":0.5,"cos(pi/6)":"sqrt(3)/2",
  "sin(pi/4)":"sqrt(2)/2","cos(pi/4)":"sqrt(2)/2",
  "sin(pi/3)":"sqrt(3)/2","cos(pi/3)":0.5,"sin(pi/2)":1,"cos(pi/2)":0
 });
 const trigFormulas=Object.freeze({
  sinSum:"sin(a+b)=sin(a)cos(b)+cos(a)sin(b)",
  sinDifference:"sin(a-b)=sin(a)cos(b)-cos(a)sin(b)",
  cosSum:"cos(a+b)=cos(a)cos(b)-sin(a)sin(b)",
  cosDifference:"cos(a-b)=cos(a)cos(b)+sin(a)sin(b)",
  sinHalfAngle:"sin(x/2)^2=(1-cos(x))/2",
  cosHalfAngle:"cos(x/2)^2=(1+cos(x))/2",
  productSinCos:"sin(a)cos(b)=(sin(a+b)+sin(a-b))/2",
  productCosCos:"cos(a)cos(b)=(cos(a+b)+cos(a-b))/2",
  productSinSin:"sin(a)sin(b)=(cos(a-b)-cos(a+b))/2",
  sumSin:"sin(a)+sin(b)=2sin((a+b)/2)cos((a-b)/2)",
  sumCos:"cos(a)+cos(b)=2cos((a+b)/2)cos((a-b)/2)"
 });
 function exactTrigValue(expr){const k=String(expr).replace(/\\s+/g,"").toLowerCase();return Object.prototype.hasOwnProperty.call(exactTrig,k)?exactTrig[k]:null}
 function inverseTrigSimplify(fn,value){
  const v=Number(value),eps=1e-12;
  if(fn==="asin"){if(Math.abs(v)<eps)return 0;if(Math.abs(v-.5)<eps)return "pi/6";if(Math.abs(v-1)<eps)return "pi/2";}
  if(fn==="acos"){if(Math.abs(v-1)<eps)return 0;if(Math.abs(v-.5)<eps)return "pi/3";if(Math.abs(v)<eps)return "pi/2";}
  if(fn==="atan"){if(Math.abs(v)<eps)return 0;if(Math.abs(v-1)<eps)return "pi/4";}
  return null;
 }
 
// CAD-oriented trig solver: angle normalization, periodic equivalence, and triangle solving.
 function normalizeAngle(rad){const tau=2*Math.PI;let r=Number(rad)%tau;if(r<0)r+=tau;return r}
 function periodicEquivalent(a,b,tol=1e-10){const d=normalizeAngle(a)-normalizeAngle(b);return Math.abs(d)<tol||Math.abs(Math.abs(d)-2*Math.PI)<tol}
 function degToRad(d){return Number(d)*Math.PI/180}
 function radToDeg(r){return Number(r)*180/Math.PI}
 function solveRightTriangle({opposite,adjacent,hypotenuse,angleRad}={}){
  let o=Number(opposite),a=Number(adjacent),h=Number(hypotenuse),t=Number(angleRad);
  const ok=n=>Number.isFinite(n)&&n>=0;
  if(ok(t)&&ok(h)){if(!ok(o))o=h*Math.sin(t);if(!ok(a))a=h*Math.cos(t)}
  if(ok(o)&&ok(a)){if(!ok(h))h=Math.hypot(o,a);if(!ok(t))t=Math.atan2(o,a)}
  if(ok(h)&&ok(o)&&!ok(a))a=Math.sqrt(Math.max(0,h*h-o*o));
  if(ok(h)&&ok(a)&&!ok(o))o=Math.sqrt(Math.max(0,h*h-a*a));
  if(!ok(t)&&ok(o)&&ok(h)&&h>0)t=Math.asin(Math.min(1,o/h));
  if(!ok(t)&&ok(a)&&ok(h)&&h>0)t=Math.acos(Math.min(1,a/h));
  if(!(ok(o)&&ok(a)&&ok(h)&&ok(t)))throw Error("Insufficient triangle constraints");
  return {opposite:o,adjacent:a,hypotenuse:h,angleRad:t,angleDeg:radToDeg(t)};
 }
 function rotate2D(x,y,angleRad){const c=Math.cos(angleRad),s=Math.sin(angleRad);return{x:x*c-y*s,y:x*s+y*c}}
 function polarToCartesian(radius,angleRad){return{x:radius*Math.cos(angleRad),y:radius*Math.sin(angleRad)}}
 function cartesianToPolar(x,y){return{radius:Math.hypot(x,y),angleRad:Math.atan2(y,x),angleDeg:radToDeg(Math.atan2(y,x))}}
 
 // Vector/rotation helpers for 3D CAD constraints and kinematics.
 function rotate3D(p,axis,angleRad){
  const x=Number(p.x),y=Number(p.y),z=Number(p.z),ax=Number(axis.x),ay=Number(axis.y),az=Number(axis.z);
  const m=Math.hypot(ax,ay,az);if(!m)throw Error("Rotation axis cannot be zero");
  const u={x:ax/m,y:ay/m,z:az/m},c=Math.cos(angleRad),s=Math.sin(angleRad),d=u.x*x+u.y*y+u.z*z;
  return {x:x*c+(u.y*z-u.z*y)*s+u.x*d*(1-c),y:y*c+(u.z*x-u.x*z)*s+u.y*d*(1-c),z:z*c+(u.x*y-u.y*x)*s+u.z*d*(1-c)};
 }
 function angleBetweenVectors(a,b){
  const da=Math.hypot(a.x,a.y,a.z),db=Math.hypot(b.x,b.y,b.z);if(!da||!db)throw Error("Zero-length vector");
  const q=(a.x*b.x+a.y*b.y+a.z*b.z)/(da*db);return Math.acos(Math.max(-1,Math.min(1,q)));
 }
 function vectorFromYawPitch(yaw,pitch,length=1){
  const cp=Math.cos(pitch);return{x:length*cp*Math.cos(yaw),y:length*Math.sin(pitch),z:length*cp*Math.sin(yaw)};
 }
 function yawPitchFromVector(v){
  const r=Math.hypot(v.x,v.y,v.z);if(!r)throw Error("Zero-length vector");
  return{yaw:Math.atan2(v.z,v.x),pitch:Math.asin(v.y/r),length:r};
 }
 function arcLength(radius,angleRad){return Math.abs(Number(radius)*Number(angleRad))}
 function chordLength(radius,angleRad){return 2*Math.abs(Number(radius))*Math.sin(Math.abs(Number(angleRad))/2)}
 function radiusFromChord(chord,angleRad){const s=2*Math.sin(Math.abs(Number(angleRad))/2);if(Math.abs(s)<1e-15)throw Error("Angle produces undefined radius");return Math.abs(Number(chord)/s)}
 
 // Curve differential geometry for CAD paths, sweeps, CAM and trajectory analysis.
 function derivative3(fn,t,h=1e-5){const a=fn(t-h),b=fn(t+h);return{x:(b.x-a.x)/(2*h),y:(b.y-a.y)/(2*h),z:(b.z-a.z)/(2*h)}}
 function secondDerivative3(fn,t,h=1e-4){const a=fn(t-h),b=fn(t),d=fn(t+h),q=h*h;return{x:(d.x-2*b.x+a.x)/q,y:(d.y-2*b.y+a.y)/q,z:(d.z-2*b.z+a.z)/q}}
 function curveKinematics(fn,t,h=1e-5){
  const v=derivative3(fn,t,h),a=secondDerivative3(fn,t,Math.sqrt(h));
  const speed=Math.hypot(v.x,v.y,v.z),cx=v.y*a.z-v.z*a.y,cy=v.z*a.x-v.x*a.z,cz=v.x*a.y-v.y*a.x;
  const curvature=speed?Math.hypot(cx,cy,cz)/Math.pow(speed,3):0;
  return{position:fn(t),velocity:v,acceleration:a,speed,curvature,radiusOfCurvature:curvature?1/curvature:Infinity};
 }
 function sampleParametricCurve(fn,t0,t1,segments=64){const out=[];for(let i=0;i<=segments;i++){const t=t0+(t1-t0)*i/segments;out.push({t,...fn(t)})}return out}
 function polylineLength(points){let s=0;for(let i=1;i<points.length;i++)s+=Math.hypot(points[i].x-points[i-1].x,points[i].y-points[i-1].y,points[i].z-points[i-1].z);return s}
 function adaptiveCurveLength(fn,t0,t1,tol=1e-5,maxDepth=16){
  function rec(a,b,pa,pb,d){const m=(a+b)/2,pm=fn(m),ch=Math.hypot(pb.x-pa.x,pb.y-pa.y,pb.z-pa.z),sp=Math.hypot(pm.x-pa.x,pm.y-pa.y,pm.z-pa.z)+Math.hypot(pb.x-pm.x,pb.y-pm.y,pb.z-pm.z);return d>=maxDepth||Math.abs(sp-ch)<=tol?sp:rec(a,m,pa,pm,d+1)+rec(m,b,pm,pb,d+1)}
  return rec(t0,t1,fn(t0),fn(t1),0);
 }
 
 // Surface differential geometry for parametric CAD faces and manufacturing analysis.
 function partial3(fn,u,v,axis,h=1e-5){const a=axis==="u"?fn(u-h,v):fn(u,v-h),b=axis==="u"?fn(u+h,v):fn(u,v+h);return{x:(b.x-a.x)/(2*h),y:(b.y-a.y)/(2*h),z:(b.z-a.z)/(2*h)}}
 function surfaceNormal(fn,u,v,h=1e-5){const a=partial3(fn,u,v,"u",h),b=partial3(fn,u,v,"v",h),x=a.y*b.z-a.z*b.y,y=a.z*b.x-a.x*b.z,z=a.x*b.y-a.y*b.x,m=Math.hypot(x,y,z);if(!m)throw Error("Degenerate surface normal");return{x:x/m,y:y/m,z:z/m}}
 function sampleParametricSurface(fn,u0,u1,v0,v1,uSegments=24,vSegments=24){const points=[];for(let j=0;j<=vSegments;j++){const v=v0+(v1-v0)*j/vSegments;for(let i=0;i<=uSegments;i++){const u=u0+(u1-u0)*i/uSegments;points.push({u,v,...fn(u,v)})}}return{points,uSegments,vSegments}}
 function surfaceAreaApprox(fn,u0,u1,v0,v1,uSegments=40,vSegments=40){let area=0;const du=(u1-u0)/uSegments,dv=(v1-v0)/vSegments;for(let j=0;j<vSegments;j++)for(let i=0;i<uSegments;i++){const u=u0+(i+.5)*du,v=v0+(j+.5)*dv,a=partial3(fn,u,v,"u"),b=partial3(fn,u,v,"v"),cx=a.y*b.z-a.z*b.y,cy=a.z*b.x-a.x*b.z,cz=a.x*b.y-a.y*b.x;area+=Math.hypot(cx,cy,cz)*Math.abs(du*dv)}return area}
 function tangentPlane(fn,u,v){const p=fn(u,v),n=surfaceNormal(fn,u,v);return{point:p,normal:n,d:-(n.x*p.x+n.y*p.y+n.z*p.z)}}
 g.UNGSymbolic={E,evalExpr,diff,integrateNumeric,substitutePower,trigIdentities,trigRewrite,verifyTrigIdentity,trigFormulas,exactTrig,exactTrigValue,inverseTrigSimplify,normalizeAngle,periodicEquivalent,degToRad,radToDeg,solveRightTriangle,rotate2D,polarToCartesian,cartesianToPolar,rotate3D,angleBetweenVectors,vectorFromYawPitch,yawPitchFromVector,arcLength,chordLength,radiusFromChord,derivative3,secondDerivative3,curveKinematics,sampleParametricCurve,polylineLength,adaptiveCurveLength,partial3,surfaceNormal,sampleParametricSurface,surfaceAreaApprox,tangentPlane};
})(window);
