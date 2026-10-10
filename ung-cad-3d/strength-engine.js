/*
 * UNG-CAD strength engine
 *  - stressCheck(): simple beam-theory stress check for a printed part
 *    (part treated as a cantilever: one end held, load at the other end).
 *  - sectionProperties(): exact cross-section of a triangle mesh at a plane,
 *    measured by scanline fill (holes handled by even-odd rule).
 *  - explodeOffsets(): pull assembly parts apart from the assembly centre.
 *
 * Honest scope: this is a hand-calculation check (sigma = M*c/I, unit-load
 * deflection), not finite-element analysis. It ignores shear, twisting and
 * stress concentrations at sharp corners/holes, and assumes the section is solid.
 */
(function(root,factory){
  const api=factory();
  if(typeof module!=='undefined'&&module.exports) module.exports=api;
  if(root) root.UNGStrength=api;
})(typeof window!=='undefined'?window:globalThis,function(){
  const AX=['x','y','z'];
  // Typical values for FDM prints. XY = along the printed lines (in-plane).
  // Z = pulling layers apart; no single published number exists, so a
  // conservative fraction of XY is used (PETG bonds layers better).
  // Sources: in-plane tensile ranges PLA 50-60, PETG 40-50, ABS 34-36 MPa
  // (wevolver.com strength comparison); lower bound used. Moduli are common datasheet values.
  const MATERIALS={
    PLA :{strengthXY:50,zFactor:.50,modulus:3000,label:'PLA'},
    PETG:{strengthXY:40,zFactor:.65,modulus:2000,label:'PETG'},
    ABS :{strengthXY:34,zFactor:.50,modulus:2100,label:'ABS'},
  };
  const G=9.80665;

  function boundsOf(tris){
    const min={x:Infinity,y:Infinity,z:Infinity},max={x:-Infinity,y:-Infinity,z:-Infinity};
    for(const t of tris)for(const p of[t.a,t.b,t.c])for(const k of AX){if(p[k]<min[k])min[k]=p[k];if(p[k]>max[k])max[k]=p[k];}
    return{min,max,size:{x:max.x-min.x,y:max.y-min.y,z:max.z-min.z}};
  }

  // Cut every triangle with the plane {axis = value}; returns 2D segments in (u,v).
  function sliceSegments(tris,axis,value,u,v){
    const segs=[];
    for(const t of tris){
      const P=[t.a,t.b,t.c],d=P.map(p=>p[axis]-value),pts=[];
      for(let i=0;i<3;i++){
        const j=(i+1)%3;
        if((d[i]<0)!==(d[j]<0)){const s=d[i]/(d[i]-d[j]);pts.push([P[i][u]+(P[j][u]-P[i][u])*s,P[i][v]+(P[j][v]-P[i][v])*s]);}
      }
      if(pts.length===2)segs.push(pts);
    }
    return segs;
  }

  // Section properties by scanline fill. w = the direction the load bends the
  // section in (one of u/v). Returns area, centroid, I about the neutral axis,
  // and c = distance from neutral axis to the farthest material.
  function sectionProperties(tris,axis,value,loadDir,opts={}){
    const others=AX.filter(k=>k!==axis);
    if(!others.includes(loadDir))throw Error('load direction must be across the part, not along it');
    const w=loadDir,q=others.find(k=>k!==w);
    const segs=sliceSegments(tris,axis,value,w,q);
    if(!segs.length)return{area:0,I:0,c:0,centroid:0,segments:0};
    let wMin=Infinity,wMax=-Infinity;
    for(const s of segs)for(const p of s){if(p[0]<wMin)wMin=p[0];if(p[0]>wMax)wMax=p[0];}
    const rows=opts.rows||400,h=(wMax-wMin)/rows;
    if(!(h>0))return{area:0,I:0,c:0,centroid:0,segments:segs.length};
    // Each row is a strip of height h at w = wi; its width is the total inside length.
    let A=0,Sw=0,Sww=0,lo=Infinity,hi=-Infinity;
    for(let r=0;r<rows;r++){
      const wi=wMin+(r+.5)*h,xs=[];
      for(const [p0,p1] of segs){
        const a=p0[0],b=p1[0];
        if(a===b)continue;
        if((wi>=Math.min(a,b))&&(wi<Math.max(a,b))){const s=(wi-a)/(b-a);xs.push(p0[1]+(p1[1]-p0[1])*s);}
      }
      if(xs.length<2)continue;
      xs.sort((m,n)=>m-n);
      let width=0;for(let k=0;k+1<xs.length;k+=2)width+=xs[k+1]-xs[k];
      if(width<=0)continue;
      const dA=width*h;A+=dA;Sw+=dA*wi;Sww+=dA*(wi*wi+h*h/12);
      if(wi-h/2<lo)lo=wi-h/2;if(wi+h/2>hi)hi=wi+h/2;
    }
    if(A<=0)return{area:0,I:0,c:0,centroid:0,segments:segs.length};
    const wc=Sw/A,I=Sww-A*wc*wc,c=Math.max(wc-lo,hi-wc);
    return{area:A,I,c,centroid:wc,segments:segs.length};
  }

  function stressCheck(tris,opts={}){
    if(!tris||tris.length<4)throw Error('no part geometry loaded');
    const mat=MATERIALS[opts.material]||null;
    if(!mat)throw Error('stress check supports PLA, PETG and ABS (TPU is flexible and is not checked this way)');
    const b=boundsOf(tris);
    const axis=(opts.axis&&opts.axis!=='auto')?opts.axis:AX.reduce((m,k)=>b.size[k]>b.size[m]?k:m,'x');
    const across=AX.filter(k=>k!==axis);
    let loadDir=opts.loadDir&&opts.loadDir!=='auto'?opts.loadDir:(across.includes('z')?'z':across[0]);
    if(!across.includes(loadDir))throw Error('the load must push across the part, not along its length');
    const fixedAtMin=(opts.fixed||'min')==='min';
    const L=b.size[axis];if(!(L>0))throw Error('part has no length');
    const F=opts.loadN!=null?Number(opts.loadN):Number(opts.loadKg||0)*G;
    if(!(F>0))throw Error('enter a load greater than zero');
    const n=Math.max(8,Math.min(200,opts.slices||60)),ds=L/n,E=mat.modulus;
    // Printed layers stack along Z. Bending stress runs along the part's length,
    // so a part standing upright (length along Z) is pulled across its layers.
    const acrossLayers=axis==='z';
    const strength=acrossLayers?mat.strengthXY*mat.zFactor:mat.strengthXY;
    const sections=[];let deflection=0,missing=0;
    for(let k=0;k<n;k++){
      const s=(k+.5)*ds;                         // distance from held end
      const coord=fixedAtMin?b.min[axis]+s:b.max[axis]-s;
      const sp=sectionProperties(tris,axis,coord+L*1e-7,loadDir,{rows:opts.rows||300});
      const M=F*(L-s);                           // bending moment, N*mm
      if(sp.I<=0){missing++;sections.push({s,coord,area:0,I:0,c:0,M,sigma:Infinity});continue;}
      const sigma=M*sp.c/sp.I;                    // MPa (N/mm^2)
      deflection+=F*(L-s)*(L-s)/(E*sp.I)*ds;      // unit-load method, mm
      sections.push({s,coord,area:sp.area,I:sp.I,c:sp.c,M,sigma});
    }
    const solid=sections.filter(x=>Number.isFinite(x.sigma));
    if(!solid.length)throw Error('could not find solid material along the part');
    const weakest=solid.reduce((m,x)=>x.sigma>m.sigma?x:m,solid[0]);
    const safety=strength/weakest.sigma;
    const verdict=safety>=3?'OK':safety>=1.5?'MARGINAL':'LIKELY TO BREAK';
    // triangles touching the weakest slice, for highlighting
    const highlight=[];
    tris.forEach((t,i)=>{const lo=Math.min(t.a[axis],t.b[axis],t.c[axis]),hi=Math.max(t.a[axis],t.b[axis],t.c[axis]);if(hi>=weakest.coord-ds&&lo<=weakest.coord+ds)highlight.push(i);});
    return{axis,loadDir,fixed:fixedAtMin?'min':'max',length:L,loadN:F,material:mat.label,
      strengthUsed:strength,acrossLayers,modulus:E,sections,weakest,safetyFactor:safety,
      deflection,verdict,gaps:missing,highlight};
  }

  // Move each part away from the assembly centre. factor 0 = assembled.
  function explodeOffsets(parts,factor){
    const f=Math.max(0,Number(factor)||0);
    const boxes=parts.map(p=>boundsOf(p.tris));
    const all={min:{},max:{}};for(const k of AX){all.min[k]=Math.min(...boxes.map(x=>x.min[k]));all.max[k]=Math.max(...boxes.map(x=>x.max[k]));}
    const C={},D=Math.hypot(...AX.map(k=>all.max[k]-all.min[k]))||1;
    for(const k of AX)C[k]=(all.min[k]+all.max[k])/2;
    let stacked=0;
    return boxes.map((bx,i)=>{
      const d={};for(const k of AX)d[k]=(bx.min[k]+bx.max[k])/2-C[k];
      if(Math.hypot(d.x,d.y,d.z)<.05*D){ // centred part: lift it so it still separates
        stacked++;return{name:parts[i].name,x:0,y:0,z:f*D*.5*stacked};
      }
      return{name:parts[i].name,x:d.x*f,y:d.y*f,z:d.z*f};
    });
  }

  return{MATERIALS,sliceSegments,sectionProperties,stressCheck,explodeOffsets};
});
