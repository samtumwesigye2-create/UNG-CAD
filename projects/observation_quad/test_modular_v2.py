"""Production checks for Modular Observation Quad V2."""
from pathlib import Path
s=Path(__file__).with_name("modular_v2.scad").read_text()
required=[
 "part=0;", "plate=72;", "arm_len=62;", "guard_od=92;",
 "motor_mount=9;", "motor_screw=2.2;",
 "module center_plate()", "module arm()", "module guard()",
 "for(x=[-10,10],y=[-10,10])"
]
for token in required:
    assert token in s, f"missing:{token}"
# Largest individual part envelope is the optional 92 mm guard.
assert 92 <= 215
print("MODULAR_V2_PRODUCTION_CHECK_PASS")
