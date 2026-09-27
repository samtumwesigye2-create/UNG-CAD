/* UNG parametric curve library for sketches, sweeps and visualization. */
(function(g){
 function sample(fn,t0=0,t1=Math.PI*2,n=256){const pts=[];for(let i=0;i<=n;i++){const t=t0+(t1-t0)*i/n;pts.push(fn(t))}return pts}
 const deltoid=(a=1)=>t=>[2*a*Math.cos(t)+a*Math.cos(2*t),2*a*Math.sin(t)-a*Math.sin(2*t),0];
 const hypotrochoid=(R=5,r=3,d=5)=>t=>[(R-r)*Math.cos(t)+d*Math.cos((R-r)/r*t),(R-r)*Math.sin(t)-d*Math.sin((R-r)/r*t),0];
 const butterfly=(s=1)=>t=>{const r=Math.exp(Math.sin(t))-2*Math.cos(4*t)+Math.pow(Math.sin((2*t-Math.PI)/24),5);return[s*r*Math.cos(t),s*r*Math.sin(t),0]};
 const trefoil=(s=1)=>t=>[s*(Math.sin(t)+2*Math.sin(2*t)),s*(Math.cos(t)-2*Math.cos(2*t)),s*(-Math.sin(3*t))];
 function superformula({m=6,a=1,b=1,n1=1,n2=1,n3=1,scale=1}={}){return t=>{const p1=Math.pow(Math.abs(Math.cos(m*t/4)/a),n2),p2=Math.pow(Math.abs(Math.sin(m*t/4)/b),n3);const r=Math.pow(p1+p2,-1/n1);return[scale*r*Math.cos(t),scale*r*Math.sin(t),0]}}
 const epicycloid=(R=3,r=1)=>t=>[(R+r)*Math.cos(t)-r*Math.cos((R+r)/r*t),(R+r)*Math.sin(t)-r*Math.sin((R+r)/r*t),0];
 const hypocycloid=(R=4,r=1)=>t=>[(R-r)*Math.cos(t)+r*Math.cos((R-r)/r*t),(R-r)*Math.sin(t)-r*Math.sin((R-r)/r*t),0];
 g.UNGParametricCurves={sample,deltoid,hypotrochoid,butterfly,trefoil,superformula,epicycloid,hypocycloid};
})(globalThis);
