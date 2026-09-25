"""UNG-CAD facade for UNG-GEOMETRY."""
from ung_geometry import (
    Artifact, CheckResult, CheckStatus, DependencyGraph, GeometryIntegrityReport,
    LengthUnit, Mesh, convert_length, validate_gcode,
)

class CADGeometry:
    def __init__(self):
        self.dependencies=DependencyGraph()

    def validate_mesh(self, mesh:Mesh)->dict:
        return mesh.validate()

    def integrity_report(self, mesh:Mesh)->GeometryIntegrityReport:
        result=mesh.validate()
        return GeometryIntegrityReport([
            CheckResult("degenerate_faces",
                        CheckStatus.VALID if result["degenerate_faces"]==0 else CheckStatus.INVALID,
                        str(result["degenerate_faces"])),
            CheckResult("nonmanifold_edges",
                        CheckStatus.VALID if result["nonmanifold_edges"]==0 else CheckStatus.INVALID,
                        str(result["nonmanifold_edges"])),
            CheckResult("watertight",
                        CheckStatus.VALID if result["watertight"] else CheckStatus.WARNING,
                        str(result["watertight"])),
        ])

    def convert_length(self,value:float,src:str,dst:str)->float:
        return convert_length(value,LengthUnit(src),LengthUnit(dst))

    def track(self,artifact_id:str,kind:str,revision:str,dependencies=None):
        a=Artifact(artifact_id,kind,revision,list(dependencies or []))
        self.dependencies.add(a)
        return a

    def invalidate(self,artifact_id:str):
        return self.dependencies.invalidate_downstream(artifact_id)

    def validate_machine_code(self,lines,controller:str):
        return validate_gcode(lines,controller)
