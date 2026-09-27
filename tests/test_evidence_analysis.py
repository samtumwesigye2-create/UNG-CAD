from cad_core.evidence_analysis import build_search_index,search,relationship_graph,media_record
from cad_core.evidence_access import Principal,protected_view,integration_event
from cad_core.evidence_reporting import build_report,verify_report

A=[{"source_ref":"sms:1","observed":{"contact":"alice@example.com","body":"meeting"}},
   {"source_ref":"call:2","observed":{"contact":"alice@example.com"}}]

def test_search_and_graph():
    idx=build_search_index(A)
    assert search(idx,"alice@example.com")==["call:2","sms:1"]
    assert relationship_graph(A)["edges"]

def test_media_hash():
    assert len(media_record(b"x")["sha256"])==64

def test_sensitive_default_redaction():
    p=Principal("u",frozenset({"reviewer"}))
    assert "299040" not in protected_view("verification code is 299040",p)

def test_integration_event_allowlist():
    assert integration_event("timeline.updated","c","e")["event_type"]=="timeline.updated"

def test_report_integrity():
    r=build_report("c",[{"sha256":"a"}],[{"finding":"observed"}],["parser unavailable"],{"core":"1"})
    assert verify_report(r)
    r["case_id"]="changed"
    assert not verify_report(r)
