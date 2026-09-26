/* UNG-CAD Professional Command Core
 * IntelliCAD-14-class workflow upgrade: command registry, high-speed transforms,
 * batched boolean union, structured extraction, SVG ingestion, QR entities,
 * plugin/API surface and detachable-window messaging.
 */
(function(g){
'use strict';
const now=()=>globalThis.performance?.now?.()??Date.now();
class CommandRegistry{
 constructor(){this.commands=new Map();this.listeners=new Set();}
 register(name,handler,meta={}){if(!name||typeof handler!=='function')throw new TypeError('command requires name and handler');this.commands.set(name.toUpperCase(),{handler,meta});return this;}
 async execute(name,ctx={},...args){const key=String(name).trim().toUpperCase(),c=this.commands.get(key);if(!c)throw new Error('Unknown CAD command: '+key);const t=now();const result=await c.handler(ctx,...args);const event={command:key,ms:now()-t,result};this.listeners.forEach(fn=>fn(event));return result;}
 onExecuted(fn){this.listeners.add(fn);return()=>this.listeners.delete(fn);}
 list(){return [...this.commands].map(([name,v])=>({name,...v.meta}));}
}
const clonePolys=p=>p.map(poly=>({vertices:poly.vertices.map(v=>({pos:{...v.pos},normal:{...v.normal}})),plane:{normal:{...poly.plane.normal},w:poly.plane.w}}));
function move(polys,delta,E=g.CSGEngine){return E.translatePolygons(polys,E.v3(+delta.x||0,+delta.y||0,+delta.z||0));}
function copy(polys,delta,E=g.CSGEngine){return move(clonePolys(polys),delta,E);}
function unionMany(solids,E=g.CSGEngine){const q=solids.filter(x=>x?.length);if(!q.length)return[];while(q.length>1){const n=[];for(let i=0;i<q.length;i+=2)n.push(i+1<q.length?E.csgUnion(q[i],q[i+1]):q[i]);q.splice(0,q.length,...n);}return q[0];}
function extract(objects){return (objects||[]).map((o,i)=>{const b=o.polygons?.length?g.CSGEngine.boundingBox(o.polygons):null;return{id:o.id??i,name:o.name||('Object '+(i+1)),visible:o.visible!==false,polygonCount:o.polygons?.length||0,bounds:b,metadata:o.metadata||{},parametric:o.parametric||null};});}
function svgToEntities(svgText){const doc=new DOMParser().parseFromString(svgText,'image/svg+xml'),num=(v,d=0)=>Number.isFinite(parseFloat(v))?parseFloat(v):d,out=[];doc.querySelectorAll('line,rect,circle,ellipse,polyline,polygon,path,text').forEach((el,i)=>{const a={};for(const n of el.getAttributeNames())a[n]=el.getAttribute(n);out.push({id:'svg-'+i,type:el.tagName.toLowerCase(),attributes:a,text:el.textContent||'',x:num(a.x),y:num(a.y)});});return out;}
function qrEntity(text,x=0,y=0,size=20){return{type:'qr',text:String(text),x:+x||0,y:+y||0,size:Math.max(.1,+size||20),renderHint:'qr-code'};}
function openDetached(url,name='UNG-CAD Drawing'){return window.open(url,name,'popup=yes,resizable=yes,scrollbars=yes');}
function install(E=g.CSGEngine){
 const r=new CommandRegistry();
 r.register('MOVE',(c,d)=>move(c.polygons,d,E),{category:'Modify'});
 r.register('COPY',(c,d)=>copy(c.polygons,d,E),{category:'Modify'});
 r.register('UNION',(c)=>unionMany(c.solids,E),{category:'Solid'});
 r.register('DATAEXTRACT',(c)=>extract(c.objects),{category:'Data'});
 r.register('SVGIMPORT',(c,text)=>svgToEntities(text),{category:'Interoperability'});
 r.register('QRCODE',(c,text,x,y,size)=>qrEntity(text,x,y,size),{category:'Annotate'});
 r.register('DETACH',(c,url,name)=>openDetached(url,name),{category:'Window'});
 return r;
}
g.UNGCADPro={version:'14-class-1.0',CommandRegistry,install,move,copy,unionMany,extract,svgToEntities,qrEntity,openDetached};
g.dispatchEvent?.(new CustomEvent('ungcad:pro-ready',{detail:{version:g.UNGCADPro.version}}));
})(window);
