"""UNG-CAD geometry/manufacturing API. Real pipeline; no mock geometry or DXF artifacts."""
from pathlib import Path
from typing import Any
from uuid import UUID,uuid4
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from cad_core.layout_boundary import LayoutBoundaryEvaluator
from cad_core.process_compensation import apply_manufacturing_compensation
from cad_core.material_cost import MaterialCostEstimator
from cad_core.dxf_exporter import UngCadDxfExporter
from cad_core.dxf_dimensioner import UngCadAutoDimensioner

app=FastAPI(title="UNG-CAD Geometry Computation Engine",description="Parametric layout validation, manufacturing metrics, and blueprint compilation.",version="1.4.0")
OUTPUT_DIR=Path("/tmp/ung_cad_builds");OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
_sessions:dict[str,dict[str,Any]]={}

class Position2D(BaseModel): x_mm:float;y_mm:float
class CutoutRequest(BaseModel):
 component_id:str;type:str;position:Position2D;rotation:float=0;clearance_mm:float=Field(default=0,ge=0);depth_mm:float=-1;tolerance_profile:str
 geometry_payload:dict[str,Any]|None=None;dimensions:dict[str,Any]|None=None;mounting_holes:list[dict[str,Any]]=Field(default_factory=list)
class PanelAssemblyPayload(BaseModel):
 panel_id:str;width_mm:float=Field(gt=0);height_mm:float=Field(gt=0);material_key:str="aluminum_6061";thickness_mm:float=Field(default=3.2,gt=0)
 cutouts:list[CutoutRequest]=Field(default_factory=list)

@app.post("/api/v1/process-assembly")
async def process_assembly(payload:PanelAssemblyPayload):
 try:
  flat=[c.model_dump(exclude_none=True) for c in payload.cutouts]
  valid,errors=LayoutBoundaryEvaluator(payload.width_mm,payload.height_mm).verify_layout(flat)
  if not valid: raise HTTPException(status_code=422,detail={"message":"Geometric layout constraints breached.","errors":errors})
  compensated=[apply_manufacturing_compensation(c) for c in flat]
  bom=MaterialCostEstimator(payload.material_key,payload.thickness_mm).generate_bill_of_materials(compensated,payload.width_mm,payload.height_mm)
  token=str(uuid4());_sessions[token]={"cutouts":compensated,"width":payload.width_mm,"height":payload.height_mm}
  return {"status":"Success","session_token":token,"features_processed_count":len(compensated),"bill_of_materials":bom}
 except HTTPException: raise
 except (ValueError,KeyError,TypeError) as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc

@app.get("/api/v1/download/dxf/{session_token}")
async def download_dxf_file(session_token:str):
 try: UUID(session_token)
 except ValueError: raise HTTPException(status_code=400,detail="invalid session token")
 state=_sessions.get(session_token)
 if not state: raise HTTPException(status_code=404,detail="build session not found")
 path=OUTPUT_DIR/f"panel_blueprint_{session_token}.dxf"
 try:
  UngCadDxfExporter.export_to_dxf(str(path),state["cutouts"],state["width"],state["height"])
  UngCadAutoDimensioner.append_datum_dimensions(str(path),state["cutouts"])
 except (ValueError,RuntimeError,KeyError) as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
 return FileResponse(str(path),filename="manufacturing_blueprint.dxf",media_type="application/dxf")
