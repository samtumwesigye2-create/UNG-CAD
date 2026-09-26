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


def test_nonplanar_curvature_and_accel_gate():
    n=NonplanarOval(110,110,40,20,.2,.4,.2,0,3,.04)
    g=nonplanar_oval_gcode(n,segments_per_turn=32,dynamic_accel_supported=False)
    assert "M204" not in g
    g2=nonplanar_oval_gcode(n,segments_per_turn=32,dynamic_accel_supported=True)
    assert "M204 P" in g2

def test_nonplanar_rejects_downward_z_by_default():
    n=NonplanarOval(0,0,20,10,.2,2,.2,2.5,3,.04)
    try:
        nonplanar_oval_gcode(n,segments_per_turn=64)
    except ValueError as e:
        assert "downward Z" in str(e)
    else:
        raise AssertionError("expected downward-Z safety rejection")
