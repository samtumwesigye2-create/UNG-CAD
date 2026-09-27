"""Closed-loop physical measurement and calibration feedback."""
from dataclasses import dataclass
from statistics import mean
from typing import Iterable,Dict
@dataclass(frozen=True)
class Measurement:
 feature_id:str;nominal_mm:float;measured_mm:float
 @property
 def error_mm(self):return self.measured_mm-self.nominal_mm
class CalibrationFeedbackEngine:
 def analyze(self,measurements:Iterable[Measurement],max_abs_error_mm:float=0.20)->Dict:
  ms=list(measurements)
  if not ms:raise ValueError("at least one measurement is required")
  if max_abs_error_mm<=0:raise ValueError("max_abs_error_mm must be positive")
  errors=[m.error_mm for m in ms];mae=mean(abs(e) for e in errors);bias=mean(errors);worst=max(abs(e) for e in errors)
  return {"count":len(ms),"mean_error_mm":bias,"mae_mm":mae,"worst_abs_error_mm":worst,"passed":worst<=max_abs_error_mm,"recommended_internal_delta_adjustment_mm":-bias,"features":[{"feature_id":m.feature_id,"nominal_mm":m.nominal_mm,"measured_mm":m.measured_mm,"error_mm":m.error_mm} for m in ms]}
 def update_internal_delta(self,current_delta_mm:float,report:Dict,max_step_mm:float=0.10)->float:
  if max_step_mm<=0:raise ValueError("max_step_mm must be positive")
  adj=float(report["recommended_internal_delta_adjustment_mm"]);adj=max(-max_step_mm,min(max_step_mm,adj))
  return current_delta_mm+adj
