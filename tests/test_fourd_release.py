from cad_core.fourd_release import TimelineState,TimeState,evaluate_4d_release

def test_4d_release_requires_all_evidence():
    r=evaluate_4d_release(timeline=TimelineState(1,10),material_calibrated=True,
      stimulus_validated=True,toolpath_valid=True,machine_profile_valid=True)
    assert r.releasable

def test_uncalibrated_material_blocks_4d_release():
    r=evaluate_4d_release(timeline=TimelineState(1,10),material_calibrated=False,
      stimulus_validated=True,toolpath_valid=True,machine_profile_valid=True)
    assert not r.releasable
    assert any(c.name=="material-response" and c.state.value=="BLOCKED" for c in r.checks)

def test_invalid_time_blocks_release():
    r=evaluate_4d_release(timeline=TimelineState(11,10),material_calibrated=True,
      stimulus_validated=True,toolpath_valid=True,machine_profile_valid=True)
    assert not r.releasable
