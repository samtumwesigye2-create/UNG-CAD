/* UNG-CAD professional UI bridge */
(function(){
'use strict';
const input=document.getElementById('pro-command'),run=document.getElementById('pro-run'),status=document.getElementById('status');
if(!input||!window.UNGCADPro)return;
const pro=window.UNGCADPro.install(window.CSGEngine);
window.UNGCADCommands=pro;
function setStatus(s){if(status)status.textContent=s}
function parse(line){const m=String(line||'').trim().match(/(?:[^\s"]+|"[^"]*")+/g)||[];return m.map(x=>x.replace(/^"|"$/g,''));}
async function exec(){
 const a=parse(input.value);if(!a.length)return;const cmd=a.shift().toUpperCase();
 try{
  if(cmd==='MOVE'||cmd==='COPY'){
   const ids=(window.__ungCadSelection?.()||[]),delta={x:+a[0]||0,y:+a[1]||0,z:+a[2]||0};
   if(window.__ungCadCommandBridge?.transform){await window.__ungCadCommandBridge.transform(cmd,ids,delta);}
   else throw new Error('Select geometry and use the transform bridge');
  }else if(cmd==='UNION'){
   if(window.__ungCadCommandBridge?.union)await window.__ungCadCommandBridge.union();else document.querySelector('[data-op="union"]')?.click();
  }else if(cmd==='DATAEXTRACT'){
   const data=window.__ungCadCommandBridge?.extract?.()||[];const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'}),u=URL.createObjectURL(blob),x=document.createElement('a');x.href=u;x.download='UNG-CAD-data-extract.json';x.click();setTimeout(()=>URL.revokeObjectURL(u),500);
  }else if(cmd==='DETACH'){window.UNGCADPro.openDetached(a[0]||location.href,'UNG-CAD Drawing');}
  else {await pro.execute(cmd,{},...a);}
  setStatus('Command '+cmd+' complete');input.value='';
 }catch(e){setStatus('Command '+cmd+' — '+e.message);}
}
run.addEventListener('click',exec);input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();exec()}});
window.addEventListener('keydown',e=>{if(e.key==='Escape')input.value='';if((e.ctrlKey||e.metaKey)&&e.key==='/'){e.preventDefault();input.focus()}});
setStatus('Professional command core ready • Ctrl/⌘+/ focuses command line');
})();