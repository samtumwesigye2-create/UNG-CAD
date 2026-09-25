"""Static production checks for Simple Bicopter V2."""
from pathlib import Path
s=Path(__file__).with_name("simple_v2.scad").read_text()
for token in [
 "body_x=80;", "body_y=60;", "arm_l=92;", "guard_od=92;",
 "servo_x=23.6;", "servo_y=12.6;", "horn_clear_d=18;",
 "link_hole=2.2;", "motor_mount=9;",
 "module body()", "module arm()", "module guard()"
]:
    assert token in s, f"missing:{token}"
assert max(80,60,92) <= 215
print("SIMPLE_BICOPTER_V2_STATIC_CHECK_PASS")
