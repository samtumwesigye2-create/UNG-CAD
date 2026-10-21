/* UNG-CAD Manufacturing — Analyze panel wiring.
 * Connects the Analyze buttons on manufacturing.html to the 3D preview hooks
 * (manufacturing-preview.js) and the maths engines (analyze-engine.js,
 * strength-engine.js). */
(function(){
  const A=window.UNGAnalyze,S=window.UNGStrength,$=id=>document.getElementById(id);
  const box=$('analyzeBox');if(!box||!A)return;
  const say=(id,text)=>{const e=$(id);if(e)e.textContent=text;};
  const f1=x=>Number(x).toFixed(1),f2=x=>Number(x).toFixed(2);
  const currentName=()=>($('part')&&$('part').value)||'part.stl';
  const material=()=>($('material')&&$('material').value)||'PLA';
  const quality=()=>($('quality')&&$('quality').value)||'balanced';
  const guard=(id,fn)=>{const e=$(id);if(e)e.addEventListener('click',()=>{try{fn(e);}catch(err){console.error(err);}});};
  const needPart=out=>{if(window.__analyzeGetCurrent&&window.__analyzeGetCurrent())return true;say(out,'Preview a part first (step 2).');return false;};

  // ---- show the panel once a part is in the preview, and switch tabs ----
  window.__analyzeReady=()=>{box.style.display='block';refreshEstimate();};
  box.querySelectorAll('.an-tabs button').forEach(b=>b.addEventListener('click',()=>{
    box.querySelectorAll('.an-tabs button').forEach(x=>x.classList.toggle('active',x===b));
    box.querySelectorAll('.an-panel').forEach(p=>p.classList.toggle('active',p.id==='an-'+b.dataset.an));
    if(b.dataset.an!=='measure'&&measuring)setMeasure(false);
  }));

  // ---- measure ----
  let measuring=false;
  function setMeasure(on){measuring=on;if(window.__analyzeSetMeasure)window.__analyzeSetMeasure(on);say('measureToggle',on?'Stop measuring':'Start measuring');if(on)say('measureOut','Tap two points on the 3D part.');}
  guard('measureToggle',()=>setMeasure(!measuring));
  guard('measureClear',()=>{if(window.__analyzeClearMeasure)window.__analyzeClearMeasure();say('measureOut','Tap two points on the 3D part.');});
  window.__measureResult=r=>{if(!r)return;say('measureOut','Distance: '+f2(r.distance)+' mm\nAcross (X): '+f2(Math.abs(r.dx))+' mm\nFront–back (Y): '+f2(Math.abs(r.dy))+' mm\nUp (Z): '+f2(Math.abs(r.dz))+' mm');};

  // ---- print estimate ----
  const estText=e=>'≈ '+f1(e.grams)+' g of '+material()+'  ·  '+f1(e.filamentM)+' m filament\n≈ '+Math.round(e.minutes)+' min print  ·  ≈ $'+f2(e.cost)+' of plastic';
  function refreshEstimate(){const t=window.__analyzeGetCurrent&&window.__analyzeGetCurrent();if(!t)return;say('estimateOut',currentName()+'\n'+estText(A.printEstimate(t,{material:material(),quality:quality()})));}
  window.__refreshAnalyzeEstimate=refreshEstimate;
  ['material','quality'].forEach(id=>{const e=$(id);if(e)e.addEventListener('change',refreshEstimate);});
  guard('estimateAll',async()=>{
    const pkg=window.__getPackage&&window.__getPackage(),names=(window.__partNames?window.__partNames():[]).filter(n=>/\.stl$/i.test(n));
    if(!pkg||!names.length){say('estimateOut','Load a package with STL parts first.');return;}
    say('estimateOut','Estimating '+names.length+' parts…');let g=0,m=0,min=0,c=0;const lines=[];
    for(const n of names){const tris=A.trianglesFromPolygons(window.CSGEngine.parseSTL(await extractPartBytes(pkg,n))),e=A.printEstimate(tris,{material:material(),quality:quality()});g+=e.grams;m+=e.filamentM;min+=e.minutes;c+=e.cost;lines.push('● '+n+': '+f1(e.grams)+' g, '+Math.round(e.minutes)+' min');}
    say('estimateOut',lines.join('\n')+'\n\nTotal: '+estText({grams:g,filamentM:m,minutes:min,cost:c}));
  });

  // ---- rotate, resize, mirror ----
  const rot={x:A.rotationX,y:A.rotationY,z:A.rotationZ};
  const sizeText=b=>b?'New size: '+f1(b.size.x)+' × '+f1(b.size.y)+' × '+f1(b.size.z)+' mm':'Preview a part first.';
  box.querySelectorAll('[data-turn]').forEach(b=>b.addEventListener('click',()=>{if(!needPart('rotateOut'))return;say('rotateOut','Turned 90° around '+b.dataset.turn.toUpperCase()+'.\n'+sizeText(window.__analyzeApplyMatrix(rot[b.dataset.turn](90))));}));
  guard('exactTurn',()=>{if(!needPart('rotateOut'))return;const d=Number($('exactDeg').value)||0,ax=$('exactAxis').value;say('rotateOut','Turned '+d+'° around '+ax.toUpperCase()+'.\n'+sizeText(window.__analyzeApplyMatrix(rot[ax](d))));});
  guard('resizePart',()=>{if(!needPart('rotateOut'))return;const p=Number($('scalePct').value);if(!(p>0)){say('rotateOut','Enter a size above 0 %.');return;}const k=p/100;say('rotateOut','Resized to '+p+' %.\n'+sizeText(window.__analyzeApplyMatrix(A.scaling(k,k,k))));$('scalePct').value=100;});
  guard('mirrorX',()=>{if(needPart('rotateOut'))say('rotateOut','Mirrored left–right.\n'+sizeText(window.__analyzeApplyMatrix(A.mirror('x'))));});
  guard('mirrorY',()=>{if(needPart('rotateOut'))say('rotateOut','Mirrored front–back.\n'+sizeText(window.__analyzeApplyMatrix(A.mirror('y'))));});

  // ---- support check & best position ----
  guard('checkSupports',()=>{if(!needPart('supportOut'))return;const r=window.__analyzeSupport(true),total=A.surfaceArea(window.__analyzeGetCurrent());
    say('supportOut',r.indices.length?'Red areas hang over more than 45° and need support.\nOverhang: '+f1(r.area)+' mm² ('+f1(total?r.area/total*100:0)+' % of the surface).\nTry "Best position" to reduce it.':'No overhangs over 45° — this part prints without supports.');});
  guard('hideRed',()=>{if(window.__analyzeHideSupport)window.__analyzeHideSupport();});
  guard('bestPos',()=>{if(!needPart('bestOut'))return;const r=window.__analyzeBestPosition();
    say('bestOut','Part turned to the position with the least overhang.\nOverhang before: '+f1(r.overhangAreaBefore)+' mm²  →  now: '+f1(r.overhangArea)+' mm²\nSize: '+f1(r.size.x)+' × '+f1(r.size.y)+' × '+f1(r.size.z)+' mm'+(r.fits?'':'\n⚠ Does not fit the 220 mm bed in this position.'));});

  // ---- changed-part bar ----
  window.__analyzeChanged=c=>{const b=$('changedBar');if(b)b.style.display=c?'block':'none';};
  guard('saveVersion',async()=>{const t=window.__analyzeGetCurrent();if(!t)return;const n=currentName();try{await window.__replacePart(n,A.toBinarySTL(t,n));window.__analyzeChanged(false);say('status','Saved — printing will now use the changed '+n+'.');}catch(e){say('status','Could not save the change — '+e.message);}});
  guard('undoChanges',()=>{if(window.__analyzeReset)window.__analyzeReset();});

  // ---- stress check ----
  guard('stRun',()=>{
    if(!needPart('stressOut'))return;if(!S){say('stressOut','Strength engine did not load.');return;}
    const amount=Number($('stLoad').value),unit=$('stUnit').value;
    let r;try{r=S.stressCheck(window.__analyzeGetCurrent(),{material:$('stMat').value,axis:$('stAxis').value,fixed:$('stFixed').value,loadDir:$('stDir').value,[unit==='kg'?'loadKg':'loadN']:amount});}
    catch(e){say('stressOut','Cannot check: '+e.message+'.');return;}
    if(window.__analyzeMarkSection)window.__analyzeMarkSection(r.axis,r.weakest.coord);
    const icon=r.verdict==='OK'?'✓':r.verdict==='MARGINAL'?'⚠':'✗';
    const lines=[icon+' '+r.verdict+' — safety factor '+f1(r.safetyFactor)+' (aim for 3 or more)',
      '','Weakest spot (red band): '+f1(r.weakest.s)+' mm from the held end',
      'Stress there: '+f1(r.weakest.sigma)+' MPa  ·  '+r.material+' can take about '+f1(r.strengthUsed)+' MPa',
      'Bends about '+f2(r.deflection)+' mm at the loaded end',
      '','Part length '+f1(r.length)+' mm along '+r.axis.toUpperCase()+', load '+f1(r.loadN)+' N pushing along '+r.loadDir.toUpperCase()+'.'];
    if(r.acrossLayers)lines.push('⚠ The part stands upright, so the load pulls its layers apart — the weakest way to print. Lay it flat if you can; it would be about '+f1(1/S.MATERIALS[r.material].zFactor)+'× stronger.');
    if(r.gaps)lines.push('Note: '+r.gaps+' slice(s) had no material (gaps along the part) and were skipped.');
    lines.push('','Hand calculation, not full simulation: assumes a solid print (use high infill and 4+ walls for loaded parts) and ignores sharp-corner and screw-hole stress.');
    say('stressOut',lines.join('\n'));
  });

  // ---- frames: point converter ----
  const num=id=>Number($(id).value)||0;
  const frame=()=>({x:num('fx'),y:num('fy'),z:num('fz'),rx:num('frx'),ry:num('fry'),rz:num('frz')});
  guard('convertPoint',()=>{const p={x:num('px'),y:num('py'),z:num('pz')},to=$('frameDir').value==='to',q=to?A.toParent(frame(),p):A.fromParent(frame(),p);
    say('frameOut',(to?'Point in the part frame M':'Point in the base frame F')+': ('+[p.x,p.y,p.z].map(f2).join(', ')+')\n→ same point '+(to?'in F':'in M')+': ('+[q.x,q.y,q.z].map(f2).join(', ')+')');});
  const lesson=(vals,text)=>()=>{['fx','fy','fz','frx','fry','frz','px','py','pz'].forEach((id,i)=>$(id).value=vals[i]);$('frameDir').value='to';$('convertPoint').click();say('frameOut',$('frameOut').textContent+'\n\n'+text);};
  guard('lessonTrans',lesson([10,5,0,0,0,0,1,0,0],'Pure translation: the frame only moves, so every point shifts by the same (10, 5, 0).'));
  guard('lessonRot',lesson([0,0,0,0,0,90,1,0,0],'Pure rotation: turning 90° about Z swings the point (1,0,0) round to (0,1,0); distance from the origin stays the same.'));
  guard('lessonBoth',lesson([10,5,0,0,0,90,1,0,0],'Rotation + translation (X = T·x): first turn, then move — (1,0,0) → (0,1,0) → (10,6,0).'));

  // ---- assembly placement, exploded view, fit checks ----
  const rows=$('assemblyRows'),stlNames=()=>(window.__partNames?window.__partNames():[]).filter(n=>/\.stl$/i.test(n));
  function buildRows(){
    const names=stlNames();if(!rows)return;
    const keep={};rows.querySelectorAll('.assembly-row').forEach(r=>keep[r.dataset.name]=r);
    rows.innerHTML=names.length?'<div class="small">Place each part: move (X Y Z mm), turn (X Y Z °), and what it is attached to.</div>':'<div class="small">Load a package with two or more STL parts.</div>';
    names.forEach(n=>{if(keep[n]){rows.appendChild(keep[n]);return;}const d=document.createElement('div');d.className='assembly-row';d.dataset.name=n;
      d.innerHTML='<b>'+n.replace(/[<>&]/g,'')+'</b><br>'+['x','y','z','rx','ry','rz'].map(k=>'<input type="number" data-k="'+k+'" value="0" title="'+k+'">').join('')+'<select data-k="parent"><option value="F">Base frame (F)</option>'+names.filter(o=>o!==n).map(o=>'<option>'+o.replace(/[<>&]/g,'')+'</option>').join('')+'</select>';rows.appendChild(d);});
  }
  const det=rows&&rows.closest('details');if(det)det.addEventListener('toggle',()=>{if(det.open)buildRows();});
  function frames(){const out={};rows.querySelectorAll('.assembly-row').forEach(r=>{const f={};r.querySelectorAll('[data-k]').forEach(i=>f[i.dataset.k]=i.dataset.k==='parent'?i.value:(Number(i.value)||0));out[r.dataset.name]=f;});return out;}
  let assemblyShown=false;
  guard('showAssembly',async()=>{
    buildRows();const pkg=window.__getPackage&&window.__getPackage(),names=stlNames();
    if(!pkg||names.length<2){say('clashOut','An assembly needs two or more STL parts in the package.');return;}
    say('clashOut','Loading '+names.length+' parts…');
    try{const parts=[];for(const n of names)parts.push({name:n,bytes:await extractPartBytes(pkg,n)});
      const b=await window.__showAssembly(parts,frames());assemblyShown=true;if($('explodeRange'))$('explodeRange').value=0;say('explodeState','Assembled');
      say('clashOut','Assembly shown — '+f1(b.size.x)+' × '+f1(b.size.y)+' × '+f1(b.size.z)+' mm overall.\nDrag "Exploded view" to pull the parts apart.');}
    catch(e){say('clashOut','Could not show assembly — '+e.message);}
  });
  const ex=$('explodeRange');if(ex)ex.addEventListener('input',()=>{if(!assemblyShown){say('explodeState','Show the assembly first');return;}const f=Number(ex.value)/100;window.__explodeAssembly(f);say('explodeState',f?'Exploded '+ex.value+' %':'Assembled');});
  const listHits=(hits,none,fmt)=>hits.length?hits.map(fmt).join('\n'):none;
  const needAsm=()=>{if(assemblyShown)return true;say('clashOut','Press "Show assembly" first.');return false;};
  guard('checkClashes',()=>{if(needAsm())say('clashOut',listHits(window.__checkAssemblyClashes(),'✓ No outer boxes overlap.',h=>'⚠ '+h.a+' and '+h.b+' may overlap (outer boxes touch) — run Geometry clash check.'));});
  guard('checkGeometryClashes',()=>{if(needAsm())say('clashOut',listHits(window.__checkAssemblyGeometryClashes(),'✓ No parts pass through each other.',h=>'✗ '+h.a+' goes into '+h.b+'.'));});
  const gap=()=>Math.max(0,Number($('clearanceMm').value)||0.4);
  guard('checkClearance',()=>{if(needAsm())say('clashOut',listHits(window.__checkAssemblyClearance(gap()),'✓ Every gap is at least '+f2(gap())+' mm.',h=>'⚠ '+h.a+' ↔ '+h.b+': only '+f2(h.distance)+' mm apart (want '+f2(gap())+').'));});
  let csv='';
  guard('fitReport',()=>{if(!needAsm())return;const r=window.__assemblyFitReport();csv='part_a,part_b,gap_mm\n'+r.map(h=>'"'+h.a+'","'+h.b+'",'+h.distance.toFixed(3)).join('\n');$('downloadFitCsv').disabled=!r.length;
    say('clashOut',listHits(r,'No part pairs.',h=>(h.distance<=1e-6?'✗ touching/overlapping':h.distance<gap()?'⚠ '+f2(h.distance)+' mm':'✓ '+f2(h.distance)+' mm')+'  '+h.a+' ↔ '+h.b));});
  guard('downloadFitCsv',()=>{if(!csv)return;const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='fit-report.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000);});
  guard('backSingle',()=>{assemblyShown=false;if(window.__backSingle)window.__backSingle();if($('explodeRange'))$('explodeRange').value=0;say('explodeState','Assembled');say('clashOut','Show the assembly, then check for possible overlaps.');});
})();
