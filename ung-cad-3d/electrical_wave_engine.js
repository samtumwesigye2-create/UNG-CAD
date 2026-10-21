/* UNG-CAD AC, phasor and electromagnetic-wave engineering helpers */
(function(g){
 const TAU=2*Math.PI;
 function sinusoid({amplitude=1,frequency=60,phase=0,offset=0}={}){const w=TAU*frequency;return {amplitude,frequency,phase,offset,omega:w,period:1/frequency,value:t=>offset+amplitude*Math.sin(w*t+phase)}}
 function peakToRms(v){return Number(v)/Math.sqrt(2)} function rmsToPeak(v){return Number(v)*Math.sqrt(2)}
 function phasor(magnitude,phase=0){return {re:magnitude*Math.cos(phase),im:magnitude*Math.sin(phase),magnitude,phase}}
 function complex(re=0,im=0){return {re:+re,im:+im}}
 function cadd(a,b){return complex(a.re+b.re,a.im+b.im)} function cmul(a,b){return complex(a.re*b.re-a.im*b.im,a.re*b.im+a.im*b.re)}
 function cdiv(a,b){const d=b.re*b.re+b.im*b.im;if(!d)throw Error("Division by zero impedance");return complex((a.re*b.re+a.im*b.im)/d,(a.im*b.re-a.re*b.im)/d)}
 function polar(z){return {magnitude:Math.hypot(z.re,z.im),phase:Math.atan2(z.im,z.re)}}
 function impedanceRLC({R=0,L=0,C=Infinity,frequency=60}={}){const w=TAU*frequency,xl=w*L,xc=Number.isFinite(C)&&C>0?1/(w*C):0;return complex(R,xl-xc)}
 function acCurrent({voltageRms=120,R=0,L=0,C=Infinity,frequency=60,sourcePhase=0}={}){const z=impedanceRLC({R,L,C,frequency}),v=phasor(voltageRms,sourcePhase),i=cdiv(v,z),p=polar(i);return {current:i,currentRms:p.magnitude,phase:p.phase,impedance:z,impedancePolar:polar(z)}}
 function wave({E0=1,frequency=1e6,phase=0,c=299792458}={}){const omega=TAU*frequency,k=omega/c,B0=E0/c;return {E0,B0,frequency,omega,k,wavelength:c/frequency,E:(z,t)=>E0*Math.sin(k*z-omega*t+phase),B:(z,t)=>B0*Math.sin(k*z-omega*t+phase)}}
 function sampleWaveform(model,duration=model.period||1,points=256){const out=[];for(let i=0;i<=points;i++){const t=duration*i/points;out.push({t,value:model.value(t)})}return out}
 g.UNGElectrical={sinusoid,peakToRms,rmsToPeak,phasor,complex,cadd,cmul,cdiv,polar,impedanceRLC,acCurrent,wave,sampleWaveform};
})(window);
