from cad_core.evidence_integrity import (
    AuditChain, EvidenceRecord, manifest_hash, redact_sensitive_text,
    sha256_bytes, verify_sha256, normalized_artifact,
)


def test_hash_round_trip():
    data = b"authorized evidence"
    digest = sha256_bytes(data)
    assert verify_sha256(data, digest)
    assert not verify_sha256(data + b"x", digest)


def test_manifest_is_deterministic():
    a = EvidenceRecord("C1", "E2", "S2", "U1", "2026-01-01T00:00:00Z", "b"*64, 2)
    b = EvidenceRecord("C1", "E1", "S1", "U1", "2026-01-01T00:00:00Z", "a"*64, 1)
    assert manifest_hash([a, b]) == manifest_hash([b, a])


def test_audit_chain_links_events():
    chain = AuditChain()
    chain.append("C1", "E1", "U1", "import", {"ok": True}, "2026-01-01T00:00:00Z")
    chain.append("C1", "E1", "U1", "review", {}, "2026-01-01T00:01:00Z")
    assert chain.verify()
    assert chain.events[1].previous_hash == chain.events[0].event_hash()


def test_context_bound_secret_redaction():
    s = "Your Apple Account verification code is 299040. Order 123456 remains visible."
    out = redact_sensitive_text(s)
    assert "299040" not in out
    assert "Order 123456" in out


def test_artifact_provenance_and_deleted_flag():
    a = normalized_artifact(
        artifact_type="message", source_ref="db:42",
        observed={"body": "hello"}, parser="sms-v1",
        confidence=0.9, deleted=True,
    )
    assert a["source_ref"] == "db:42"
    assert a["deleted"] is True
