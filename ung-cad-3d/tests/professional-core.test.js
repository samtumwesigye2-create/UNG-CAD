const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const ctx={window:{dispatchEvent(){},open(){return {}}},CustomEvent:function(){},performance:{now:()=>0},DOMParser:class{parseFromString(){return{querySelectorAll(){return[]}}}}};ctx.window.window=ctx.window;vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname,'..','professional-core.js'),'utf8'),ctx);
assert.ok(ctx.window.UNGCADPro);
const E={v3:(x,y,z)=>({x,y,z}),translatePolygons:(p,d)=>p.map(x=>({...x,d})),csgUnion:(a,b)=>a.concat(b),boundingBox:()=>({min:{x:0,y:0,z:0},max:{x:1,y:1,z:1}})};
const r=ctx.window.UNGCADPro.install(E);
assert.strictEqual(Array.from(r.list(),x=>x.name).join(','),'MOVE,COPY,UNION,DATAEXTRACT,SVGIMPORT,QRCODE,DETACH');
(async()=>{const u=await r.execute('UNION',{solids:[[1],[2],[3]]});assert.strictEqual(u.length,3);console.log('professional-core tests passed')})().catch(e=>{console.error(e);process.exit(1)});
