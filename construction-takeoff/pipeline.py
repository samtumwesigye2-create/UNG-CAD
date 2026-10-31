"""UNG-CAD construction pipeline: IFC/OBJ geometry, takeoff, phases, gates, exports.
Optional dependency for IFC: pip install ifcopenshell
No deployment or external connections. This is a local, conservative pipeline.
"""
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

IFC_SYSTEMS = {
    "IfcSlab": "concrete", "IfcFooting": "concrete", "IfcWall": "envelope",
    "IfcWallStandardCase": "envelope", "IfcBeam": "structural_steel",
    "IfcColumn": "structural_steel", "IfcRoof": "roof",
    "IfcDoor": "doors", "IfcWindow": "windows", "IfcPipeSegment": "plumbing",
    "IfcDuctSegment": "hvac",
}
PHASES = {"concrete": 2, "structural_steel": 3, "envelope": 4, "roof": 5,
          "doors": 6, "windows": 6, "plumbing": 7, "hvac": 7}
UNIT_TO_QTO = {"m3": "NetVolume", "m2": "NetArea", "m": "Length"}
def _positive(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x > 0

def load_ifc(path):
    """Read explicit IFC BaseQuantities. Do not invent quantities from bounding boxes."""
    try:
        import ifcopenshell
        import ifcopenshell.util.element
    except ImportError as e:
        raise RuntimeError("IFC import requires optional package: pip install ifcopenshell") from e
    file = ifcopenshell.open(str(path))
    units = file.by_type("IfcUnitAssignment")
    # IFC project units must be SI for this conservative reader.
    if not units:
        raise ValueError("IFC unit assignment missing")
    assignment = units[0]
    for unit in assignment.Units:
        if unit.is_a("IfcSIUnit") and unit.UnitType in ("LENGTHUNIT","AREAUNIT","VOLUMEUNIT"):
            if unit.Prefix not in (None,):
                raise ValueError("Non-base SI units require explicit conversion")
        if unit.UnitType in ("LENGTHUNIT","AREAUNIT","VOLUMEUNIT") and not unit.is_a("IfcSIUnit"):
            raise ValueError("Non-SI IFC units require explicit conversion")
    elements, warnings = [], []
    for ifc_type, system in IFC_SYSTEMS.items():
        for item in file.by_type(ifc_type):
            if item.is_a() != ifc_type:
                continue
            quantities = ifcopenshell.util.element.get_psets(item, qtos_only=True)
            flat = {}
            for qto in quantities.values():
                if isinstance(qto, dict):
                    flat.update(qto)
            choices = (("NetVolume","m3"),("NetArea","m2"),("Length","m"))
            found = next(((flat[k],u) for k,u in choices if _positive(flat.get(k))),None)
            if not found:
                warnings.append(f"{item.GlobalId}: missing supported measured quantity")
                continue
            qty, unit = found
            elements.append({"id": item.GlobalId,"system":system,"quantity":qty,
                             "unit":unit,"waste_fraction":0,"phase":PHASES.get(system,8),
                             "source":"IFC BaseQuantities"})
    project = file.by_type("IfcProject")
    return {"schema_version":1,"model_id":project[0].GlobalId if project else Path(path).stem,
            "revision":"IFC-import","components":elements,"warnings":warnings}

def obj_preview(path):
    """Parse OBJ vertices and faces into a non-authoritative preview manifest."""
    vertices, faces = [], []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        parts=line.strip().split()
        if not parts: continue
        if parts[0]=="v" and len(parts)>=4:
            vertex=tuple(float(n) for n in parts[1:4])
            if not all(math.isfinite(n) for n in vertex): raise ValueError("Invalid OBJ vertex")
            vertices.append(vertex)
        elif parts[0]=="f" and len(parts)>=4:
            face=[]
            for token in parts[1:]:
                index=int(token.split("/")[0])
                if index == 0: raise ValueError("Invalid OBJ face index")
                resolved=index-1 if index>0 else len(vertices)+index
                if not 0<=resolved<len(vertices): raise ValueError("OBJ face index out of range")
                face.append(resolved)
            faces.append(face)
    return {"format":"OBJ","vertices":vertices,"faces":faces,
            "warning":"Preview only. OBJ units and material assemblies unknown; not valid for takeoff."}

def build(model, catalog, *, gatekeeper=None):
    """No approval unless an external, authenticated gatekeeper has actually approved."""
    issues=list(model.get("warnings",[]))
    if model.get("schema_version") != 1 or not model.get("model_id") or not model.get("revision"):
        issues.append("Model schema, ID or revision invalid")
    if not isinstance(catalog,dict) or not catalog.get("currency")=="USD":
        issues.append("Price catalog must specify USD")
    if not catalog.get("effective_date") or not catalog.get("location"):
        issues.append("Catalog date and location required")
    components=model.get("components",[])
    if not isinstance(components,list) or not components: issues.append("No measured components")
    rows, ids = [], set()
    for c in components if isinstance(components,list) else []:
        if not isinstance(c,dict):
            issues.append("Malformed component");continue
        cid=c.get("id")
        if not isinstance(cid,str) or not cid or cid in ids:
            issues.append("Missing or duplicate component ID");continue
        ids.add(cid)
        system,unit=c.get("system"),c.get("unit")
        qty,waste=c.get("quantity"),c.get("waste_fraction",0)
        phase=c.get("phase",PHASES.get(system,8))
        rate=catalog.get("rates",{}).get(system,{}).get(unit)
        labor=catalog.get("labor",{}).get(system,{}).get(unit,0)
        if unit not in ("m","m2","m3","kg","count") or not _positive(qty):
            issues.append(f"{cid}: invalid measurement");continue
        if not isinstance(waste,(int,float)) or isinstance(waste,bool) or not math.isfinite(waste) or not 0<=waste<=0.5:
            issues.append(f"{cid}: invalid waste");continue
        if not isinstance(phase,int) or isinstance(phase,bool) or not 1<=phase<=20:
            issues.append(f"{cid}: invalid phase");continue
        if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<0 for v in (rate,labor)):
            issues.append(f"{cid}: missing or invalid material/labor rate");continue
        amount=qty*(1+waste)*rate+qty*labor
        rows.append({"id":cid,"system":system,"unit":unit,"quantity":qty,
                     "waste_fraction":waste,"phase":phase,"material_rate_usd":rate,
                     "labor_rate_usd":labor,"amount_usd":round(amount,2),
                     "source":c.get("source","user-supplied")})
    if not rows: issues.append("No priced measured components")
    # Never treat caller-provided boolean or forged JSON as a real Gatekeeper decision.
    gate_status="NOT_CONNECTED"
    if gatekeeper is not None:
        gate_status="REQUIRES_EXTERNAL_VERIFICATION"
        issues.append("External Manufacturing Gatekeeper signature not verified")
    totals=defaultdict(float)
    for r in rows: totals[r["system"]]+=r["amount_usd"]
    result={"schema_version":1,"model_id":model.get("model_id"),
            "revision":model.get("revision"),"generated_at":datetime.now(timezone.utc).isoformat(),
            "currency":"USD","catalog_date":catalog.get("effective_date"),
            "catalog_location":catalog.get("location"),"status":"BLOCKED" if issues else "ESTIMATE_ONLY",
            "gatekeeper_status":gate_status,"gatekeeper_approved":False,
            "issues":issues,"lines":rows if not issues else [],
            "system_totals_usd":{k:round(v,2) for k,v in totals.items()} if not issues else {},
            "total_usd":round(sum(totals.values()),2) if not issues else None,
            "phases":[{"phase":n,"components":[r["id"] for r in rows if r["phase"]==n]}
                      for n in sorted({r["phase"] for r in rows})] if not issues else [],
            "integration_targets":["UNG-TITAN","UNG-APOLLO","UNG-MERCURY"],
            "integration_state":"export_only_not_connected"}
    return result

def export(result, destination):
    directory=Path(destination);directory.mkdir(parents=True,exist_ok=True)
    (directory/"estimate.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    if result["status"]=="BLOCKED": return
    columns=["id","system","unit","quantity","waste_fraction","phase","material_rate_usd",
             "labor_rate_usd","amount_usd","source"]
    with (directory/"takeoff.csv").open("w",newline="",encoding="utf-8") as file:
        writer=csv.DictWriter(file,fieldnames=columns);writer.writeheader();writer.writerows(result["lines"])
    for target in ("TITAN","APOLLO","MERCURY"):
        (directory/(target.lower()+"-handoff.json")).write_text(json.dumps({
            "target":target,"mode":"REVIEW_ONLY","model_id":result["model_id"],
            "revision":result["revision"],"estimate_total_usd":result["total_usd"],
            "phases":result["phases"],"lines":result["lines"]},indent=2),encoding="utf-8")

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("model",help="Measured model JSON or IFC file")
    parser.add_argument("catalog",help="Versioned local price catalog JSON")
    parser.add_argument("--out",default="construction-output")
    args=parser.parse_args()
    model=load_ifc(args.model) if args.model.lower().endswith(".ifc") else json.loads(Path(args.model).read_text())
    result=build(model,json.loads(Path(args.catalog).read_text()))
    export(result,args.out)
    print(json.dumps({"status":result["status"],"issues":result["issues"],
                      "total_usd":result["total_usd"],"output":args.out},indent=2))
    if result["status"]=="BLOCKED": raise SystemExit(2)
if __name__=="__main__":main()
