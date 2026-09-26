/* UNG-CAD 2D professional drafting extensions */
(function(){
'use strict';
const $=id=>document.getElementById(id), status=$('status'), canvas=$('canvas'), wrap=$('wrap');
const entities=[]; window.UNGCAD2DProfessional={entities};
function say(s){if(status)status.textContent=s}
function download(name,text,type){const u=URL.createObjectURL(new Blob([text],{type})),a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),500)}
function mtext(text='Multiline text',x=30,y=30){entities.push({type:'mtext',text,x,y,style:{font:'Arial',size:14,bold:false,italic:false}});say('MTEXT added');}
function table(rows=3,cols=3){const data=Array.from({length:rows},(_,r)=>Array.from({length:cols},(_,c)=>r===0?'Column '+(c+1):''));entities.push({type:'table',rows,cols,data,x:30,y:60});say(rows+'×'+cols+' table added');}
function qr(text){const q=window.UNGCADPro.qrEntity(text||location.href,30,30,24);entities.push(q);say('QR entity added');}
$('mtext-btn')?.addEventListener('click',()=>{const t=prompt('MTEXT');if(t!==null)mtext(t)});
$('table-btn')?.addEventListener('click',()=>table());
$('qr-btn')?.addEventListener('click',()=>{const t=prompt('QR code content',location.href);if(t!==null)qr(t)});
$('svg-import-btn')?.addEventListener('click',()=>$('svg-file').click());
$('svg-file')?.addEventListener('change',async e=>{const f=e.target.files?.[0];if(!f)return;const parsed=window.UNGCADPro.svgToEntities(await f.text());entities.push(...parsed);say('Imported '+parsed.length+' SVG entities');});
$('data-extract-btn')?.addEventListener('click',()=>download('UNG-CAD-2D-data.json',JSON.stringify({drawing:$('drawing-name')?.value||'Untitled',entities},null,2),'application/json'));
$('detach-btn')?.addEventListener('click',()=>window.UNGCADPro.openDetached(location.href,'UNG-CAD 2D Drawing'));
async function command(){const raw=$('pro2d-command').value.trim(),[cmd,...a]=raw.match(/(?:[^\s"]+|"[^"]*")+/g)||[];if(!cmd)return;const args=a.map(x=>x.replace(/^"|"$/g,''));try{switch(cmd.toUpperCase()){case'MTEXT':mtext(args.join(' '));break;case'TABLE':table(+args[0]||3,+args[1]||3);break;case'QRCODE':qr(args.join(' '));break;case'DATAEXTRACT':$('data-extract-btn').click();break;case'DETACH':$('detach-btn').click();break;case'SVGIMPORT':$('svg-import-btn').click();break;default:throw new Error('Unknown 2D command')} $('pro2d-command').value='';}catch(e){say(e.message)}}
$('pro2d-run')?.addEventListener('click',command);$('pro2d-command')?.addEventListener('keydown',e=>{if(e.key==='Enter')command()});
say('Professional 2D drafting ready • MTEXT • tables • QR • SVG • data extraction');
})();