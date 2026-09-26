import math
from cad_core.arc_toolpath import ArcCircle,circle_length,filament_for_bead,full_circle_arc_gcode,segmented_circle_gcode

def test_true_arc_geometry():
    c=ArcCircle(110,110,20,.2,1.25)
    g=full_circle_arc_gcode(c)
    assert "G2 X130.000 Y110.000 I-20.000 J0.000" in g

def test_volumetric_extrusion():
    e=filament_for_bead(20,.2,.4)
    expected=(2*math.pi*20*.2*.4)/(math.pi*(1.75/2)**2)
    assert math.isclose(e,expected)

def test_g1_fallback():
    assert segmented_circle_gcode(ArcCircle(0,0,10,.2,1),32).count("G1 ")==32
