from slicer import _emit_prime_sequence

def test_prime_sequence_extrudes_before_layer_one():
    lines = []
    _emit_prime_sequence(lines)
    assert "G1 X80 Y10 E8.0000 F600" in lines
    assert "G1 X10 Y10.4 E9.0000 F600" in lines
    assert lines.count("G92 E0") == 2
    assert lines[-1] == "G1 Z0.20 F600"
