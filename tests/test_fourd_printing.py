from cad_core.fourd_printing import FourDPrintEngine,FourDProfile,compile_4d_gcode

def test_4d_engine_modulates_speed_and_material():
    src="G1 X0 Y0 Z0.2 E1 F1200\nG1 X10 Y6 Z0.5 E2\n"
    r=compile_4d_gcode(src,FourDProfile(light_interval_mm=.5))
    assert "4D PROCESS SPEED" in r.gcode
    assert "T1 ; 4D MATERIAL REGION" in r.gcode
    assert "G4 P5000 ; 4D LIGHT EXPOSURE EVENT" in r.gcode
    assert r.modified_moves==2 and r.tool_changes==1 and r.light_dwells==1
    assert r.experimental is True

def test_4d_engine_clamps_programmed_speed():
    p=FourDProfile(base_speed_mm_min=10000,max_speed_boost_mm_min=10000,max_speed_mm_min=11000)
    r=FourDPrintEngine(p).compile("G1 X1 Y1 Z0.2 E1\n")
    assert "F11000" in r.gcode

def test_4d_engine_preserves_non_motion_commands():
    r=compile_4d_gcode("M104 S210 ; nozzle\nM82\n")
    assert "M104 S210 ; nozzle" in r.gcode
    assert "M82" in r.gcode
