import json, os, sqlite3, zipfile, io, re, secrets, csv, urllib.request, urllib.error, urllib.parse
import trimesh
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cad_core.draco_release_gate import RELEASE_MANIFEST, parse_release_manifest, evaluate_package, allow_selected_slice, is_draco_name
from cad_core.feature_timeline import Point3D, Vector3D, ParametricCircle, ParametricArc, ParametricCylinder, ParametricSphere, ParametricHole, ParametricExtrusion, ParametricRevolve, UNGCadFeatureTimeline, ToleranceExceededError, tessellated_surface_triangles, sphere_manufacturing_triangles, FeatureNode, ParametricDependencyGraph
from cad_core.geometry_validation import validate_triangle_mesh, bed_fit
from cad_core.manufacturability import analyze_fdm_printability
from cad_core.fit_analysis import PrinterCompensationProfile, analyze_compensated_fit, wall_from_opposed_planes, bore_diameter_from_cylinder_radius
from cad_core.calibration_coupon import ad5m_coupon_manifest, ad5m_coupon_parts, measurement_template_rows, derive_compensation_profile
from fastapi import Depends, FastAPI, Header, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from orca_slicer import slice_stl_orca as slice_stl  # real AD5M slicing (fixed)
from slicer_cnc import slice_shapes_to_gcode
from fourd_engine import compile_ad5m_4d, Missing4DMetadataError
# Authorized evidence-analysis router (read-only evidence analytics; no device bypass/acquisition)
try:
    from evidence_api import router as evidence_router
except ImportError:
    evidence_router = None

BASE_DIR=Path(__file__).resolve().parent
DB_PATH=Path(os.getenv("UNG_CAD_3D_DB",str(BASE_DIR/"ung_cad_3d.db")))
app=FastAPI(title="UNG-CAD-3D",version="1.2.0")
# Allow the GitHub Pages front end to call the Railway API.
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,
    allow_origins=["https://samtumwesigye2-create.github.io"],
    allow_methods=["GET","POST","PUT","DELETE","OPTIONS"],
    allow_headers=["*"], expose_headers=["Content-Disposition"])
if evidence_router is not None:
    app.include_router(evidence_router)

def now_iso(): return datetime.now(timezone.utc).isoformat()
def get_connection():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c
def init_db():
    c=get_connection()
    c.execute("CREATE TABLE IF NOT EXISTS scenes (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,data_json TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS print_jobs (id TEXT PRIMARY KEY, printer_id TEXT NOT NULL, machine_file TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, claimed_at TEXT, completed_at TEXT, result_json TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS bridge_status (printer_id TEXT PRIMARY KEY, last_seen TEXT NOT NULL, version TEXT, printer_json TEXT, error TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS print_progress (printer_id TEXT PRIMARY KEY, job_id TEXT, current_layer INTEGER, total_layers INTEGER, percent REAL, machine_state TEXT, updated_at TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS machines (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,kind TEXT NOT NULL,connection_type TEXT NOT NULL,config_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,source_name TEXT NOT NULL,machine_file TEXT,status TEXT NOT NULL,error_message TEXT,stats_json TEXT,submitted_by TEXT,created_at TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS api_keys (id INTEGER PRIMARY KEY AUTOINCREMENT,key TEXT NOT NULL UNIQUE,owner_system TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS twin_bindings (object_key TEXT PRIMARY KEY, object_name TEXT NOT NULL, vector_sku TEXT, draco_device_id TEXT, metadata_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS calibration_profiles (printer_id TEXT NOT NULL, material TEXT NOT NULL, process_key TEXT NOT NULL, profile_json TEXT NOT NULL, measurements_json TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(printer_id,material,process_key))")
    c.commit(); c.close()
@app.get("/")
def home_page():
    return RedirectResponse(url="/studio.html", status_code=302)

@app.on_event("startup")
def startup(): init_db()

feature_timeline_core=UNGCadFeatureTimeline()
feature_dependency_graph=ParametricDependencyGraph()

class ParametricCircleIn(BaseModel):
    entity_id:str
    center:list[float]=[0.0,0.0,0.0]
    radius:float
    normal:list[float]=[0.0,0.0,1.0]

class ParametricActionIn(BaseModel):
    action:str
    value:float
    target_quality:str="ui"

@app.post("/api/cad/parametric/circle")
def create_parametric_circle(body:ParametricCircleIn):
    if len(body.center)!=3 or len(body.normal)!=3: raise HTTPException(400,"center and normal must contain exactly 3 values")
    try:
        circle=ParametricCircle(Point3D(*body.center),body.radius,Vector3D(*body.normal))
        feature_timeline_core.add_circle(body.entity_id,circle)
        return {"entity_id":body.entity_id,"status":"created","meta":{"radius":circle.radius,"center":circle.center.to_array(),"normal":[circle.normal.x,circle.normal.y,circle.normal.z]}}
    except (ValueError,KeyError) as e: raise HTTPException(400,str(e))

@app.post("/api/cad/parametric/{entity_id}/action")
def parametric_action(entity_id:str,body:ParametricActionIn):
    try: return feature_timeline_core.process_api_action(entity_id,body.action,body.value,body.target_quality)
    except KeyError as e: raise HTTPException(404,str(e))
    except (ValueError,NotImplementedError,ToleranceExceededError) as e: raise HTTPException(422,str(e))

class ParametricPrimitiveIn(BaseModel):
    entity_id:str
    primitive_type:str
    params:dict={}
    target_quality:str="ui"

@app.post("/api/cad/parametric/primitive")
def create_parametric_primitive(body:ParametricPrimitiveIn):
    tol=UNGCadFeatureTimeline.QUALITY_TOLERANCES.get(body.target_quality)
    if tol is None: raise HTTPException(400,"target_quality must be ui or export")
    p=body.params
    try:
        center=Point3D(*p.get("center",[0,0,0])); typ=body.primitive_type
        if typ=="arc": obj=ParametricArc(center,float(p["radius"]),float(p.get("start_deg",0)),float(p.get("end_deg",90)),Vector3D(*p.get("normal",[0,0,1]))); data={"vertices":obj.tessellate(tol)}
        elif typ=="cylinder": obj=ParametricCylinder(center,float(p["radius"]),float(p["height"])); s=obj.tessellate(tol); data={"triangles":tessellated_surface_triangles(s)}
        elif typ=="sphere": obj=ParametricSphere(center,float(p["radius"])); data={"triangles":sphere_manufacturing_triangles(obj,tol)}
        elif typ=="hole": obj=ParametricHole(center,float(p["radius"]),float(p["depth"])); s=obj.tessellate(tol); data={"triangles":tessellated_surface_triangles(s),"operation":"subtract"}
        elif typ=="extrusion": obj=ParametricExtrusion(tuple(tuple(x) for x in p["profile"]),float(p["height"])); data={"triangles":tessellated_surface_triangles(obj.tessellate())}
        elif typ=="revolve": obj=ParametricRevolve(tuple(tuple(x) for x in p["profile"]),float(p.get("angle_deg",360))); data={"triangles":tessellated_surface_triangles(obj.tessellate())}
        else: raise ValueError("primitive_type must be arc, cylinder, sphere, hole, extrusion, or revolve")
        return {"entity_id":body.entity_id,"type":typ,"quality":body.target_quality,**data}
    except (KeyError,ValueError,ToleranceExceededError) as e: raise HTTPException(422,str(e))

class FeatureNodeIn(BaseModel):
    id:str
    kind:str
    entity_id:str
    params:dict={}
    parents:list[str]=[]

class FeatureUpdateIn(BaseModel):
    params:dict

@app.post("/api/cad/features")
def add_feature_node(body:FeatureNodeIn):
    try:
        n=feature_dependency_graph.add(FeatureNode(body.id,body.kind,body.entity_id,body.params,tuple(body.parents)))
        return {"status":"created","feature":{"id":n.id,"kind":n.kind,"entity_id":n.entity_id,"params":n.params,"parents":list(n.parents),"revision":n.revision}}
    except (KeyError,ValueError) as e: raise HTTPException(422,str(e))

@app.get("/api/cad/features")
def list_feature_nodes():
    return {"features":feature_dependency_graph.serialize()}

@app.put("/api/cad/features/{feature_id}")
def update_feature_node(feature_id:str,body:FeatureUpdateIn):
    try:
        order=feature_dependency_graph.replace(feature_id,body.params)
        return {"status":"updated","feature_id":feature_id,"regeneration_order":order,"features":feature_dependency_graph.serialize()}
    except KeyError as e: raise HTTPException(404,str(e))

class ParametricExportIn(BaseModel):
    primitive_type:str
    params:dict={}
    target_quality:str="export"
    filename:str="UNG_parametric.stl"

class MeshValidationIn(BaseModel):
    triangles:list
    require_watertight:bool=False
    tolerance:float=1e-9
    build_volume_mm:list[float]|None=None
    bed_clearance_mm:float=0.0

class CompensationProfileIn(BaseModel):
    name:str="uncalibrated"
    nozzle_diameter_mm:float=0.4
    xy_scale_error_fraction:float=0.0
    z_scale_error_fraction:float=0.0
    hole_diameter_error_mm:float=0.0
    slot_width_error_mm:float=0.0
    outer_dimension_error_mm:float=0.0
    clearance_error_mm:float=0.0
    source:str="neutral-default"
    calibrated:bool=False

class FitAnalysisIn(BaseModel):
    target_hole_mm:float
    target_insert_mm:float
    transition_band_mm:float=0.05
    profile:CompensationProfileIn=CompensationProfileIn()

@app.post("/api/manufacturing/fit-analysis")
def manufacturing_fit_analysis(body:FitAnalysisIn):
    try:
        profile=PrinterCompensationProfile(**body.profile.model_dump())
        return {
            "ok":True,
            "analysis":analyze_compensated_fit(
                target_hole_mm=body.target_hole_mm,
                target_insert_mm=body.target_insert_mm,
                profile=profile,
                transition_band_mm=body.transition_band_mm,
            ),
        }
    except ValueError as e:
        raise HTTPException(422,str(e))

class CalibrationMeasurementIn(BaseModel):
    feature:str
    nominal_mm:float
    measured_mm:float

class CalibrationFeedbackIn(BaseModel):
    printer_id:str
    material:str="PLA"
    process_key:str="0.4mm-nozzle_0.20mm-layer"
    profile_name:str="AD5M measured profile"
    measurements:list[CalibrationMeasurementIn]

class ExactBRepFeatureIn(BaseModel):
    kind:str
    values:list[float]

@app.post("/api/cad/exact-feature")
def exact_brep_feature(body:ExactBRepFeatureIn):
    try:
        kind=body.kind.strip().lower()
        if kind=="parallel_wall":
            if len(body.values)!=2: raise ValueError("parallel_wall requires two plane offsets")
            return {"ok":True,"kind":kind,"wall_thickness_mm":wall_from_opposed_planes(body.values[0],body.values[1])}
        if kind=="cylindrical_bore":
            if len(body.values)!=1: raise ValueError("cylindrical_bore requires one radius")
            return {"ok":True,"kind":kind,"bore_diameter_mm":bore_diameter_from_cylinder_radius(body.values[0])}
        raise ValueError("kind must be parallel_wall or cylindrical_bore")
    except ValueError as e:
        raise HTTPException(422,str(e))

@app.post("/api/manufacturing/validate-mesh")
def validate_mesh(body:MeshValidationIn):
    try:
        report=validate_triangle_mesh(
            body.triangles,
            tolerance=body.tolerance,
            require_watertight=body.require_watertight,
        )
        fit=None
        if body.build_volume_mm is not None:
            if report.dimensions is None:
                raise ValueError("Cannot evaluate build-volume fit for an empty mesh.")
            fit=bed_fit(report.dimensions,body.build_volume_mm,clearance=body.bed_clearance_mm)
        status="PASS" if report.valid and (fit is None or fit["fits"]) and not report.warnings else (
            "WARNING" if report.valid and (fit is None or fit["fits"]) else "FAIL"
        )
        return {"ok":report.valid and (fit is None or fit["fits"]),
                "status":status,
                "validation":report.to_dict(),
                "build_volume":fit}
    except (TypeError,ValueError,KeyError) as e:
        raise HTTPException(422,str(e))

def _triangles_to_ascii_stl(triangles,name="UNG_PARAMETRIC"):
    def normal(a,b,c):
        ux,uy,uz=b["x"]-a["x"],b["y"]-a["y"],b["z"]-a["z"]; vx,vy,vz=c["x"]-a["x"],c["y"]-a["y"],c["z"]-a["z"]
        nx,ny,nz=uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx; mag=(nx*nx+ny*ny+nz*nz)**.5
        return (nx/mag,ny/mag,nz/mag) if mag>1e-15 else (0.,0.,0.)
    out=["solid "+name]
    for a,b,c in triangles:
        n=normal(a,b,c);out.append(f" facet normal {n[0]:.9g} {n[1]:.9g} {n[2]:.9g}\n  outer loop")
        for p in (a,b,c):out.append(f"   vertex {p['x']:.9g} {p['y']:.9g} {p['z']:.9g}")
        out.append("  endloop\n endfacet")
    out.append("endsolid "+name);return ("\n".join(out)+"\n").encode()

@app.get("/api/manufacturing/calibration/coupon")
def calibration_coupon():
    manifest=ad5m_coupon_manifest()
    parts=ad5m_coupon_parts()
    mem=io.BytesIO()
    with zipfile.ZipFile(mem,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for name,triangles in parts.items():
            z.writestr(name,_triangles_to_ascii_stl(
                [[{"x":p[0],"y":p[1],"z":p[2]} for p in tri] for tri in triangles],
                Path(name).stem,
            ))
        z.writestr("manifest.json",json.dumps(manifest.to_dict(),indent=2))
        buf=io.StringIO()
        w=csv.DictWriter(buf,fieldnames=["feature_id","feature","nominal_mm","measured_mm"])
        w.writeheader()
        for row in measurement_template_rows(): w.writerow(row)
        z.writestr("measurements.csv",buf.getvalue())
        z.writestr("README.txt",
            "Print these parts with the same material/process you want to calibrate. "
            "Measure with calipers after cooling, fill measurements.csv, then submit the values "
            "to /api/manufacturing/calibration/feedback. No compensation is baked into this coupon.\n")
    return Response(content=mem.getvalue(),media_type="application/zip",
                    headers={"Content-Disposition":"attachment; filename=UNG-CAD_AD5M_calibration_coupon_v1.zip"})

@app.post("/api/manufacturing/calibration/feedback")
def calibration_feedback(body:CalibrationFeedbackIn):
    if not body.printer_id.strip(): raise HTTPException(400,"printer_id is required")
    if not body.measurements: raise HTTPException(400,"at least one measurement is required")
    try:
        rows=[m.model_dump() for m in body.measurements]
        derived=derive_compensation_profile(
            rows,name=body.profile_name,
            source=f"coupon:{body.printer_id}:{body.material}:{body.process_key}",
            nozzle_diameter_mm=0.4,
        )
        profile={k:v for k,v in derived.items() if k not in ("measurement_count","measurements")}
        # Validate against the compensation model before persistence.
        PrinterCompensationProfile(**profile)
    except (TypeError,ValueError,KeyError) as e:
        raise HTTPException(422,str(e))
    c=get_connection();ts=now_iso()
    c.execute("""INSERT INTO calibration_profiles(printer_id,material,process_key,profile_json,measurements_json,updated_at)
                 VALUES(?,?,?,?,?,?) ON CONFLICT(printer_id,material,process_key) DO UPDATE SET
                 profile_json=excluded.profile_json,measurements_json=excluded.measurements_json,updated_at=excluded.updated_at""",
              (body.printer_id.strip(),body.material.strip().upper(),body.process_key.strip(),
               json.dumps(profile),json.dumps(derived["measurements"]),ts))
    c.commit();c.close()
    return {"ok":True,"printer_id":body.printer_id.strip(),"material":body.material.strip().upper(),
            "process_key":body.process_key.strip(),"profile":profile,
            "measurement_count":derived["measurement_count"],"updated_at":ts}

@app.get("/api/manufacturing/calibration/profile/{printer_id}")
def calibration_profile(printer_id:str,material:str="PLA",process_key:str="0.4mm-nozzle_0.20mm-layer"):
    c=get_connection()
    r=c.execute("SELECT * FROM calibration_profiles WHERE printer_id=? AND material=? AND process_key=?",
                (printer_id,material.strip().upper(),process_key)).fetchone()
    c.close()
    if not r:
        neutral=PrinterCompensationProfile().to_dict()
        return {"found":False,"printer_id":printer_id,"material":material.strip().upper(),
                "process_key":process_key,"profile":neutral,
                "warning":"No measured calibration profile stored; neutral compensation is active."}
    return {"found":True,"printer_id":r["printer_id"],"material":r["material"],"process_key":r["process_key"],
            "profile":json.loads(r["profile_json"]),"measurements":json.loads(r["measurements_json"]),
            "updated_at":r["updated_at"]}

def _parametric_triangles(typ,p,tol):
    """Manufacturing-authoritative curved primitive exporter.

    Curved solids must be tessellated from their analytic parameters here.
    Never substitute width/height bounding boxes for circles or cylinders.
    """
    typ=str(typ).strip().lower()
    center=Point3D(*p.get("center",[0,0,0]))
    if typ in {"cylinder","circle"}:
        # A printable circle is a cylindrical solid; require an explicit height
        # instead of silently turning its XY bounds into a rectangular panel.
        radius=float(p.get("radius",float(p["diameter"])/2 if "diameter" in p else 0))
        height=float(p.get("height",p.get("thickness",0)))
        if radius<=0 or height<=0:
            raise ValueError("circle/cylinder STL export requires positive radius (or diameter) and height (or thickness)")
        return tessellated_surface_triangles(ParametricCylinder(center,radius,height).tessellate(tol))
    if typ=="sphere": return sphere_manufacturing_triangles(ParametricSphere(center,float(p["radius"])),tol)
    if typ=="extrusion": return tessellated_surface_triangles(ParametricExtrusion(tuple(tuple(x) for x in p["profile"]),float(p["height"])).tessellate())
    if typ=="revolve": return tessellated_surface_triangles(ParametricRevolve(tuple(tuple(x) for x in p["profile"]),float(p.get("angle_deg",360))).tessellate())
    raise ValueError("STL export supports circle/cylinder, sphere, extrusion, and revolve; curves require a solid operation first")

@app.post("/api/cad/parametric/export-stl")
def export_parametric_stl(body:ParametricExportIn):
    tol=UNGCadFeatureTimeline.QUALITY_TOLERANCES.get(body.target_quality)
    if tol is None: raise HTTPException(400,"target_quality must be ui or export")
    try: triangles=_parametric_triangles(body.primitive_type,body.params,tol)
    except (KeyError,ValueError,ToleranceExceededError) as e: raise HTTPException(422,str(e))
    if not triangles: raise HTTPException(422,"No printable triangles generated")
    report=validate_triangle_mesh(triangles)
    if not report.valid:
        raise HTTPException(422,{"message":"Generated mesh failed manufacturing validation","validation":report.to_dict()})
    safe=re.sub(r"[^A-Za-z0-9_.-]+","_",Path(body.filename).stem)+".stl"
    out=BASE_DIR/"generated";out.mkdir(exist_ok=True);target=out/safe
    target.write_bytes(_triangles_to_ascii_stl(triangles,Path(safe).stem))
    return {"ok":True,"status":"exported","machine_source":safe,"triangles":len(triangles),
            "validation":report.to_dict(),
            "download":f"/api/manufacturing/download/{safe}","next":"/api/manufacturing/slice"}

class TwinBindingIn(BaseModel):
    object_key:str
    object_name:str
    vector_sku:str|None=None
    draco_device_id:str|None=None
    metadata:dict={}
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

@app.get("/")
def root(): return RedirectResponse(url="/studio.html")
@app.get("/studio.html")
def studio(): return FileResponse(BASE_DIR/"studio.html")

@app.get("/viewer.html")
def viewer_page(): return FileResponse(BASE_DIR/"viewer.html")

@app.get("/data-twin.html")
def data_twin_page(): return FileResponse(BASE_DIR/"data-twin.html")

@app.get("/manufacturing.html")
def manufacturing_page(): return FileResponse(BASE_DIR/"manufacturing.html")

@app.get("/drafting.html")
def drafting_page(): return FileResponse(BASE_DIR/"drafting.html")


@app.put("/api/data-twin/bindings/{object_key}")
def put_twin_binding(object_key: str, body: TwinBindingIn):
    if object_key != body.object_key: raise HTTPException(400,"object_key mismatch")
    c=get_connection(); ts=now_iso()
    c.execute("""INSERT INTO twin_bindings(object_key,object_name,vector_sku,draco_device_id,metadata_json,updated_at)
                 VALUES(?,?,?,?,?,?) ON CONFLICT(object_key) DO UPDATE SET object_name=excluded.object_name,vector_sku=excluded.vector_sku,draco_device_id=excluded.draco_device_id,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at""",
              (body.object_key,body.object_name,body.vector_sku,body.draco_device_id,json.dumps(body.metadata),ts))
    c.commit(); c.close(); return {"status":"saved","object_key":object_key,"updated_at":ts}

@app.get("/api/data-twin/bindings/{object_key}")
def get_twin_binding(object_key: str):
    c=get_connection(); r=c.execute("SELECT * FROM twin_bindings WHERE object_key=?",(object_key,)).fetchone(); c.close()
    if not r: raise HTTPException(404,"binding not found")
    return {"object_key":r["object_key"],"object_name":r["object_name"],"vector_sku":r["vector_sku"],"draco_device_id":r["draco_device_id"],"metadata":json.loads(r["metadata_json"] or "{}"),"updated_at":r["updated_at"]}

@app.get("/api/data-twin/bindings")
def list_twin_bindings():
    c=get_connection(); rows=c.execute("SELECT * FROM twin_bindings ORDER BY updated_at DESC").fetchall(); c.close()
    return [{"object_key":r["object_key"],"object_name":r["object_name"],"vector_sku":r["vector_sku"],"draco_device_id":r["draco_device_id"],"metadata":json.loads(r["metadata_json"] or "{}"),"updated_at":r["updated_at"]} for r in rows]

@app.get("/api/data-twin/resolve")
def resolve_data_twin(sku: str = "", device_id: str = ""):
    out={"sku":sku or None,"device_id":device_id or None,"vector":None,"draco":None,"sources":{}}
    vector=os.getenv("UNG_VECTOR_URL","https://ung-vector-production.up.railway.app").rstrip("/")
    draco=os.getenv("UNG_DRACO_URL","https://ung-draco-production-9552.up.railway.app").rstrip("/")
    def pull(label,url):
        try:
            with urllib.request.urlopen(url,timeout=4) as r:
                out[label]=json.loads(r.read().decode()); out["sources"][label]={"url":url,"status":"connected"}
        except Exception as e: out["sources"][label]={"url":url,"status":"unavailable","error":str(e)[:160]}
    if sku: pull("vector",vector+"/v1/digital-twin/product/"+urllib.parse.quote(sku,safe=""))
    if device_id: pull("draco",draco+"/api/draco/v1/device/"+urllib.parse.quote(device_id,safe=""))
    return out

@app.get("/data-twin")
def data_twin_page(): return FileResponse(BASE_DIR/"data-twin.html")
@app.get("/studio")
def studio_short(): return FileResponse(BASE_DIR/"studio.html")
@app.get("/viewer.html")
def viewer(): return FileResponse(BASE_DIR/"viewer.html")
@app.get("/manufacturing.html")
def manufacturing():
    return FileResponse(BASE_DIR/"manufacturing.html",headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0"})
@app.get("/drafting.html")
def drafting(): return FileResponse(BASE_DIR/"drafting.html")
@app.get("/ung-cad-ad5m-bridge.py")
def bridge(): return FileResponse(BASE_DIR/"ung-cad-ad5m-bridge.py",filename="ung-cad-ad5m-bridge.py")
@app.get("/start-ad5m-bridge.bat")
def bridge_bat(): return FileResponse(BASE_DIR/"start-ad5m-bridge.bat",filename="start-ad5m-bridge.bat")
@app.get("/install-ad5m-agent.command")
def install_agent_mac(): return FileResponse(BASE_DIR/"install-ad5m-agent.command",filename="install-ad5m-agent.command",media_type="application/octet-stream")
@app.get("/install-ad5m-agent.bat")
def install_agent_windows(): return FileResponse(BASE_DIR/"install-ad5m-agent.bat",filename="install-ad5m-agent.bat",media_type="application/octet-stream")
@app.get("/start-ad5m-bridge.command")
def bridge_mac(): return FileResponse(BASE_DIR/"start-ad5m-bridge.command",filename="start-ad5m-bridge.command",media_type="application/octet-stream")

def printable_entries(names):
    out=[]
    for n in names:
        low=n.lower()
        if low.endswith((".stl",".glb",".gltf",".obj",".3mf",".gcode",".gx")) and not low.endswith("draco_gen1_full_assembly_reference.stl"): out.append(n)
    return out

@app.post("/api/manufacturing/inspect")
async def inspect(file:UploadFile=File(...)):
    name=file.filename or "project"; data=await file.read(); entries=[]; manifest=None
    if name.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                members=[n for n in z.namelist() if not n.endswith("/")]
                entries=printable_entries(members)
                manifest_name=next((n for n in members if Path(n).name==RELEASE_MANIFEST),None)
                if manifest_name:
                    try: manifest=parse_release_manifest(z.read(manifest_name))
                    except ValueError as e: raise HTTPException(422,str(e))
        except zipfile.BadZipFile: raise HTTPException(400,"Invalid ZIP")
    elif name.lower().endswith((".stl",".glb",".gltf",".obj",".3mf",".gcode",".gx")): entries=[name]
    else: raise HTTPException(400,"Unsupported project type")
    if not entries: raise HTTPException(400,"No printable files found")
    release_ok,blockers=evaluate_package(entries,manifest)
    return {"ok":True,"part_count":len(entries),"parts":[Path(n).name for n in entries],
            "printer_profile":"FlashForge Adventurer 5M","assembly_reference_excluded":True,
            "production_release":{"ready":release_ok,"blockers":blockers,
                                  "p0_only_until_release":bool(blockers and any(is_draco_name(n) for n in entries))}}

async def read_selected(file:UploadFile, selected:str):
    data=await file.read()
    if not data: raise HTTPException(400,"Empty package")
    if not selected: raise HTTPException(400,"Select a printable part")
    if file.filename.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names=printable_entries([n for n in z.namelist() if not n.endswith("/")])
                target=next((n for n in names if Path(n).name==selected or n==selected),None)
                if not target: raise HTTPException(404,"Selected part not found in package")
                return target, z.read(target)
        except zipfile.BadZipFile: raise HTTPException(400,"Invalid ZIP")
    if Path(file.filename).name==selected or not selected: return file.filename,data
    raise HTTPException(404,"Selected part not found")

def _mesh_triangles_for_validation(mesh):
    if isinstance(mesh,trimesh.Scene):
        if not mesh.geometry: raise ValueError("No mesh geometry found")
        mesh=trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if not isinstance(mesh,trimesh.Trimesh) or len(mesh.faces)==0:
        raise ValueError("No triangle mesh geometry found")
    vertices=mesh.vertices
    return [[tuple(float(v) for v in vertices[i]) for i in face] for face in mesh.faces]

@app.post("/api/manufacturing/validate-upload")
async def manufacturing_validate_upload(
    file:UploadFile=File(...),
    selected:str=Form(...),
    require_watertight:bool=Form(False),
    build_x:float=Form(220.0),
    build_y:float=Form(220.0),
    build_z:float=Form(220.0),
    clearance:float=Form(0.0),
    nozzle_diameter:float=Form(0.4),
    layer_height:float=Form(0.2),
    overhang_limit_deg:float=Form(45.0),
    minimum_feature:float=Form(0.4),
):
    source_name,data=await read_selected(file,selected)
    low=source_name.lower()
    if low.endswith((".gcode",".gx")) or low.endswith(".gcode.3mf"):
        return {"ok":True,"status":"PASS","source":Path(source_name).name,
                "machine_ready":True,"validation":None,"build_volume":None}
    if not low.endswith((".stl",".glb",".gltf",".obj")):
        raise HTTPException(400,"Validation supports STL, GLB, GLTF and OBJ geometry")
    try:
        mesh=trimesh.load(io.BytesIO(data),file_type=Path(source_name).suffix.lstrip("."),force="scene")
        triangles=_mesh_triangles_for_validation(mesh)
        report=validate_triangle_mesh(triangles,require_watertight=require_watertight)
        fit=bed_fit(report.dimensions,(build_x,build_y,build_z),clearance=clearance) if report.dimensions else None
        printability=analyze_fdm_printability(
            triangles,
            nozzle_diameter_mm=nozzle_diameter,
            layer_height_mm=layer_height,
            overhang_limit_deg=overhang_limit_deg,
            minimum_feature_mm=minimum_feature,
        )
        ok=report.valid and bool(fit and fit["fits"])
        advisory=bool(report.warnings or printability.warnings)
        status="PASS" if ok and not advisory else ("WARNING" if ok else "FAIL")
        return {"ok":ok,"status":status,"source":Path(source_name).name,
                "machine_ready":False,"validation":report.to_dict(),"build_volume":fit,
                "printability":printability.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(422,f"Could not validate model: {e}")

@app.post("/api/manufacturing/preview-stl")
async def manufacturing_preview_stl(file:UploadFile=File(...), selected:str=Form(...)):
    source_name, data = await read_selected(file, selected)
    low = source_name.lower()
    if low.endswith(".stl"):
        return Response(content=data, media_type="model/stl")
    if not low.endswith((".glb",".gltf",".obj")):
        raise HTTPException(400,"3D preview supports STL, GLB, GLTF and OBJ")
    try:
        mesh = trimesh.load(io.BytesIO(data), file_type=Path(source_name).suffix.lstrip("."), force="scene")
        if isinstance(mesh, trimesh.Scene):
            if not mesh.geometry: raise ValueError("No mesh geometry found")
            mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
        out = mesh.export(file_type="stl")
        return Response(content=out, media_type="model/stl")
    except Exception as e:
        raise HTTPException(422,f"Could not convert model for preview: {e}")

@app.post("/api/manufacturing/slice")
async def slice_part(file:UploadFile=File(...), selected:str=Form(...), layer_height:float=Form(0.20), quality:str=Form("balanced"), material:str=Form("PLA"), supports:str=Form("auto"), copies:int=Form(1), fourd_thermal:bool=Form(False), fourd_material:bool=Form(False), fourd_light:bool=Form(False), fourd_geometry_driven:bool=Form(False), fourd_transition_height:float|None=Form(None), fourd_light_interval_mm:float|None=Form(None)):
    if not (0.08 <= layer_height <= 0.4): raise HTTPException(400,"Layer height must be 0.08–0.40 mm")
    package_bytes=await file.read()
    await file.seek(0)
    release_ok=True; blockers=[]
    if (file.filename or "").lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(package_bytes)) as z:
                members=[n for n in z.namelist() if not n.endswith("/")]
                entries=printable_entries(members)
                manifest_name=next((n for n in members if Path(n).name==RELEASE_MANIFEST),None)
                manifest=parse_release_manifest(z.read(manifest_name)) if manifest_name else None
                release_ok,blockers=evaluate_package(entries,manifest)
        except zipfile.BadZipFile: raise HTTPException(400,"Invalid ZIP")
        except ValueError as e: raise HTTPException(422,str(e))
    elif is_draco_name(file.filename or ""):
        release_ok=False; blockers=["single DRACO production part has no package release manifest"]
    # Manufacturing must remain usable for operator-selected parts.
    # Release-gate findings are advisory here; physical validation/release status
    # is shown to the operator instead of disabling the slicer.
    release_warning = None if release_ok else {"blockers": blockers, "selected": selected}
    source_name, data=await read_selected(file,selected); low=source_name.lower()
    if low.endswith((".gcode",".gx")) or low.endswith(".gcode.3mf"):
        out=BASE_DIR/"generated"; out.mkdir(exist_ok=True)
        safe=re.sub(r"[^A-Za-z0-9_.-]+","_",Path(source_name).name); target=out/safe; target.write_bytes(data)
        return {"ok":True,"status":"machine_file_ready","source":Path(source_name).name,"machine_file":target.name,"download":f"/api/manufacturing/download/{target.name}","printer":"FlashForge Adventurer 5M","stats":{"pre_sliced":True,"machine_package":low.endswith(".gcode.3mf")},"transmission":"local AD5M bridge required","release_warning":release_warning}
    if low.endswith((".glb",".gltf",".obj")):
        try:
            mesh=trimesh.load(io.BytesIO(data),file_type=Path(source_name).suffix.lstrip("."),force="scene")
            if isinstance(mesh,trimesh.Scene):
                if not mesh.geometry: raise ValueError("No mesh geometry found")
                mesh=trimesh.util.concatenate(tuple(mesh.geometry.values()))
            data=mesh.export(file_type="stl")
            source_name=Path(source_name).stem+".stl"
            low=source_name.lower()
        except Exception as e: raise HTTPException(422,f"Model conversion failed: {e}")
    if not low.endswith(".stl"): raise HTTPException(400,"This build slices STL/GLB/GLTF/OBJ and sends pre-sliced G-code/GX/GCODE.3MF machine packages directly")
    try:
        validation_mesh=trimesh.load(io.BytesIO(data),file_type="stl",force="scene")
        validation_report=validate_triangle_mesh(_mesh_triangles_for_validation(validation_mesh))
        validation_fit=bed_fit(validation_report.dimensions,(220.0,220.0,220.0)) if validation_report.dimensions else None
        if not validation_report.valid:
            raise HTTPException(422,{"message":"Manufacturing validation failed before slicing","validation":validation_report.to_dict()})
        if validation_fit is not None and not validation_fit["fits"]:
            raise HTTPException(422,{"message":"Model exceeds Adventurer 5M build volume","validation":validation_report.to_dict(),"build_volume":validation_fit})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(422,f"Manufacturing validation failed before slicing: {e}")
    try:
        gcode,stats=slice_stl(data,Path(source_name).name,layer_height=layer_height)
        printability_report=analyze_fdm_printability(
            _mesh_triangles_for_validation(validation_mesh),
            nozzle_diameter_mm=0.4,
            layer_height_mm=layer_height,
            overhang_limit_deg=45.0,
            minimum_feature_mm=0.4,
        )
        stats["manufacturing_validation"]={"status":"PASS" if not (validation_report.warnings or printability_report.warnings) else "WARNING",
                                           "mesh":validation_report.to_dict(),
                                           "build_volume":validation_fit,
                                           "printability":printability_report.to_dict()}
        if fourd_thermal or fourd_material or fourd_light:
            text_gcode=gcode.decode("utf-8","replace") if isinstance(gcode,bytes) else gcode
            text_gcode=compile_ad5m_4d(text_gcode,thermal=fourd_thermal,material_swap=fourd_material,transition_height_mm=fourd_transition_height,geometry_driven=fourd_geometry_driven,light=fourd_light,light_interval_mm=fourd_light_interval_mm)
            gcode=text_gcode.encode()
            stats["experimental_4d"]={"thermal":fourd_thermal,"material_swap":fourd_material,"light":fourd_light,"geometry_driven":fourd_geometry_driven,"transition_height_mm":fourd_transition_height,"light_interval_mm":fourd_light_interval_mm,"manual_resume_required":bool(fourd_material or fourd_light)}
    except Missing4DMetadataError as e: raise HTTPException(422,str(e))
    except Exception as e: raise HTTPException(422,f"Slicing/4D preparation failed: {e}")
    out=BASE_DIR/"generated"; out.mkdir(exist_ok=True)
    safe=re.sub(r"[^A-Za-z0-9_.-]+","_",Path(source_name).stem); target=out/(safe+"_AD5M.gcode"); target.write_bytes(gcode)
    # PLA-only overhang post-processing runs after slicing/4D compilation and
    # before the machine file is exposed to the local AD5M bridge.
    if str(material).strip().upper()=="PLA":
        try:
            from tools.ung_overhang_fix import process_orcaslicer_pla_overhang_cross_platform
            process_orcaslicer_pla_overhang_cross_platform(str(target))
            stats["pla_overhang_postprocess"]={"enabled":True,"speed_mm_s":20,"fan":255,"temp_drop_c":10,"min_temp_c":190}
        except Exception as e:
            try: target.unlink(missing_ok=True)
            except Exception: pass
            raise HTTPException(422,f"PLA overhang post-processing failed: {e}")
    else:
        stats["pla_overhang_postprocess"]={"enabled":False,"reason":"material is not PLA"}
    return {"ok":True,"status":"sliced","source":Path(source_name).name,"machine_file":target.name,"download":f"/api/manufacturing/download/{target.name}","printer":"FlashForge Adventurer 5M","stats":stats,"transmission":"local AD5M bridge required","release_warning":release_warning}

def _save_gcode(source_name,gcode,suffix):
    out=BASE_DIR/"generated"; out.mkdir(exist_ok=True)
    safe=re.sub(r"[^A-Za-z0-9_.-]+","_",Path(source_name).stem); target=out/(safe+suffix)
    target.write_bytes(gcode if isinstance(gcode,bytes) else gcode.encode()); return target

def log_job(kind,source_name,machine_file,status,error_message,stats,submitted_by):
    c=get_connection(); q=c.execute("INSERT INTO jobs (kind,source_name,machine_file,status,error_message,stats_json,submitted_by,created_at) VALUES (?,?,?,?,?,?,?,?)",(kind,source_name,machine_file,status,error_message,json.dumps(stats) if stats else None,submitted_by,now_iso()))
    c.commit(); job_id=q.lastrowid; c.close(); return job_id

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
    c=get_connection(); q=c.execute("INSERT INTO machines (name,kind,connection_type,config_json,created_at) VALUES (?,?,?,?,?)",(m.name,m.kind,m.connection_type,json.dumps(m.config),now_iso()))
    c.commit(); mid=q.lastrowid; c.close(); return {"id":mid,"status":"created"}

@app.get("/api/machines")
def list_machines():
    c=get_connection(); rows=c.execute("SELECT * FROM machines ORDER BY created_at DESC").fetchall(); c.close(); out=[]
    for r in rows:
        d=dict(r); d["config"]=json.loads(d.pop("config_json")); out.append(d)
    return out

@app.delete("/api/machines/{machine_id}")
def delete_machine(machine_id:int):
    c=get_connection(); c.execute("DELETE FROM machines WHERE id=?",(machine_id,)); c.commit(); c.close(); return {"status":"deleted"}

@app.get("/api/jobs")
def list_jobs(limit:int=100):
    c=get_connection(); rows=c.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",(limit,)).fetchall(); c.close(); out=[]
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
        log_job(mode,payload.drawing_name,None,"failed",str(e),None,owner_system); raise HTTPException(422,f"CNC/laser toolpath generation failed: {e}")
    target=_save_gcode(payload.drawing_name,gcode,f"_{mode}.gcode"); stats={"paths":count,"estimated_seconds":seconds,"mode":mode}; job_id=log_job(mode,payload.drawing_name,target.name,"sliced",None,stats,owner_system)
    return {"ok":True,"job_id":job_id,"machine_file":target.name,"download":f"/api/manufacturing/download/{target.name}","stats":stats}

@app.get("/api/manufacturing/toolpath/{name}")
def toolpath_preview(name:str):
    safe=Path(name).name; target=BASE_DIR/"generated"/safe
    if not target.exists(): raise HTTPException(404,"Machine file not found")
    if not safe.lower().endswith((".gcode",".gx")): raise HTTPException(400,"Toolpath preview requires G-code")
    layers=[]; current={"z":0.0,"segments":[]}; x=y=e=0.0
    try:
        for raw in target.read_text(errors="ignore").splitlines():
            line=raw.strip()
            if line.startswith(";LAYER:"):
                if current["segments"]: layers.append(current)
                current={"z":current["z"],"segments":[]}; continue
            if not line.startswith(("G0 ","G1 ")): continue
            vals={k:float(v) for k,v in re.findall(r"([XYZE])(-?\d+(?:\.\d+)?)",line)}
            nx,ny,nz=vals.get("X",x),vals.get("Y",y),vals.get("Z",current["z"])
            if "Z" in vals: current["z"]=nz
            extruding="E" in vals and vals["E"]>e and (nx!=x or ny!=y)
            if nx!=x or ny!=y: current["segments"].append([round(x,3),round(y,3),round(nx,3),round(ny,3),1 if extruding else 0])
            x,y=nx,ny
            if "E" in vals:e=vals["E"]
        if current["segments"]:layers.append(current)
    except Exception as ex: raise HTTPException(422,f"Could not parse toolpath: {ex}")
    return {"ok":True,"file":safe,"layer_count":len(layers),"layers":layers}

@app.get("/api/manufacturing/download/{name}")
def download_machine_file(name:str):
    safe=Path(name).name; target=BASE_DIR/"generated"/safe
    if not target.exists(): raise HTTPException(404,"Machine file not found")
    return FileResponse(target,media_type="application/octet-stream",filename=safe)

class PrintJobIn(BaseModel):
    printer_id:str
    machine_file:str

@app.post("/api/manufacturing/jobs")
def create_print_job(job:PrintJobIn):
    machine=Path(job.machine_file).name; target=BASE_DIR/"generated"/machine
    if not target.exists(): raise HTTPException(404,"Machine file not found")
    jid=secrets.token_urlsafe(12); c=get_connection(); c.execute("INSERT INTO print_jobs (id,printer_id,machine_file,status,created_at) VALUES (?,?,?,?,?)",(jid,job.printer_id.strip(),machine,"queued",now_iso())); c.commit(); c.close()
    return {"ok":True,"job_id":jid,"status":"queued","printer_id":job.printer_id.strip(),"machine_file":machine}

@app.get("/api/manufacturing/jobs/{job_id}")
def get_print_job(job_id:str):
    c=get_connection(); row=c.execute("SELECT * FROM print_jobs WHERE id=?",(job_id,)).fetchone(); c.close()
    if not row: raise HTTPException(404,"Print job not found")
    r=dict(row); r["result"]=json.loads(r.pop("result_json")) if r.get("result_json") else None; return r

class BridgeHeartbeat(BaseModel):
    printer_id:str
    version:str|None=None
    printer:dict|None=None
    error:str|None=None

@app.post("/api/bridge/heartbeat")
def bridge_heartbeat(body:BridgeHeartbeat):
    c=get_connection(); c.execute("INSERT INTO bridge_status (printer_id,last_seen,version,printer_json,error) VALUES (?,?,?,?,?) ON CONFLICT(printer_id) DO UPDATE SET last_seen=excluded.last_seen,version=excluded.version,printer_json=excluded.printer_json,error=excluded.error",(body.printer_id,now_iso(),body.version,json.dumps(body.printer) if body.printer else None,body.error)); c.commit(); c.close(); return {"ok":True}

@app.get("/api/manufacturing/bridge-status")
def manufacturing_bridge_status(printer_id:str="a51a5435"):
    aliases={"SNMTUF9100669","a51a5435"}; ids=aliases if printer_id in aliases else {printer_id}; marks=",".join("?" for _ in ids)
    c=get_connection(); row=c.execute(f"SELECT * FROM bridge_status WHERE printer_id IN ({marks}) ORDER BY last_seen DESC LIMIT 1",[*ids]).fetchone(); c.close()
    if not row:return {"online":False,"printer_id":printer_id,"reason":"bridge has never checked in"}
    r=dict(row); last=datetime.fromisoformat(r["last_seen"]); age=(datetime.now(timezone.utc)-last).total_seconds()
    return {"online":age<45,"age_seconds":round(age,1),"last_seen":r["last_seen"],"version":r["version"],"printer":json.loads(r["printer_json"]) if r["printer_json"] else None,"error":r["error"]}

@app.get("/api/bridge/jobs/next")
def bridge_next(printer_id:str):
    aliases={"SNMTUF9100669","a51a5435"}; ids=aliases if printer_id in aliases else {printer_id}; marks=",".join("?" for _ in ids); params=[*ids]
    c=get_connection(); row=c.execute(f"SELECT * FROM print_jobs WHERE printer_id IN ({marks}) AND status='queued' ORDER BY created_at LIMIT 1",params).fetchone()
    if not row: c.close(); return {"job":None}
    c.execute("UPDATE print_jobs SET status='claimed',claimed_at=? WHERE id=? AND status='queued'",(now_iso(),row["id"])); c.commit()
    row=c.execute("SELECT * FROM print_jobs WHERE id=?",(row["id"],)).fetchone(); c.close()
    return {"job":{"id":row["id"],"machine_file":row["machine_file"],"download":f"/api/manufacturing/download/{row['machine_file']}"}}

class BridgeResult(BaseModel):
    ok:bool
    result:dict|None=None
    error:str|None=None

@app.post("/api/bridge/jobs/{job_id}/complete")
def bridge_complete(job_id:str, body:BridgeResult):
    c=get_connection(); status="completed" if body.ok else "failed"; result=body.result or {"error":body.error}
    c.execute("UPDATE print_jobs SET status=?,completed_at=?,result_json=? WHERE id=?",(status,now_iso(),json.dumps(result),job_id)); c.commit(); c.close(); return {"ok":True,"status":status}

class BridgeProgress(BaseModel):
    printer_id:str
    job_id:str|None=None
    current_layer:int|None=None
    total_layers:int|None=None
    percent:float|None=None
    machine_state:str|None=None

@app.post("/api/bridge/progress")
def bridge_progress(body:BridgeProgress):
    c=get_connection()
    c.execute("INSERT INTO print_progress (printer_id,job_id,current_layer,total_layers,percent,machine_state,updated_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT(printer_id) DO UPDATE SET job_id=excluded.job_id,current_layer=excluded.current_layer,total_layers=excluded.total_layers,percent=excluded.percent,machine_state=excluded.machine_state,updated_at=excluded.updated_at",(body.printer_id,body.job_id,body.current_layer,body.total_layers,body.percent,body.machine_state,now_iso()))
    c.commit(); c.close(); return {"ok":True}

@app.get("/api/manufacturing/print-progress")
def manufacturing_print_progress(printer_id:str="a51a5435"):
    aliases={"SNMTUF9100669","a51a5435"}; ids=aliases if printer_id in aliases else {printer_id}; marks=",".join("?" for _ in ids)
    c=get_connection(); row=c.execute(f"SELECT * FROM print_progress WHERE printer_id IN ({marks})",[*ids]).fetchone(); c.close()
    if not row: return {"printing":False,"reason":"no progress reported yet"}
    r=dict(row); age=(datetime.now(timezone.utc)-datetime.fromisoformat(r["updated_at"])).total_seconds()
    return {"printing":age<30 and r["machine_state"] not in (None,"READY","IDLE"),"stale":age>=30,"age_seconds":round(age,1),**{k:r[k] for k in ("job_id","current_layer","total_layers","percent","machine_state","updated_at")}}

@app.get("/api/manufacturing/health")
def manufacturing_health():
    return {"ok":True,"slicer":"UNG-CAD Native Slicer 2","printer_profile":"FlashForge Adventurer 5M","direct_railway_printer_connection":False,"local_bridge_required":True}

@app.get("/api/scenes")
def list_scenes():
    c=get_connection(); rows=c.execute("SELECT id,name,created_at,updated_at FROM scenes ORDER BY updated_at DESC").fetchall(); c.close(); return [dict(r) for r in rows]
@app.get("/api/scenes/{scene_id}")
def get_scene(scene_id:int):
    c=get_connection(); row=c.execute("SELECT * FROM scenes WHERE id=?",(scene_id,)).fetchone(); c.close()
    if not row: raise HTTPException(404,"Scene not found")
    r=dict(row); r["data"]=json.loads(r.pop("data_json")); return r
@app.post("/api/scenes")
def create_scene(scene:SceneIn):
    c=get_connection(); n=now_iso(); q=c.execute("INSERT INTO scenes (name,data_json,created_at,updated_at) VALUES (?,?,?,?)",(scene.name,json.dumps(scene.data),n,n)); c.commit(); i=q.lastrowid; c.close(); return {"id":i,"status":"created"}
@app.put("/api/scenes/{scene_id}")
def update_scene(scene_id:int,scene:SceneIn):
    c=get_connection()
    if not c.execute("SELECT id FROM scenes WHERE id=?",(scene_id,)).fetchone():
        c.close(); raise HTTPException(404,"Scene not found")
    c.execute("UPDATE scenes SET name=?,data_json=?,updated_at=? WHERE id=?",(scene.name,json.dumps(scene.data),now_iso(),scene_id)); c.commit(); c.close(); return {"status":"updated"}
@app.delete("/api/scenes/{scene_id}")
def delete_scene(scene_id:int):
    c=get_connection(); c.execute("DELETE FROM scenes WHERE id=?",(scene_id,)); c.commit(); c.close(); return {"status":"deleted"}
@app.get("/health")
def health():
    return {"system":"UNG-CAD-3D","status":"ok","ui":"/studio.html","manufacturing":"/manufacturing.html","ad5m_bridge":"/ung-cad-ad5m-bridge.py"}
# Root-level UI assets must be registered AFTER API and health routes.
@app.get("/{asset_name}")
def ui_asset(asset_name: str):
    allowed_ext={".js",".css",".json",".py",".txt",".map",".wasm"}
    safe=Path(asset_name).name
    target=BASE_DIR/safe
    if target.is_file() and target.suffix.lower() in allowed_ext:
        return FileResponse(target)
    raise HTTPException(404,"Not Found")

app.mount("/static",StaticFiles(directory=BASE_DIR),name="static")
