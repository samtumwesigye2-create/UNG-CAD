/* UNG-CAD interoperability registry: adapters preserve source metadata and fail explicitly. */
(function(g){'use strict';
class AdapterRegistry{
 constructor(){this.adapters=new Map()}
 register(format,adapter){this.adapters.set(String(format).toLowerCase(),adapter);return this}
 capabilities(){return [...this.adapters].map(([format,a])=>({format,read:!!a.read,write:!!a.write,version:a.version||null}))}
 async read(format,input,options={}){const a=this.adapters.get(String(format).toLowerCase());if(!a?.read)throw new Error('No reader for '+format);return a.read(input,options)}
 async write(format,model,options={}){const a=this.adapters.get(String(format).toLowerCase());if(!a?.write)throw new Error('No writer for '+format);return a.write(model,options)}
}
function metadataEnvelope(format,version,entities,source={}){return{schema:'ung-cad.exchange.v1',format,version,source,entities,importedAt:new Date().toISOString()}}
function svgReader(text){return metadataEnvelope('svg','1.x',g.UNGCADPro.svgToEntities(text),{})}
function jsonReader(text){const x=typeof text==='string'?JSON.parse(text):text;if(!x||typeof x!=='object')throw new Error('Invalid exchange document');return x}
const registry=new AdapterRegistry().register('svg',{version:'1.x',read:svgReader}).register('ungjson',{version:'1',read:jsonReader,write:m=>JSON.stringify(m,null,2)});
/* Native DGN/Revit parsing requires licensed/validated backend translators. These descriptors
   let UI/server plugins advertise support without pretending browser JS can parse proprietary files. */
registry.register('dgn',{version:'adapter-required',read:null}).register('rvt2025',{version:'adapter-required',read:null});
g.UNGCADInterop={AdapterRegistry,registry,metadataEnvelope};})(window);