/* Stable browser plugin surface for UNG-CAD extensions. */
(function(g){'use strict';const plugins=new Map(),hooks=new Map();
function register(plugin){if(!plugin?.id||typeof plugin.activate!=='function')throw new Error('Plugin requires id and activate(api)');if(plugins.has(plugin.id))throw new Error('Plugin already registered: '+plugin.id);plugins.set(plugin.id,plugin);plugin.activate(api);return plugin.id}
function on(name,fn){const s=hooks.get(name)||new Set();s.add(fn);hooks.set(name,s);return()=>s.delete(fn)}
function emit(name,payload){for(const fn of hooks.get(name)||[])fn(payload)}
const api={version:'1.0',register,on,emit,get commands(){return g.UNGCADCommands||null},get interop(){return g.UNGCADInterop?.registry||null},get geo(){return g.UNGCADGeo||null},get performance(){return g.UNGCADPerformance||null}};
g.UNGCADPluginAPI=api;})(window);