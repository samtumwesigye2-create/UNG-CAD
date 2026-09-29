from cad_core.manufacturability import analyze_fdm_printability


def test_cube_has_bed_contact_and_downward_faces():
    v000=(0,0,0);v100=(10,0,0);v110=(10,10,0);v010=(0,10,0)
    v001=(0,0,10);v101=(10,0,10);v111=(10,10,10);v011=(0,10,10)
    tris=[
      (v000,v110,v100),(v000,v010,v110),
      (v001,v101,v111),(v001,v111,v011),
      (v000,v100,v101),(v000,v101,v001),
      (v100,v110,v111),(v100,v111,v101),
      (v110,v010,v011),(v110,v011,v111),
      (v010,v000,v001),(v010,v001,v011),
    ]
    r=analyze_fdm_printability(tris)
    assert r.bed_contact_face_count == 2
    assert r.bridge_candidate_face_count == 0
    assert r.max_height_mm == 10


def test_suspended_horizontal_underside_is_bridge_candidate():
    tris=[((0,0,5),(10,10,5),(10,0,5))]
    r=analyze_fdm_printability(tris,bed_z_mm=0)
    assert r.bridge_candidate_face_count == 1
    assert r.overhang_face_count == 1


def test_vertical_wall_is_not_overhang():
    tris=[((0,0,0),(0,10,0),(0,10,10))]
    r=analyze_fdm_printability(tris,bed_z_mm=0)
    assert r.overhang_face_count == 0


def test_minimum_feature_proxy_warns_on_short_edges():
    tris=[((0,0,0),(0.1,0,0),(0,1,0))]
    r=analyze_fdm_printability(tris,minimum_feature_mm=.4)
    assert r.min_mesh_edge_mm < .4
    assert r.tiny_mesh_edges > 0
    assert r.warnings
