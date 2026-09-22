"""Conservative machine compatibility and routing helpers."""
def compatible(machine,job_kind):
    return machine.get("kind")==job_kind and machine.get("state","offline") in ("idle","ready")
def rank(machines,job_kind):
    eligible=[m for m in machines if compatible(m,job_kind)]
    return sorted(eligible,key=lambda m:(m.get("queue_depth",0),m.get("name","")))
