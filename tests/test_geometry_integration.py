from cad_core.geometry_adapter import CADGeometry
from ung_geometry import ArtifactState, Mesh, Vec3

def test_cad_and_geometry_mesh_contract():
    cad=CADGeometry()
    mesh=Mesh([Vec3(0,0,0),Vec3(1,0,0),Vec3(0,1,0)],[(0,1,2)])
    report=cad.validate_mesh(mesh)
    assert report["faces"]==1
    assert report["boundary_edges"]==3

def test_cad_and_geometry_unit_contract():
    assert CADGeometry().convert_length(1,"in","mm")==25.4

def test_cad_dependency_invalidation_contract():
    cad=CADGeometry()
    cad.track("model","brep","r1")
    cad.track("slice","slice","r1",["model"])
    cad.invalidate("model")
    assert cad.dependencies.items["slice"].state==ArtifactState.STALE

def test_machine_code_controller_contract():
    cad=CADGeometry()
    report=cad.validate_machine_code(["G0 X0","G1 X2","M6 T2"],"grbl")
    assert report.valid is False
    assert "M6" in report.unsupported
