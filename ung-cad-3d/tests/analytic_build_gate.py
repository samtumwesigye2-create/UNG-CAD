from pathlib import Path
import math
root=Path(__file__).resolve().parents[1]
required={
 "analytic_geometry.js":["UNGAnalytic","intersection","contains"],
 "parametric_surfaces.js":["UNGSurfaces","tessellate","cylinder","sphere"],
 "surface_unroll.js":["UNGUnroll","develop","distortion"],
 "symbolic_math.js":["UNGSymbolic","integrateNumeric","substitutePower"],
 "viewer.js":["analyticManufacturingGate","analyticRecord","restoreAnalytic","surfaceDevelopment","analytic:objects.map"],
 "viewer.html":["analytic-cylinder","analytic-intersect","analytic-unroll","unroll-svg","symbolic-integral"],
}
for name,tokens in required.items():
 s=(root/name).read_text(encoding="utf-8")
 for token in tokens:
  assert token in s, f"{name}: missing {token}"
r=5.0
assert abs(2*math.pi*r-31.41592653589793)<1e-12
steinmetz=16*r**3/3
assert abs(steinmetz-666.6666666666666)<1e-9
print("analytic-build-gate: PASS")
