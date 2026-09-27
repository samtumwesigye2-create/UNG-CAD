from cad_core.evidence_timeline import TimelineEvent, build_timeline, correlate, reconstruct_threads

def ev(ts,ref,**obs):
    return TimelineEvent(ts,"message",ref,obs)

def test_timeline_order():
    x=[ev("2026-01-01T00:01:00Z","b"),ev("2026-01-01T00:00:00Z","a")]
    assert [e.source_ref for e in build_timeline(x)]==["a","b"]

def test_correlation_shared_identifier_and_time():
    x=[ev("2026-01-01T00:00:00Z","sms:1",contact="+15551234567"),
       ev("2026-01-01T00:00:30Z","call:2",phone="+15551234567")]
    r=correlate(x,threshold=.2)
    assert len(r)==1
    assert "shared-identifiers" in r[0]["reasons"]
    assert "temporal-proximity" in r[0]["reasons"]

def test_thread_reconstruction():
    x=[ev("2026-01-01T00:01:00Z","2",thread_id="t1"),
       ev("2026-01-01T00:00:00Z","1",thread_id="t1")]
    assert [e.source_ref for e in reconstruct_threads(x)["t1"]]==["1","2"]
