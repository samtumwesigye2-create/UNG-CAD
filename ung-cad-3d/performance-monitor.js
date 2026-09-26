/* Lightweight CAD command telemetry with no external transmission. */
(function(g){'use strict';class Perf{
 constructor(limit=250){this.limit=limit;this.samples=[]}
 async measure(name,fn){const t=performance.now();try{return await fn()}finally{this.samples.push({name,ms:performance.now()-t,at:Date.now()});if(this.samples.length>this.limit)this.samples.shift()}}
 summary(){const m={};for(const s of this.samples)(m[s.name]??=[]).push(s.ms);return Object.fromEntries(Object.entries(m).map(([k,v])=>[k,{count:v.length,avgMs:v.reduce((a,b)=>a+b,0)/v.length,maxMs:Math.max(...v)}]))}
 clear(){this.samples.length=0}
}g.UNGCADPerformance=new Perf();})(window);