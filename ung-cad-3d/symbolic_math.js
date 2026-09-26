/* UNG-CAD lightweight symbolic math helpers */
(function(g){
 const E={
  c:v=>({op:"const",v:+v}), x:n=>({op:"var",n}), add:(a,b)=>({op:"add",a,b}), mul:(a,b)=>({op:"mul",a,b}), pow:(a,b)=>({op:"pow",a,b})
 };
 function evalExpr(e,env={}){if(e.op==="const")return e.v;if(e.op==="var")return +env[e.n];if(e.op==="add")return evalExpr(e.a,env)+evalExpr(e.b,env);if(e.op==="mul")return evalExpr(e.a,env)*evalExpr(e.b,env);if(e.op==="pow")return Math.pow(evalExpr(e.a,env),evalExpr(e.b,env));throw Error("Unknown expression");}
 function diff(e,x){if(e.op==="const")return E.c(0);if(e.op==="var")return E.c(e.n===x?1:0);if(e.op==="add")return E.add(diff(e.a,x),diff(e.b,x));if(e.op==="mul")return E.add(E.mul(diff(e.a,x),e.b),E.mul(e.a,diff(e.b,x)));if(e.op==="pow"&&e.b.op==="const")return E.mul(E.mul(E.c(e.b.v),E.pow(e.a,E.c(e.b.v-1))),diff(e.a,x));throw Error("Derivative form not supported");}
 function integrateNumeric(fn,a,b,n=2048){if(n%2)n++;let h=(b-a)/n,sum=fn(a)+fn(b);for(let i=1;i<n;i++)sum+=(i%2?4:2)*fn(a+i*h);return sum*h/3;}
 function substitutePower(k){return {x:"u^"+k,dx:k+"*u^"+(k-1)+" du",power:k};}
 g.UNGSymbolic={E,evalExpr,diff,integrateNumeric,substitutePower};
})(window);
