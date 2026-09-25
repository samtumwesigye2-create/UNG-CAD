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
function runLive(){
 const g=id=>Number(document.getElementById(id)?.value),mat=document.getElementById('em-core-material')?.value||'custom';
 const mu=mat==='silicon_steel'?4000:mat==='ferrite'?2000:1,area=g('em-core-area')*1e-4;
 const field=analyticalField({turns:g('em-n1'),current_a:Math.max(g('em-i2')*(g('em-n2')/Math.max(g('em-n1'),1)),.001),path_length_m:.25,mu_r:mu,core_area_m2:area});
 const opt=optimize({vin:g('em-v1'),vout:g('em-v1')*(g('em-n2')/Math.max(g('em-n1'),1)),frequency_hz:g('em-freq'),core_area_m2:area,bmax_t:g('em-bmax-limit')});
 state.last={field,opt};window.dispatchEvent(new CustomEvent('ung:em-v2-field',{detail:state.last}));
 const o=document.getElementById('em-v2-output');if(o)o.innerHTML='<b>Analytical field</b><br>B ≈ '+field.B_t.toFixed(4)+' T · H ≈ '+field.H_a_per_m.toFixed(1)+' A/m · Φ ≈ '+field.flux_wb.toExponential(3)+' Wb<br><b>Optimizer</b><br>N₁ '+opt.primary_turns+' · N₂ '+opt.secondary_turns+' · ratio '+opt.ratio.toFixed(4);
}
function open(){const p=document.getElementById('em-v2-panel');if(!p)return;p.style.display=p.style.display==='none'?'block':'none';p.innerHTML='<strong>Electromagnetics V2</strong><button id="em-v2-run">Run Field + Optimize</button><div id="em-v2-output" class="gate"><span class="muted">Ready.</span></div>'+FEATURES.map(x=>'<div class="obj"><b>'+x[1]+'</b><br><span class="muted">'+x[2]+'</span></div>').join('')+'<div class="muted">High-fidelity FEA and standards compliance require validated external solver/material/standards data.</div>';document.getElementById('em-v2-run')?.addEventListener('click',runLive)}
document.addEventListener('DOMContentLoaded',()=>document.getElementById('em-v2-btn')?.addEventListener('click',open));
window.UNGElectromagneticsV2={state,features:FEATURES,open,runLive,analyticalField,optimize};
})();