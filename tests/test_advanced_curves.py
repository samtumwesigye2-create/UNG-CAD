import math
from cad_core.advanced_curves import *

def test_spiral_length_is_3d_helix_length():
    assert math.isclose(spiral_length_per_turn(25,.2),math.hypot(50*math.pi,.2))

def test_spiral_fallback_has_continuous_z():
    g=spiral_circle_gcode(SpiralCircle(110,110,25,.2,.4,.2,1),segments_per_turn=16)
    assert g.count("G1 ")==32 and " Z0.400 " in g and " Z0.600 " in g

def test_helical_arc_requires_explicit_capability():
    s=SpiralCircle(0,0,10,.2,.4,.2,1)
    assert "G2 " not in spiral_circle_gcode(s,helical_arcs_supported=False,segments_per_turn=16)
    assert spiral_circle_gcode(s,helical_arcs_supported=True).count("G2 ")==2

def test_ellipse_closes_and_distributes_extrusion():
    g=ellipse_gcode(Ellipse(110,110,35,15,.2,2),64)
    assert g.count("G1 ")==64
    assert "X145.000 Y110.000" in g.splitlines()[-1]
