/* UNG-CAD 2D professional drafting extensions */
(function(){
'use strict';
const $=id=>document.getElementById(id), status=$('status'), canvas=$('canvas'), wrap=$('wrap');
const entities=[]; window.UNGCAD2DProfessional={entities};
const model=()=>window.__ung2dModel;
function say(s){if(status)status.textContent=s}
function download(name,text,type){const u=URL.createObjectURL(new Blob([text],{type})),a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),500)}
function mtext(text='Multiline text',x=30,y=30){const e={type:'mtext',text,x,y,style:{font:'Arial',size:14,bold:false,italic:false}};entities.push(e);model()?.add({t:'label',a:{x,y},text});say('MTEXT added to drawing');}
function table(rows=3,cols=3){const data=Array.from({length:rows},(_,r)=>Array.from({length:cols},(_,c)=>r===0?'Column '+(c+1):''));const e={type:'table',rows,cols,data,x:30,y:60};entities.push(e);model()?.add({t:'table',a:{x:30,y:60},data,cellW:24,cellH:8});say(rows+'×'+cols+' table added to drawing');}
function qr(text){const value=String(text||location.href),q=window.UNGCADPro.qrEntity(value,30,30,24);entities.push(q);const n=21,m=Array.from({length:n},()=>Array(n).fill(false)),finder=(ox,oy)=>{for(let y=0;y<7;y++)for(let x=0;x<7;x++)m[oy+y][ox+x]=(x===0||x===6||y===0||y===6||(x>=2&&x<=4&&y>=2&&y<=4))};finder(0,0);finder(n-7,0);finder(0,n-7);let seed=2166136261;for(const ch of value){seed^=ch.charCodeAt(0);seed=Math.imul(seed,16777619)>>>0}for(let y=0;y<n;y++)for(let x=0;x<n;x++)if(!m[y][x]){seed=(Math.imul(seed,1664525)+1013904223)>>>0;m[y][x]=!!(seed&0x80000000)}model()?.add({t:'qr',a:{x:30,y:30},size:24,matrix:m,text:value});say('QR visual added to drawing');}
$('mtext-btn')?.addEventListener('click',()=>{const t=prompt('MTEXT');if(t!==null)mtext(t)});
$('table-btn')?.addEventListener('click',()=>table());
$('qr-btn')?.addEventListener('click',()=>{const t=prompt('QR code content',location.href);if(t!==null)qr(t)});
$('svg-import-btn')?.addEventListener('click',()=>$('svg-file').click());
$('svg-file')?.addEventListener('change',async e=>{const f=e.target.files?.[0];if(!f)return;const parsed=window.UNGCADPro.svgToEntities(await f.text());entities.push(...parsed);const shapes=[];for(const e of parsed){const a=e.attributes||{},n=v=>parseFloat(v)||0;if(e.type==='line')shapes.push({t:'line',a:{x:n(a.x1),y:n(a.y1)},b:{x:n(a.x2),y:n(a.y2)}});else if(e.type==='rect')shapes.push({t:'rect',a:{x:n(a.x),y:n(a.y)},b:{x:n(a.x)+n(a.width),y:n(a.y)+n(a.height)}});else if(e.type==='circle')shapes.push({t:'circle',a:{x:n(a.cx),y:n(a.cy)},b:{x:n(a.cx)+n(a.r),y:n(a.cy)}});else if(e.type==='text')shapes.push({t:'label',a:{x:n(a.x),y:n(a.y)},text:e.text||''});}model()?.addMany(shapes);say('Imported '+parsed.length+' SVG entities • rendered '+shapes.length);});
$('data-extract-btn')?.addEventListener('click',()=>download('UNG-CAD-2D-data.json',JSON.stringify({drawing:$('drawing-name')?.value||'Untitled',shapes:model()?.shapes||[],professionalEntities:entities},null,2),'application/json'));
$('detach-btn')?.addEventListener('click',()=>window.UNGCADPro.openDetached(location.href,'UNG-CAD 2D Drawing'));
async function command(){const raw=$('pro2d-command').value.trim(),[cmd,...a]=raw.match(/(?:[^\s"]+|"[^"]*")+/g)||[];if(!cmd)return;const args=a.map(x=>x.replace(/^"|"$/g,''));try{switch(cmd.toUpperCase()){case'MTEXT':mtext(args.join(' '));break;case'TABLE':table(+args[0]||3,+args[1]||3);break;case'QRCODE':qr(args.join(' '));break;case'DATAEXTRACT':$('data-extract-btn').click();break;case'DETACH':$('detach-btn').click();break;case'SVGIMPORT':$('svg-import-btn').click();break;default:throw new Error('Unknown 2D command')} $('pro2d-command').value='';}catch(e){say(e.message)}}
$('pro2d-run')?.addEventListener('click',command);$('pro2d-command')?.addEventListener('keydown',e=>{if(e.key==='Enter')command()});
say('Professional 2D drafting ready • MTEXT • tables • QR • SVG • data extraction');
})();