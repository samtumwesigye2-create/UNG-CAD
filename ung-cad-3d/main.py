import io, json, os, re, secrets, sqlite3, zipfile
from datetime import datetime, timezone
from pathlib import Path
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from slicer import slice_stl
from slicer_cnc import slice_shapes_to_gcode
from operations import migrate, audit, create_revision
from gcode_preview import analyze as analyze_gcode

BASE_DIR=Path(__file__).resolve().parent
DB_PATH=Path(os.getenv("UNG_CAD_3D_DB",str(BASE_DIR/"ung_cad_3d.db")))
app=FastAPI(title="UNG-CAD-3D",version="1.3.0")
def now_iso(): return datetime.now(timezone.utc).isoformat()
def get_connection():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c
def init_db():
    c=get_connection()
    c.execute("CREATE TABLE IF NOT EXISTS scenes (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,data_json TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS machines (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,kind TEXT NOT NULL,connection_type TEXT NOT NULL,config_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,source_name TEXT NOT NULL,machine_file TEXT,status TEXT NOT NULL,error_message TEXT,stats_json TEXT,submitted_by TEXT,created_at TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS api_keys (id INTEGER PRIMARY KEY AUTOINCREMENT,key TEXT NOT NULL UNIQUE,owner_system TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL)")
    c.commit(); migrate(c); c.close()
@app.on_event("startup")
def startup(): init_db()

class SceneIn(BaseModel):
    name:str
    data:dict
class MachineIn(BaseModel):
    name:str
    kind:str
    connection_type:str
    config:dict={}
class CncSliceIn(BaseModel):
    shapes:list
    drawing_name:str="drawing"
    settings:dict={}
class ApiKeyIn(BaseModel):
    owner_system:str
    admin_token:str
class ProjectIn(BaseModel):
    name:str
    state:dict={}
class RevisionIn(BaseModel):
    state:dict
class PreviewIn(BaseModel):
    gcode:str

def log_job(kind,source_name,machine_file,status,error_message,stats,submitted_by):
    c=get_connection()
    q=c.execute("INSERT INTO jobs (kind,source_name,machine_file,status,error_message,stats_json,submitted_by,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (kind,source_name,machine_file,status,error_message,json.dumps(stats) if stats else None,submitted_by,now_iso()))
    c.commit(); job_id=q.lastrowid; c.close(); return job_id

@app.get("/")
def root(): return RedirectResponse(url="/studio.html")
def _page(name):
    p=BASE_DIR/name
    if not p.exists(): raise HTTPException(404,f"{name} not recovered yet")
    return FileResponse(p)
@app.get("/studio.html")
def studio(): return _page("studio.html")
@app.get("/studio")
def studio_short(): return _page("studio.html")
@app.get("/viewer.html")
def viewer(): return _page("viewer.html")
@app.get("/manufacturing.html")
def manufacturing(): return _page("manufacturing.html")
@app.get("/drafting.html")
def drafting(): return _page("drafting.html")
@app.get("/ung-cad-ad5m-bridge.py")
def bridge(): return _page("ung-cad-ad5m-bridge.py")
@app.get("/start-ad5m-bridge.bat")
def bridge_bat(): return _page("start-ad5m-bridge.bat")
@app.get("/start-ad5m-bridge.command")
def bridge_mac(): return _page("start-ad5m-bridge.command")

def printable_entries(names):
    return [n for n in names if n.lower().endswith((".stl",".3mf",".gcode",".gx")) and not n.lower().endswith("draco_gen1_full_assembly_reference.stl")]

@app.post("/api/manufacturing/inspect")
async def inspect(file:UploadFile=File(...)):
    name=file.filename or "project"; data=await file.read()
    if name.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z: entries=printable_entries([n for n in z.namelist() if not n.endswith("/")])
        except zipfile.BadZipFile: raise HTTPException(400,"Invalid ZIP")
    elif name.lower().endswith((".stl",".3mf",".gcode",".gx")): entries=[name]
    else: raise HTTPException(400,"Unsupported project type")
    if not entries: raise HTTPException(400,"No printable files found")
    return {"ok":True,"part_count":len(entries),"parts":[Path(n).name for n in entries],"printer_profile":"FlashForge Adventurer 5M","assembly_reference_excluded":True}

async def read_selected(file,selected):
    data=await file.read()
    if not data: raise HTTPException(400,"Empty package")
    if not selected: raise HTTPException(400,"Select a printable part")
    if (file.filename or "").lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names=printable_entries([n for n in z.namelist() if not n.endswith("/")])
                target=next((n for n in names if Path(n).name==selected or n==selected),None)
                if not target: raise HTTPException(404,"Selected part not found in package")
                return target,z.read(target)
        except zipfile.BadZipFile: raise HTTPException(400,"Invalid ZIP")
    if Path(file.filename or "").name==selected: return file.filename,data
    raise HTTPException(404,"Selected part not found")

def _save_gcode(source_name,gcode,suffix):
    out=BASE_DIR/"generated"; out.mkdir(exist_ok=True)
    safe=re.sub(r"[^A-Za-z0-9_.-]+","_",Path(source_name).stem)
    target=out/(safe+suffix); target.write_bytes(gcode if isinstance(gcode,bytes) else gcode.encode()); return target

@app.post("/api/manufacturing/slice")
async def slice_part(file:UploadFile=File(...),selected:str=Form(...),layer_height:float=Form(0.20)):
    if not 0.08<=layer_height<=0.4: raise HTTPException(400,"Layer height must be 0.08–0.40 mm")
    source,data=await read_selected(file,selected)
    if not source.lower().endswith(".stl"): raise HTTPException(400,"Only STL geometry can be sliced here")
    try: gcode,stats=slice_stl(data,Path(source).name,layer_height=layer_height)
    except Exception as e:
        log_job("3d_printer",Path(source).name,None,"failed",str(e),None,"dashboard"); raise HTTPException(422,f"Slicing failed: {e}")
    target=_save_gcode(source,gcode,"_AD5M.gcode")
    log_job("3d_printer",Path(source).name,target.name,"sliced",None,stats,"dashboard")
    return {"ok":True,"status":"sliced","source":Path(source).name,"machine_file":target.name,"download":f"/api/manufacturing/download/{target.name}","printer":"FlashForge Adventurer 5M","stats":stats,"transmission":"local AD5M bridge required"}

@app.get("/api/manufacturing/download/{name}")
def download_machine_file(name:str):
    target=BASE_DIR/"generated"/Path(name).name
    if not target.exists(): raise HTTPException(404,"Machine file not found")
    return FileResponse(target,media_type="application/octet-stream",filename=target.name)
@app.get("/api/manufacturing/health")
def manufacturing_health(): return {"ok":True,"slicer":"available","printer_profile":"FlashForge Adventurer 5M","direct_railway_printer_connection":False,"local_bridge_required":True}

@app.post("/api/manufacturing/cnc-slice")
def cnc_slice(payload:CncSliceIn):
    mode=payload.settings.get("mode","laser")
    if mode not in ("cnc","laser"): raise HTTPException(400,"settings.mode must be 'cnc' or 'laser'")
    try: gcode,count,seconds=slice_shapes_to_gcode(payload.shapes,payload.settings)
    except Exception as e:
        log_job(mode,payload.drawing_name,None,"failed",str(e),None,"dashboard"); raise HTTPException(422,f"CNC/laser toolpath generation failed: {e}")
    target=_save_gcode(payload.drawing_name,gcode,f"_{mode}.gcode"); stats={"paths":count,"estimated_seconds":seconds,"mode":mode}
    log_job(mode,payload.drawing_name,target.name,"sliced",None,stats,"dashboard")
    return {"ok":True,"status":"sliced","mode":mode,"machine_file":target.name,"download":f"/api/manufacturing/download/{target.name}","stats":stats}

@app.post("/api/machines")
def create_machine(m:MachineIn):
    if m.kind not in ("3d_printer","cnc","laser"): raise HTTPException(400,"invalid machine kind")
    if m.connection_type not in ("bridge_lan","bridge_serial","manual"): raise HTTPException(400,"invalid connection type")
    c=get_connection(); q=c.execute("INSERT INTO machines (name,kind,connection_type,config_json,created_at) VALUES (?,?,?,?,?)",(m.name,m.kind,m.connection_type,json.dumps(m.config),now_iso())); c.commit(); mid=q.lastrowid; c.close()
    return {"id":mid,"status":"created"}
@app.get("/api/machines")
def list_machines():
    c=get_connection(); rows=c.execute("SELECT * FROM machines ORDER BY created_at DESC").fetchall(); c.close()
    out=[]
    for r in rows:
        d=dict(r); d["config"]=json.loads(d.pop("config_json")); out.append(d)
    return out
@app.delete("/api/machines/{machine_id}")
def delete_machine(machine_id:int):
    c=get_connection(); c.execute("DELETE FROM machines WHERE id=?",(machine_id,)); c.commit(); c.close(); return {"status":"deleted"}
@app.get("/api/jobs")
def list_jobs(limit:int=100):
    c=get_connection(); rows=c.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",(limit,)).fetchall(); c.close()
    out=[]
    for r in rows:
        d=dict(r); d["stats"]=json.loads(d.pop("stats_json")) if d.get("stats_json") else None; out.append(d)
    return out

def require_api_key(x_ung_api_key:str=Header(default=None)):
    if not x_ung_api_key: raise HTTPException(401,"Missing X-UNG-API-Key header")
    c=get_connection(); row=c.execute("SELECT * FROM api_keys WHERE key=? AND active=1",(x_ung_api_key,)).fetchone(); c.close()
    if not row: raise HTTPException(401,"Invalid or inactive API key")
    return row["owner_system"]
@app.post("/api/admin/api-keys")
def create_api_key(payload:ApiKeyIn):
    expected=os.getenv("UNG_CAD_ADMIN_TOKEN")
    if not expected or payload.admin_token!=expected: raise HTTPException(403,"Invalid admin token")
    key=secrets.token_urlsafe(32); c=get_connection(); c.execute("INSERT INTO api_keys (key,owner_system,active,created_at) VALUES (?,?,1,?)",(key,payload.owner_system,now_iso())); c.commit(); c.close()
    return {"api_key":key,"owner_system":payload.owner_system}

@app.post("/api/v1/slice/3d")
async def api_slice_3d(file:UploadFile=File(...),layer_height:float=Form(0.20),owner_system:str=Depends(require_api_key)):
    if not 0.08<=layer_height<=0.4: raise HTTPException(400,"Layer height must be 0.08–0.40 mm")
    data=await file.read()
    try: gcode,stats=slice_stl(data,file.filename,layer_height=layer_height)
    except Exception as e:
        log_job("3d_printer",file.filename,None,"failed",str(e),None,owner_system); raise HTTPException(422,f"Slicing failed: {e}")
    target=_save_gcode(file.filename,gcode,"_AD5M.gcode"); job_id=log_job("3d_printer",file.filename,target.name,"sliced",None,stats,owner_system)
    return {"ok":True,"job_id":job_id,"machine_file":target.name,"download":f"/api/manufacturing/download/{target.name}","stats":stats}
@app.post("/api/v1/slice/cnc")
def api_slice_cnc(payload:CncSliceIn,owner_system:str=Depends(require_api_key)):
    mode=payload.settings.get("mode","laser")
    if mode not in ("cnc","laser"): raise HTTPException(400,"settings.mode must be 'cnc' or 'laser'")
    try: gcode,count,seconds=slice_shapes_to_gcode(payload.shapes,payload.settings)
    except Exception as e:
        job_id=log_job(mode,payload.drawing_name,None,"failed",str(e),None,owner_system); raise HTTPException(422,f"CNC/laser toolpath generation failed: {e}")
    target=_save_gcode(payload.drawing_name,gcode,f"_{mode}.gcode"); stats={"paths":count,"estimated_seconds":seconds,"mode":mode}; job_id=log_job(mode,payload.drawing_name,target.name,"sliced",None,stats,owner_system)
    return {"ok":True,"job_id":job_id,"machine_file":target.name,"download":f"/api/manufacturing/download/{target.name}","stats":stats}
@app.get("/api/v1/jobs/{job_id}")
def api_get_job(job_id:int,owner_system:str=Depends(require_api_key)):
    c=get_connection(); row=c.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone(); c.close()
    if not row: raise HTTPException(404,"Job not found")
    d=dict(row); d["stats"]=json.loads(d.pop("stats_json")) if d.get("stats_json") else None; return d
@app.get("/api/v1/machines")
def api_list_machines(owner_system:str=Depends(require_api_key)): return list_machines()

@app.get("/api/scenes")
def list_scenes():
    c=get_connection(); rows=c.execute("SELECT id,name,created_at,updated_at FROM scenes ORDER BY updated_at DESC").fetchall(); c.close(); return [dict(r) for r in rows]
@app.get("/api/scenes/{scene_id}")
def get_scene(scene_id:int):
    c=get_connection(); row=c.execute("SELECT * FROM scenes WHERE id=?",(scene_id,)).fetchone(); c.close()
    if not row: raise HTTPException(404,"Scene not found")
    d=dict(row); d["data"]=json.loads(d.pop("data_json")); return d
@app.post("/api/scenes")
def create_scene(scene:SceneIn):
    c=get_connection(); n=now_iso(); q=c.execute("INSERT INTO scenes (name,data_json,created_at,updated_at) VALUES (?,?,?,?)",(scene.name,json.dumps(scene.data),n,n)); c.commit(); i=q.lastrowid; c.close(); return {"id":i,"status":"created"}
@app.put("/api/scenes/{scene_id}")
def update_scene(scene_id:int,scene:SceneIn):
    c=get_connection()
    if not c.execute("SELECT id FROM scenes WHERE id=?",(scene_id,)).fetchone(): c.close(); raise HTTPException(404,"Scene not found")
    c.execute("UPDATE scenes SET name=?,data_json=?,updated_at=? WHERE id=?",(scene.name,json.dumps(scene.data),now_iso(),scene_id)); c.commit(); c.close(); return {"status":"updated"}
@app.delete("/api/scenes/{scene_id}")
def delete_scene(scene_id:int):
    c=get_connection(); c.execute("DELETE FROM scenes WHERE id=?",(scene_id,)); c.commit(); c.close(); return {"status":"deleted"}


@app.post("/api/projects")
def create_project(p:ProjectIn):
    c=get_connection(); n=now_iso()
    q=c.execute("INSERT INTO projects(name,state_json,created_at,updated_at) VALUES(?,?,?,?)",(p.name,json.dumps(p.state),n,n))
    c.commit(); pid=q.lastrowid; create_revision(c,pid,p.state); audit(c,"dashboard","project.created","project",pid); c.close()
    return {"id":pid,"status":"created"}

@app.get("/api/projects")
def list_projects():
    c=get_connection(); rows=c.execute("SELECT id,name,created_at,updated_at FROM projects ORDER BY updated_at DESC").fetchall(); c.close()
    return [dict(r) for r in rows]

@app.put("/api/projects/{project_id}")
def save_project(project_id:int,p:ProjectIn):
    c=get_connection()
    if not c.execute("SELECT id FROM projects WHERE id=?",(project_id,)).fetchone(): c.close(); raise HTTPException(404,"Project not found")
    c.execute("UPDATE projects SET name=?,state_json=?,updated_at=? WHERE id=?",(p.name,json.dumps(p.state),now_iso(),project_id)); c.commit()
    rev=create_revision(c,project_id,p.state); audit(c,"dashboard","project.saved","project",project_id,{"revision":rev}); c.close()
    return {"status":"saved","revision":rev}

@app.get("/api/projects/{project_id}/revisions")
def revisions(project_id:int):
    c=get_connection(); rows=c.execute("SELECT id,revision_no,created_at FROM revisions WHERE project_id=? ORDER BY revision_no DESC",(project_id,)).fetchall(); c.close()
    return [dict(r) for r in rows]

@app.post("/api/gcode/preview")
def gcode_preview(payload:PreviewIn):
    return analyze_gcode(payload.gcode)

@app.get("/api/audit")
def audit_log(limit:int=100):
    c=get_connection(); rows=c.execute("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT ?",(min(max(limit,1),500),)).fetchall(); c.close()
    out=[]
    for r in rows:
        d=dict(r); d["details"]=json.loads(d.pop("details_json") or "{}"); out.append(d)
    return out

@app.get("/health")
def health(): return {"system":"UNG-CAD-3D","status":"ok","ui":"/studio.html","manufacturing":"/manufacturing.html","drafting":"/drafting.html (now with CNC/laser G-code export)","ad5m_bridge":"/ung-cad-ad5m-bridge.py","external_api":"/api/v1/* (requires X-UNG-API-Key header)"}
app.mount("/static",StaticFiles(directory=BASE_DIR),name="static")
