(function(){
function n(id){return Number(document.getElementById(id).value)}
function calc(){
 const v1=n('em-v1'),n1=n('em-n1'),n2=n('em-n2'),f=n('em-freq'),out=document.getElementById('em-result');
 if(!(v1>=0&&n1>0&&n2>0&&f>0)){out.innerHTML='<div class="danger">Enter positive turns and frequency.</div>';return}
 const ratio=n2/n1,v2=v1*ratio,type=ratio>1?'step-up':ratio<1?'step-down':'isolation / 1:1';
 out.innerHTML='<div><strong>V₂ ≈ '+v2.toFixed(2)+' V</strong></div><div class="muted">N₂/N₁ '+ratio.toFixed(4)+' · '+type+' · '+f.toFixed(1)+' Hz</div><div class="muted">Ideal no-load estimate. Core saturation, regulation, losses and temperature require material/core data.</div>';
 window.dispatchEvent(new CustomEvent('ung:electromagnetics',{detail:{v1,n1,n2,frequency:f,ratio,v2,type}}));
}
document.addEventListener('DOMContentLoaded',()=>{const b=document.getElementById('em-calc-btn');if(b)b.addEventListener('click',calc);});
})();