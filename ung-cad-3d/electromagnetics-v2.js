(function(){
const FEATURES=[
['fea','Magnetic FEA','B/H field, leakage and saturation map interface'],
['optimizer','Automatic Optimizer','Vin/Vout/VA/frequency/thermal/space design synthesis'],
['materials','Traceable Material Library','Core curves, AWG, insulation and bobbin records with provenance'],
['winding','Winding CAD Generator','Layers, turns, insulation, direction and interleaving'],
['equivalent','Equivalent Circuit','R, magnetizing/leakage L and parasitic C model'],
['transient','Transient Simulation','Startup, inrush, waveform and saturation studies'],
['thermal','Thermal Network','Copper/core/hot-spot/airflow/enclosure nodes'],
['drc','Electrical DRC','Insulation, current density, saturation, creepage and clearance checks'],
['codesign','EM/Mechanical Co-design','Core/winding changes drive bobbin, enclosure and mounting geometry'],
['trade','Trade Study','Compare loss, temperature, mass, size and material use'],
['validation','Instrument Validation','Measured waveform/temperature import and prediction comparison'],
['machines','Reusable Magnetic Devices','Inductors, solenoids, relays, electromagnets, WPT coils, motors and generators']
];
const state={version:'2.0-roadmap',features:Object.fromEntries(FEATURES.map(x=>[x[0],{enabled:true,status:'scaffolded'}])),studies:[]};
function open(){const p=document.getElementById('em-v2-panel');if(!p)return;p.style.display=p.style.display==='none'?'block':'none';p.innerHTML='<strong>Electromagnetics V2</strong>'+FEATURES.map(x=>'<div class="obj"><b>'+x[1]+'</b><br><span class="muted">'+x[2]+'</span></div>').join('')+'<div class="muted">High-fidelity FEA and standards compliance require validated external solver/material/standards data; this workspace preserves that boundary.</div>'}
document.addEventListener('DOMContentLoaded',()=>document.getElementById('em-v2-btn')?.addEventListener('click',open));
window.UNGElectromagneticsV2={state,features:FEATURES,open};
})();