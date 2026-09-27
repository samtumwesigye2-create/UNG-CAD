"""Reusable feature validation for solid compilation."""
SUPPORTED_FEATURES=frozenset({"slot","boss","standoff","counterbore","fillet","chamfer"})
def validate_features(features):
 for f in features or []:
  typ=f.get("type")
  if typ not in SUPPORTED_FEATURES:raise ValueError(f"unsupported solid feature: {typ}")
  if typ=="slot" and (float(f.get("length_mm",0))<=0 or float(f.get("width_mm",0))<=0):raise ValueError("slot requires positive length/width")
  if typ in {"boss","standoff"} and (float(f.get("diameter_mm",0))<=0 or float(f.get("height_mm",0))<=0):raise ValueError(f"{typ} requires positive diameter/height")
  if typ=="counterbore" and (float(f.get("diameter_mm",0))<=0 or float(f.get("depth_mm",0))<=0):raise ValueError("counterbore requires positive diameter/depth")
  if typ in {"fillet","chamfer"} and float(f.get("size_mm",0))<=0:raise ValueError(f"{typ} requires positive size")
 return True
