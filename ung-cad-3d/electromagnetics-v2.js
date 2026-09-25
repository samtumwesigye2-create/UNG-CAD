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
function analyticalField(input){
 const N=Number(input.turns||100),I=Number(input.current_a||1),path=Math.max(Number(input.path_length_m||0.25),1e-6),muR=Math.max(Number(input.mu_r||1),1),area=Math.max(Number(input.core_area_m2||4e-4),1e-9);
 const mu0=4*Math.PI*1e-7,H=N*I/path,B=mu0*muR*H,flux=B*area;
 return {model:'analytical-magnetic-circuit',H_a_per_m:H,B_t:B,flux_wb:flux,assumptions:['uniform core path','linear permeability','no fringing/leakage','not FEA']};
}
function optimize(input){
 const vin=Number(input.vin||120),vout=Number(input.vout||12),f=Math.max(Number(input.frequency_hz||60),1),area=Math.max(Number(input.core_area_m2||4e-4),1e-9),b=Math.max(Number(input.bmax_t||1.2),.01);
 const n1=Math.ceil(vin/(4.44*f*b*area)),n2=Math.max(1,Math.round(n1*vout/vin));
 return {primary_turns:n1,secondary_turns:n2,ratio:n2/n1,model:'first-pass volts-per-turn synthesis',requiresValidation:true};
}
const state={version:'2.1',features:Object.fromEntries(FEATURES.map(x=>[x[0],{enabled:true,status:'scaffolded'}])),studies:[]};
function open(){const p=document.getElementById('em-v2-panel');if(!p)return;p.style.display=p.style.display==='none'?'block':'none';p.innerHTML='<strong>Electromagnetics V2</strong>'+FEATURES.map(x=>'<div class="obj"><b>'+x[1]+'</b><br><span class="muted">'+x[2]+'</span></div>').join('')+'<div class="muted">High-fidelity FEA and standards compliance require validated external solver/material/standards data; this workspace preserves that boundary.</div>'}
document.addEventListener('DOMContentLoaded',()=>document.getElementById('em-v2-btn')?.addEventListener('click',open));
window.UNGElectromagneticsV2={state,features:FEATURES,open,analyticalField,optimize};
})();