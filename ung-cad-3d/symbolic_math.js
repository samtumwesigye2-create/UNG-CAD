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
 g.UNGSymbolic={E,evalExpr,diff,integrateNumeric,substitutePower,trigIdentities,trigRewrite,verifyTrigIdentity};
})(window);
