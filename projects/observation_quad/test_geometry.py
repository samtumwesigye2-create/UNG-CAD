"""Geometry-contract checks for the compact observation quad concept."""
MAX_PART_MM=215
MOTOR_SPAN_MM=180
FC_PATTERN_MM=20
def test_print_envelope():
    assert MOTOR_SPAN_MM <= MAX_PART_MM
def test_fc_pattern():
    assert FC_PATTERN_MM == 20
