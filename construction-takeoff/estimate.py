"""UNG-CAD construction quantity extraction and gatekeeper preflight.
Input: explicit measured model components, not guessed geometry.
Run: python3 construction-takeoff/estimate.py model.json
"""
import json
import math
import sys
from pathlib import Path

ALLOWED_UNITS = {"m3", "m2", "m", "count", "kg"}
def estimate(model, rates):
    errors, lines = [], []
    if model.get("schema_version") != 1:
        errors.append("Unsupported model schema_version")
    if not model.get("model_id") or not model.get("revision"):
        errors.append("Model identity and revision required")
    components = model.get("components", [])
    if not isinstance(components, list) or not components:
        errors.append("At least one measured component required")
        components = []
    seen = set()
    for i, c in enumerate(components):
        if not isinstance(c, dict):
            errors.append(f"Component {i} must be an object")
            continue
        cid = c.get("id")
        if not isinstance(cid, str) or not cid or cid in seen:
            errors.append(f"Component {i} has missing or duplicate id")
            continue
        seen.add(cid)
        system, unit = c.get("system"), c.get("unit")
        qty, waste = c.get("quantity"), c.get("waste_fraction", 0)
        if unit not in ALLOWED_UNITS:
            errors.append(f"{cid}: unsupported unit")
            continue
        if not isinstance(qty, (int,float)) or isinstance(qty,bool) or not math.isfinite(qty) or qty <= 0:
            errors.append(f"{cid}: quantity must be positive finite number")
            continue
        if not isinstance(waste,(int,float)) or isinstance(waste,bool) or not math.isfinite(waste) or not 0 <= waste <= 0.5:
            errors.append(f"{cid}: waste_fraction must be between 0 and 0.5")
            continue
        rate = rates.get(system, {}).get(unit) if isinstance(rates.get(system), dict) else None
        if not isinstance(rate,(int,float)) or isinstance(rate,bool) or not math.isfinite(rate) or rate < 0:
            errors.append(f"{cid}: missing or invalid price rate for {system}/{unit}")
            continue
        billable = qty*(1+waste)
        lines.append({"component_id":cid,"system":system,"quantity":qty,"unit":unit,
                      "waste_fraction":waste,"billable_quantity":round(billable,4),
                      "unit_rate_usd":rate,"amount_usd":round(billable*rate,2)})
    # Never issue an approved estimate if any measurement, pricing, or identity is invalid.
    return {"status":"BLOCKED" if errors else "ESTIMATE_ONLY",
            "gatekeeper_approved":False,"model_id":model.get("model_id"),
            "revision":model.get("revision"),"errors":errors,
            "lines":lines if not errors else [],
            "total_usd":round(sum(x["amount_usd"] for x in lines),2) if not errors else None,
            "limitations":["Requires geometry provenance and dimensional verification",
                           "No structural, code, fabrication, or safety approval",
                           "Prices must be verified for location and date"]}

def main():
    if len(sys.argv)!=3:
        raise SystemExit("Usage: estimate.py model.json rates.json")
    model=json.loads(Path(sys.argv[1]).read_text())
    rates=json.loads(Path(sys.argv[2]).read_text())
    result=estimate(model,rates)
    print(json.dumps(result,indent=2))
    if result["status"]=="BLOCKED":
        raise SystemExit(2)

if __name__=="__main__":
    main()
