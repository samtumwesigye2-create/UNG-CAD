/* UNG-CAD shared exact/numerical engineering math.
 * Integrates series convergence, polyhedral proof helpers and unit-aware electrical relations.
 */
(function(g){'use strict';
const PI=Math.PI;
function factorial(n){n=Number(n);if(!Number.isInteger(n)||n<0)throw new RangeError('factorial requires non-negative integer');let r=1;for(let i=2;i<=n;i++)r*=i;return r}
function ramanujanPi({terms=3}={}){
 terms=Math.max(1,Math.min(12,Math.trunc(terms)));
 let sum=0,last=0;
 for(let m=0;m<terms;m++){
  const term=factorial(4*m)*(1103+26390*m)/(Math.pow(factorial(m),4)*Math.pow(396,4*m));
  sum+=term;last=Math.abs(term);
 }
 const invPi=2*Math.SQRT2/9801*sum,value=1/invPi;
 return{value,terms,absoluteError:Math.abs(value-PI),lastTermMagnitude:last,converged:Math.abs(value-PI)<1e-12};
}
function exactLength(coeff=1,radicand=1){coeff=Number(coeff);radicand=Number(radicand);if(!(radicand>=0))throw new RangeError('radicand must be >= 0');return{exact:coeff===1?`sqrt(${radicand})`:`${coeff}*sqrt(${radicand})`,value:coeff*Math.sqrt(radicand)}}
function cubeProof(a=1){
 a=Number(a);if(!(a>0))throw new RangeError('side must be > 0');
 return{side:a,faceDiagonal:exactLength(a,2),spaceDiagonal:exactLength(a,3),surfaceArea:6*a*a,volume:a*a*a};
}
function regularTetrahedronFromCube(a=1){
 a=Number(a);if(!(a>0))throw new RangeError('cube side must be > 0');
 const edge=a*Math.SQRT2,volume=edge**3/(6*Math.SQRT2),cubeVolume=a**3,cornerTetrahedraRemoved=2*cubeVolume/3;
 return{cubeSide:a,edge:{exact:`${a}*sqrt(2)`,value:edge},volume,cubeVolume,removedVolume:cornerTetrahedraRemoved,keptFraction:volume/cubeVolume};
}
const units=Object.freeze({
 voltage:'V',current:'A',resistance:'ohm',power:'W',energy:'J',frequency:'Hz',
 inductance:'H',capacitance:'F',charge:'C',apparentPower:'VA',reactivePower:'var'
});
function positive(v,name,allowZero=false){v=Number(v);if(!Number.isFinite(v)||(allowZero?v<0:v<=0))throw new RangeError(name+' invalid');return v}
function ohmsLaw({voltage,current,resistance}={}){
 let V=Number(voltage),I=Number(current),R=Number(resistance),known=[V,I,R].filter(Number.isFinite).length;
 if(known<2)throw new Error('Provide any two of voltage, current, resistance');
 if(!Number.isFinite(V))V=I*R;if(!Number.isFinite(I))I=V/R;if(!Number.isFinite(R))R=V/I;
 return{voltage:V,current:I,resistance:R,power:V*I,units:{voltage:'V',current:'A',resistance:'ohm',power:'W'}};
}
function acRLC({resistance=0,inductance=0,capacitance=Infinity,frequency,current,voltage}={}){
 const R=positive(resistance,'resistance',true),f=positive(frequency,'frequency'),L=positive(inductance,'inductance',true),C=capacitance===Infinity?Infinity:positive(capacitance,'capacitance');
 const w=2*PI*f,XL=w*L,XC=C===Infinity?0:1/(w*C),X=XL-XC,Zmag=Math.hypot(R,X),phase=Math.atan2(X,R),pf=Zmag?R/Zmag:1;
 let I=Number(current),V=Number(voltage);if(!Number.isFinite(I)&&Number.isFinite(V))I=V/Zmag;if(!Number.isFinite(V)&&Number.isFinite(I))V=I*Zmag;
 const S=Number.isFinite(V)&&Number.isFinite(I)?V*I:null,P=S==null?null:S*pf,Q=S==null?null:S*Math.sin(phase);
 return{frequency:f,omega:w,resistance:R,inductiveReactance:XL,capacitiveReactance:XC,netReactance:X,impedance:{re:R,im:X,magnitude:Zmag,phaseRad:phase,phaseDeg:phase*180/PI},current:Number.isFinite(I)?I:null,voltage:Number.isFinite(V)?V:null,powerFactor:pf,apparentPower:S,truePower:P,reactivePower:Q};
}
function energy({power,timeSeconds}={}){const P=Number(power),t=positive(timeSeconds,'timeSeconds',true);if(!Number.isFinite(P))throw new RangeError('power invalid');return{joules:P*t,wattHours:P*t/3600}}
function charge({current,timeSeconds}={}){return Number(current)*positive(timeSeconds,'timeSeconds',true)}
function capacitanceFromCharge({charge:Q,voltage:V}={}){V=Number(V);if(!Number.isFinite(Q)||!Number.isFinite(V)||V===0)throw new RangeError('charge/voltage invalid');return Number(Q)/V}
function validateElectrical(state){
 const issues=[];if(state?.frequency!=null&&!(Number(state.frequency)>0))issues.push('frequency must be > 0');
 if(state?.capacitance!=null&&state.capacitance!==Infinity&&!(Number(state.capacitance)>0))issues.push('capacitance must be > 0');
 return{valid:issues.length===0,issues};
}
g.UNGEngineeringMath={ramanujanPi,exactLength,cubeProof,regularTetrahedronFromCube,units,ohmsLaw,acRLC,energy,charge,capacitanceFromCharge,validateElectrical};
})(window);
