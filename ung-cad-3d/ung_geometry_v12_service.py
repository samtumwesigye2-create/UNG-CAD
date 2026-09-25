"""UNG-GEOMETRY browser-safe verification service.
Runs as the local authoritative geometry verifier beside the browser.
"""
import asyncio, base64, io, os, subprocess, tempfile
from pathlib import Path
import trimesh
from aiohttp import web

HOST=os.getenv("UNG_GEOMETRY_HOST","127.0.0.1")
PORT=int(os.getenv("UNG_GEOMETRY_PORT","8080"))
MAX_BYTES=int(os.getenv("UNG_GEOMETRY_MAX_BYTES",str(32*1024*1024)))
ALLOWED={x.strip() for x in os.getenv("UNG_GEOMETRY_ORIGINS",
"http://localhost:8000,http://127.0.0.1:8000,http://localhost:8080,http://127.0.0.1:8080,https://samtumwesigye2-create.github.io").split(",") if x.strip()}

def topology(mesh):
    if isinstance(mesh,trimesh.Scene): mesh=mesh.dump(concatenate=True)
    edges=mesh.edges_sorted
    import numpy as np
    _,counts=np.unique(edges,axis=0,return_counts=True)
    return {"watertight":bool(mesh.is_watertight),"winding_consistent":bool(mesh.is_winding_consistent),
            "is_volume":bool(mesh.is_volume),"boundary_edges":int((counts==1).sum()),
            "nonmanifold_edges":int((counts>2).sum()),"faces":int(len(mesh.faces))}

def verify_bytes(data):
    mesh=trimesh.load(io.BytesIO(data),file_type="stl",force="mesh",process=False)
    pre=topology(mesh)
    if not(pre["watertight"] and pre["winding_consistent"] and pre["is_volume"] and pre["boundary_edges"]==0 and pre["nonmanifold_edges"]==0):
        return {"status":"Blocked","stage2_cgal_verified":False,"topology":pre}
    with tempfile.TemporaryDirectory(prefix="ung-v12-") as td:
        td=Path(td); src=td/"input.stl"; out=td/"verified.stl"; scad=td/"verify.scad"
        src.write_bytes(data)
        scad.write_text('render(convexity=10) import("input.stl", convexity=10);\n')
        try:
            p=subprocess.run(["openscad","-o",str(out),str(scad)],cwd=td,capture_output=True,text=True,timeout=30)
        except FileNotFoundError:
            return {"status":"OpenSCADUnavailable","stage2_cgal_verified":False,"topology":pre}
        except subprocess.TimeoutExpired:
            return {"status":"OpenSCADTimeout","stage2_cgal_verified":False,"topology":pre}
        if p.returncode or not out.exists():
            return {"status":"CGALFailed","stage2_cgal_verified":False,"topology":pre,"log":(p.stderr or p.stdout)[-2000:]}
        verified=trimesh.load(out,force="mesh",process=False); post=topology(verified)
        ok=post["watertight"] and post["winding_consistent"] and post["is_volume"] and post["boundary_edges"]==0 and post["nonmanifold_edges"]==0
        return {"status":"Passed" if ok else "Blocked","stage2_cgal_verified":bool(ok),"topology":post,
                "verified_mesh_b64":base64.b64encode(out.read_bytes()).decode() if ok else None}

@web.middleware
async def cors(request,handler):
    origin=request.headers.get("Origin")
    if origin and origin not in ALLOWED: return web.json_response({"status":"OriginBlocked"},status=403)
    if request.method=="OPTIONS": response=web.Response(status=204)
    else: response=await handler(request)
    if origin in ALLOWED:
        response.headers["Access-Control-Allow-Origin"]=origin
        response.headers["Vary"]="Origin"
        response.headers["Access-Control-Allow-Headers"]="Content-Type,X-UNG-Request-Id,X-UNG-Module-Id"
        response.headers["Access-Control-Allow-Methods"]="GET,POST,OPTIONS"
    return response

async def health(_): return web.json_response({"system":"UNG-GEOMETRY","version":"12-browser","status":"ok","binary_verify":True})
async def verify_mesh(request):
    if request.content_length and request.content_length>MAX_BYTES: raise web.HTTPRequestEntityTooLarge(max_size=MAX_BYTES,actual_size=request.content_length)
    data=await request.read()
    if not data: return web.json_response({"status":"EmptyMesh"},status=400)
    result=await asyncio.to_thread(verify_bytes,data)
    result["request_id"]=request.headers.get("X-UNG-Request-Id")
    result["module_id"]=request.headers.get("X-UNG-Module-Id")
    return web.json_response(result,status=200 if result["status"]=="Passed" else 422)

app=web.Application(client_max_size=MAX_BYTES,middlewares=[cors])
app.router.add_get("/health",health); app.router.add_post("/verify-mesh",verify_mesh); app.router.add_options("/verify-mesh",verify_mesh)
if __name__=="__main__": web.run_app(app,host=HOST,port=PORT)
