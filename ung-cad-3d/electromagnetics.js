(function(){
function n(id){return Number(document.getElementById(id).value)}
function calc(){
 const v1=n('em-v1'),n1=n('em-n1'),n2=n('em-n2'),f=n('em-freq'),area=n('em-core-area'),limit=n('em-bmax-limit'),i2=n('em-i2'),wire=n('em-wire-area'),turnLen=n('em-turn-length'),out=document.getElementById('em-result');
 if(!(v1>=0&&n1>0&&n2>0&&f>0&&area>0&&limit>0&&wire>0&&turnLen>0)){out.innerHTML='<div class="danger">Enter positive turns and frequency.</div>';return}
 const ratio=n2/n1,v2=v1*ratio,type=ratio>1?'step-up':ratio<1?'step-down':'isolation / 1:1',areaM2=area*1e-4,bmax=v1/(4.44*f*n1*areaM2),j=i2/wire,lengthM=n2*turnLen/1000,rho=1.724e-8,resistance=rho*lengthM/(wire*1e-6),copperLoss=i2*i2*resistance,sat=bmax>limit;
 out.innerHTML='<div><strong>V₂ ≈ '+v2.toFixed(2)+' V</strong></div><div class="muted">N₂/N₁ '+ratio.toFixed(4)+' · '+type+' · '+f.toFixed(1)+' Hz</div><div class="'+(sat?'danger':'muted')+'">Flux density ≈ '+bmax.toFixed(3)+' T · limit '+limit.toFixed(2)+' T · '+(sat?'SATURATION RISK':'within entered limit')+'</div><div class="muted">Secondary current density ≈ '+j.toFixed(2)+' A/mm² · R₂ ≈ '+resistance.toFixed(3)+' Ω · copper loss ≈ '+copperLoss.toFixed(2)+' W</div><div class="muted">Engineering estimate: sinusoidal excitation, effective core area, copper at ~20°C. Core loss, leakage, regulation and temperature rise still require material/winding data.</div>';
 window.dispatchEvent(new CustomEvent('ung:electromagnetics',{detail:{v1,n1,n2,frequency:f,ratio,v2,type,bmax,bmaxLimit:limit,saturationRisk:sat,currentDensity:j,resistance,copperLoss}}));
}
document.addEventListener('DOMContentLoaded',()=>{const b=document.getElementById('em-calc-btn');if(b)b.addEventListener('click',calc);});
})();