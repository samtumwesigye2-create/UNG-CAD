import io

from fastapi.testclient import TestClient
import main

client=TestClient(main.app)

TETRA_STL=b"""solid tetra
facet normal 0 0 -1
 outer loop
  vertex 0 0 0
  vertex 10 0 0
  vertex 0 10 0
 endloop
endfacet
facet normal 0 -1 0
 outer loop
  vertex 0 0 0
  vertex 0 0 10
  vertex 10 0 0
 endloop
endfacet
facet normal -1 0 0
 outer loop
  vertex 0 0 0
  vertex 0 10 0
  vertex 0 0 10
 endloop
endfacet
facet normal 1 1 1
 outer loop
  vertex 10 0 0
  vertex 0 0 10
  vertex 0 10 0
 endloop
endfacet
endsolid tetra
"""

def test_standalone_stl_slices_without_production_manifest(monkeypatch):
    monkeypatch.setattr(main,"slice_stl",lambda data,name,layer_height:(
        b"; generated test gcode\n",
        {"layers":1,"infill_percent":15,"wall_count":2,"support_layers":0,"material_g":1.0,"estimated_minutes":1,"validation":"PASS"},
    ))
    monkeypatch.setattr(main,"sign_machine_file",lambda path,release:{
        "machine_file_sha256":"test",
        "project":release["project"],
        "revision":release["revision"],
    })
    response=client.post(
        "/api/manufacturing/slice",
        files={"file":("motor-cover.stl",TETRA_STL,"model/stl")},
        data={"selected":"motor-cover.stl","material":"PETG"},
    )
    assert response.status_code==200, response.text
    body=response.json()
    assert body["status"]=="sliced"
    assert body["production_release"]["gate_scope"]=="standalone"
    assert body["production_release"]["production_release_allowed"] is True
