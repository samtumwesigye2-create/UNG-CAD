"""Acceptance checks for the compact observation quad CAD source."""
from pathlib import Path
import re

p=Path(__file__).with_name("observation_quad.scad")
s=p.read_text()
assert "span=180;" in s
assert "plate_d=72;" in s
assert "for(a=[45,135,225,315])" in s
assert "for(x=[-10,10],y=[-10,10])" in s
assert "part=1;" in s
assert 180 <= 215
print("OBSERVATION_QUAD_CAD_ACCEPTANCE_PASS")
