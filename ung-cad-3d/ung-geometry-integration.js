(function(){
  const DEFAULT_URL='http://127.0.0.1:8080';
  let generation=0;
  function polygonsToSTL(polys,name='ung_geometry_input'){return window.CSGEngine.toSTL(polys,name)}
  function inspect(polys){return window.inspectPolygons?window.inspectPolygons(polys):null}
  async function health(base=DEFAULT_URL){
    try{const r=await fetch(base+'/health',{cache:'no-store'});return r.ok}catch{return false}
  }
  async function verifySTL(polys,meta={}){
    const id=++generation, base=localStorage.getItem('ung_geometry_service')||DEFAULT_URL;
    const local=inspect(polys);
    if(local && !local.watertight)return {status:'LocalTopologyBlocked',local,request_id:id};
    if(!(await health(base)))return {status:'ServiceOffline',local,request_id:id};
    // V12 path-based API cannot safely consume browser-local paths. Prefer binary endpoint
    // when present; otherwise leave authoritative verification pending rather than fabricate it.
    const stl=polygonsToSTL(polys,meta.name||'ung_geometry');
    try{
      const r=await fetch(base+'/verify-mesh',{method:'POST',headers:{
        'Content-Type':'model/stl','X-UNG-Request-Id':String(id),
        'X-UNG-Module-Id':String(meta.module_id||'viewer')
      },body:stl});
      if(r.status===404||r.status===405)return {status:'V12BinaryEndpointRequired',local,request_id:id};
      const result=await r.json();
      if(id!==generation)return {status:'Stale',request_id:id};
      return {...result,local,request_id:id};
    }catch(e){return {status:'ServiceError',error:String(e),local,request_id:id}}
  }
  async function verifyBeforeManufacturing(polys,meta={}){
    const result=await verifySTL(polys,meta);
    window.dispatchEvent(new CustomEvent('ung-geometry-verification',{detail:result}));
    return result;
  }
  window.UNGGeometry={verifySTL,verifyBeforeManufacturing,health,
    serviceURL:()=>localStorage.getItem('ung_geometry_service')||DEFAULT_URL,
    setServiceURL:u=>localStorage.setItem('ung_geometry_service',u)};
})();