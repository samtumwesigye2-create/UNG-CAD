"""Manufacturing machine/tool capability contracts."""
from dataclasses import dataclass
@dataclass(frozen=True)
class MachineProfile:
 machine_id:str;process:str;work_x_mm:float;work_y_mm:float;work_z_mm:float;materials:frozenset[str]
 def validate_part(self,x,y,z,material):
  if min(x,y,z)<=0:raise ValueError("part dimensions must be positive")
  if x>self.work_x_mm or y>self.work_y_mm or z>self.work_z_mm:raise ValueError(f"part exceeds {self.machine_id} work envelope")
  if material not in self.materials:raise ValueError(f"{material} is not configured for {self.machine_id}")
  return True
MACHINES={
 "flashforge_ad5m":MachineProfile("flashforge_ad5m","fdm",220,220,220,frozenset({"pla","petg"})),
}
@dataclass(frozen=True)
class ToolProfile:
 tool_id:str;diameter_mm:float;process:str
 def __post_init__(self):
  if self.diameter_mm<=0:raise ValueError("tool diameter must be positive")
