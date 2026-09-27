"""Async API for UNG-CAD Calculus-3 engineering analysis."""
import asyncio, os
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from cad_core.calculus3_engine import UNGCadCalculus3Engine

def _run(p):
    e=UNGCadCalculus3Engine(p["expr_x"],p["expr_y"],p["expr_z"])
    return e.surface_load_estimate((p["u_min"],p["u_max"]),(p["v_min"],p["v_max"]),p["density"],p["viscosity"],p["velocity_xyz"],p["characteristic_length"],p["resolution"])

@asynccontextmanager
async def lifespan(app:FastAPI):
    app.state.pool=ProcessPoolExecutor(max_workers=int(os.getenv("UNG_CALC_WORKERS",max(1,min(4,os.cpu_count() or 1)))))
    yield
    app.state.pool.shutdown(wait=True,cancel_futures=True)

app=FastAPI(title="UNG-CAD Calculus 3 Analysis API",version="3.1.0",lifespan=lifespan)

class AnalysisRequest(BaseModel):
    expr_x:str="u"; expr_y:str="v"; expr_z:str="sin(u)*cos(v)"
    u_min:float=-2.; u_max:float=2.; v_min:float=-2.; v_max:float=2.
    density:float=Field(1.225,gt=0); viscosity:float=Field(1.81e-5,gt=0)
    velocity_xyz:list[float]=Field(default_factory=lambda:[20.,0.,-3.],min_length=3,max_length=3)
    characteristic_length:float=Field(0.1,gt=0)
    resolution:int=Field(25,ge=5,le=150)
    @field_validator("u_max")
    @classmethod
    def u_order(cls,x,info):
        if "u_min" in info.data and x<=info.data["u_min"]: raise ValueError("u_max must exceed u_min")
        return x
    @field_validator("v_max")
    @classmethod
    def v_order(cls,x,info):
        if "v_min" in info.data and x<=info.data["v_min"]: raise ValueError("v_max must exceed v_min")
        return x

@app.post("/api/v3/calculate/manifold")
async def calculate_manifold(payload:AnalysisRequest):
    try:
        loop=asyncio.get_running_loop(); result=await loop.run_in_executor(app.state.pool,_run,payload.model_dump())
        result["status"]="SUCCESS"; result["assumptions"]=["preliminary surface-load estimate","not a CFD/Navier-Stokes solution","characteristic length supplied by caller"]
        return result
    except Exception as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
