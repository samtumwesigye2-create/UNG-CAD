"""UNG-CAD 4D/5D calculation engine. Standard library only.
Usage: python construction_engine.py project.json [--output result.json]
Input follows schemas/construction-project-v1.schema.json.
Estimates are indicative, not bids or engineering certifications.
"""
import argparse
import datetime as dt
import json
import math
from collections import defaultdict
from pathlib import Path

UNITS = {"m", "m2", "m3", "ft", "sf", "cf", "ea", "kg", "lb", "cy", "ton"}

def finite_nonnegative(v, name):
    if isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or v < 0:
        raise ValueError(f"{name}: expected nonnegative finite number")
    return float(v)

def analyze(project):
    if project.get("schema_version") != "1.0":
        raise ValueError("Unsupported schema_version")
    units = project["units"]
    if units["length"] not in ("m", "ft") or not isinstance(units["currency"], str) or len(units["currency"]) != 3:
        raise ValueError("Invalid project units")
    elements, tasks, rates = project["elements"], project["tasks"], project["rates"]
    ids = [e["id"] for e in elements]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate element ID")
    rate_map = {}
    for r in rates:
        key = (r["system"], r["unit"])
        if key in rate_map:
            raise ValueError(f"Duplicate rate: {key}")
        if r["unit"] not in UNITS:
            raise ValueError("Unknown rate unit")
        for field in ("material_rate", "labor_rate", "equipment_rate"):
            finite_nonnegative(r.get(field, 0), field)
        waste = finite_nonnegative(r.get("waste_fraction", 0), "waste_fraction")
        if waste > 1:
            raise ValueError("Waste fraction exceeds 1")
        rate_map[key] = r
    rows = []
    totals = defaultdict(float)
    for e in elements:
        key = (e["system"], e["unit"])
        if e["unit"] not in UNITS or key not in rate_map:
            raise ValueError(f"Missing rate for {key}")
        q = finite_nonnegative(e["quantity"], "quantity")
        r = rate_map[key]
        billable = q * (1 + r.get("waste_fraction", 0))
        material = billable * r["material_rate"]
        labor = q * r["labor_rate"]
        equipment = q * r.get("equipment_rate", 0)
        for label, value in (("material", material), ("labor", labor), ("equipment", equipment)):
            totals[label] += value
        rows.append({"element_id": e["id"], "system": e["system"], "quantity": q,
                     "unit": e["unit"], "billable_material_quantity": round(billable, 6),
                     "material": round(material, 2), "labor": round(labor, 2),
                     "equipment": round(equipment, 2), "total": round(material + labor + equipment, 2)})
    task_ids = [t["id"] for t in tasks]
    if len(set(task_ids)) != len(task_ids):
        raise ValueError("Duplicate task ID")
    by_id = {t["id"]: t for t in tasks}
    schedule = []
    for t in tasks:
        start, finish = dt.date.fromisoformat(t["start"]), dt.date.fromisoformat(t["finish"])
        if finish < start:
            raise ValueError(f"Task {t['id']} finishes before it starts")
        if any(e not in ids for e in t["element_ids"]):
            raise ValueError(f"Unknown element in task {t['id']}")
        for dep in t.get("dependencies", []):
            if dep not in by_id or dep == t["id"]:
                raise ValueError(f"Invalid dependency for {t['id']}")
            if dt.date.fromisoformat(by_id[dep]["finish"]) >= start:
                raise ValueError(f"Dependency overlap for {t['id']}")
        schedule.append({"task_id": t["id"], "start": t["start"], "finish": t["finish"],
                         "duration_days": (finish - start).days + 1, "element_ids": t["element_ids"]})
    visited, active = set(), set()
    def visit(task_id):
        if task_id in active:
            raise ValueError("Cyclic task dependencies")
        if task_id in visited:
            return
        active.add(task_id)
        for dep in by_id[task_id].get("dependencies", []):
            visit(dep)
        active.remove(task_id)
        visited.add(task_id)
    for task_id in by_id:
        visit(task_id)
    return {"project_id": project["project_id"], "currency": units["currency"],
            "costs": {**{k: round(totals[k], 2) for k in ("material", "labor", "equipment")},
                      "total": round(sum(totals.values()), 2)},
            "takeoff": rows, "schedule": sorted(schedule, key=lambda x: (x["start"], x["task_id"])),
            "warnings": ["Input quantities and rates are user-supplied; no geometry extraction, building-code verification or structural certification performed."]}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = analyze(json.loads(Path(args.project).read_text(encoding="utf-8")))
    output = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

if __name__ == "__main__":
    main()
