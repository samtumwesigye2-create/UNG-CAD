const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const ctx={window:{},performance:{now:()=>1},Date,console};ctx.window.window=ctx.window;ctx.window.UNGCADPro={svgToEntities:()=>[{type:'line'}]};vm.createContext(ctx);
for(const f of ['interoperability.js','geospatial.js','performance-monitor.js','plugin-api.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'..',f),'utf8'),ctx);
assert.ok(ctx.window.UNGCADInterop.registry.capabilities().some(x=>x.format==='svg'&&x.read));
assert.strictEqual(ctx.window.UNGCADInterop.registry.capabilities().find(x=>x.format==='rvt2025').read,false);
const p=ctx.window.UNGCADGeo.webMercator(0,0);assert.ok(Math.abs(p.x)<1e-9&&Math.abs(p.y)<1e-6);
assert.ok(ctx.window.UNGCADPluginAPI);assert.ok(ctx.window.UNGCADPerformance);
console.log('professional platform tests passed');