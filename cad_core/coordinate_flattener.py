"""Flatten recursive panel assemblies into global manufacturing coordinates."""
import copy,math
from typing import List,Dict,Any,Tuple

class CoordinateFlattener:
 @staticmethod
 def _apply_transform_matrix(x:float,y:float,tx:float,ty:float,angle_deg:float)->Tuple[float,float]:
  a=math.radians(angle_deg);c=math.cos(a);s=math.sin(a)
  return tx+x*c-y*s,ty+x*s+y*c

 @classmethod
 def flatten_assembly(cls,node:Dict[str,Any],accumulated_x:float=0.0,accumulated_y:float=0.0,accumulated_rot:float=0.0)->List[Dict[str,Any]]:
  # Include this node's own local transform. Root position therefore works too,
  # rather than being silently ignored.
  pos=node.get("position",{"x":0.0,"y":0.0})
  nx,ny=cls._apply_transform_matrix(float(pos.get("x",0)),float(pos.get("y",0)),accumulated_x,accumulated_y,accumulated_rot)
  nrot=(accumulated_rot+float(node.get("rotation",0)))%360.0
  out=[]
  for cutout in node.get("cutouts",[]):
   g=copy.deepcopy(cutout);lp=cutout["position"]
   gx,gy=cls._apply_transform_matrix(float(lp["x_mm"]),float(lp["y_mm"]),nx,ny,nrot)
   local_rot=float(cutout.get("rotation",0));g["position"]={"x_mm":gx,"y_mm":gy};g["rotation"]=(local_rot+nrot)%360.0
   # Keep mounting holes as offsets in the cutout-local frame. DXF/browser
   # compilers already rotate these offsets by the cutout's final rotation;
   # pre-rotating here would double-rotate them.
   out.append(g)
  for child in node.get("child_panels",[]):
   out.extend(cls.flatten_assembly(child,nx,ny,nrot))
  return out
