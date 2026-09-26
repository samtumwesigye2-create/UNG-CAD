/* UNG-CAD 4D timeline/playback controller. */
(function(){
 const by=id=>document.getElementById(id);
 const state={time:0,duration:10,playing:false,rate:1,last:0};
 function clamp(v,a,b){return Math.max(a,Math.min(b,v))}
 function emit(){
   const d={time_s:state.time,duration_s:state.duration,normalized:state.duration?state.time/state.duration:0,playing:state.playing,rate:state.rate};
   window.dispatchEvent(new CustomEvent("ung:4d-time",{detail:d}));
   const t=by("ung4d-time"); if(t)t.textContent=state.time.toFixed(2)+" s";
   const r=by("ung4d-range"); if(r)r.value=String(state.time);
 }
 function frame(ts){
   if(!state.playing)return;
   if(!state.last)state.last=ts;
   state.time=clamp(state.time+(ts-state.last)/1000*state.rate,0,state.duration); state.last=ts; emit();
   if(state.time>=state.duration){state.playing=false;state.last=0;const b=by("ung4d-play");if(b)b.textContent="▶ Play";return}
   requestAnimationFrame(frame);
 }
 function init(){
   const host=document.createElement("section");host.id="ung4d-timeline";
   host.innerHTML='<div class="ung4d-head"><b>4D Timeline</b><span id="ung4d-time">0.00 s</span></div><input id="ung4d-range" type="range" min="0" max="10" step="0.01" value="0"><div class="ung4d-controls"><button id="ung4d-play" type="button">▶ Play</button><button id="ung4d-reset" type="button">↺ Reset</button><label>Duration <input id="ung4d-duration" type="number" min="0.01" step="0.1" value="10"> s</label><label>Rate <select id="ung4d-rate"><option>.25</option><option>.5</option><option selected>1</option><option>2</option><option>4</option></select>×</label></div><small>Engineering time t — scrub to inspect time-dependent state.</small>';
   document.body.appendChild(host);
   const range=by("ung4d-range"),play=by("ung4d-play");
   range.oninput=()=>{state.time=Number(range.value);state.last=0;emit()};
   play.onclick=()=>{state.playing=!state.playing;play.textContent=state.playing?"❚❚ Pause":"▶ Play";state.last=0;if(state.playing)requestAnimationFrame(frame);emit()};
   by("ung4d-reset").onclick=()=>{state.playing=false;state.time=0;state.last=0;play.textContent="▶ Play";emit()};
   by("ung4d-duration").onchange=e=>{state.duration=Math.max(.01,Number(e.target.value)||10);range.max=String(state.duration);state.time=clamp(state.time,0,state.duration);emit()};
   by("ung4d-rate").onchange=e=>{state.rate=Number(e.target.value)||1;emit()};
   window.__ung4dTimeline={state,setTime:t=>{state.time=clamp(Number(t)||0,0,state.duration);emit()},setDuration:d=>{state.duration=Math.max(.01,Number(d)||10);range.max=String(state.duration);emit()}};
   emit();
 }
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();