"""Authorized evidence integrity primitives for the shared UNG data fabric.

This module does not acquire or bypass devices. It validates already-authorized
evidence, builds tamper-evident manifests, and provides conservative secret
redaction for downstream views.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class EvidenceRecord:
    case_id: str
    evidence_id: str
    source_id: str
    examiner_id: str
    acquired_at: str
    sha256: str
    size_bytes: int
    media_type: str = "application/octet-stream"
    parser_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_sha256(data: bytes, expected: str) -> bool:
    return sha256_bytes(data).lower() == expected.strip().lower()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def manifest_hash(records: Iterable[EvidenceRecord]) -> str:
    payload = [r.to_dict() for r in records]
    payload.sort(key=lambda x: (x["case_id"], x["evidence_id"], x["source_id"]))
    return sha256_bytes(canonical_json(payload))


@dataclass(frozen=True)
class AuditEvent:
    case_id: str
    evidence_id: str
    actor_id: str
    action: str
    timestamp: str
    details: Dict[str, Any]
    previous_hash: str = ""

    def event_hash(self) -> str:
        return sha256_bytes(canonical_json(asdict(self)))


class AuditChain:
    """Append-only in-memory chain suitable for persistence by the data fabric."""

    def __init__(self) -> None:
        self._events: List[AuditEvent] = []

    @property
    def events(self) -> List[AuditEvent]:
        return list(self._events)

    def append(self, case_id: str, evidence_id: str, actor_id: str,
               action: str, details: Optional[Dict[str, Any]] = None,
               timestamp: Optional[str] = None) -> AuditEvent:
        previous = self._events[-1].event_hash() if self._events else ""
        event = AuditEvent(
            case_id=case_id,
            evidence_id=evidence_id,
            actor_id=actor_id,
            action=action,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            details=dict(details or {}),
            previous_hash=previous,
        )
        self._events.append(event)
        return event

    def verify(self) -> bool:
        previous = ""
        for event in self._events:
            if event.previous_hash != previous:
                return False
            previous = event.event_hash()
        return True


_SECRET_PATTERNS = (
    # Context-bound OTP/verification codes; avoids redacting arbitrary short numbers.
    re.compile(r"(?i)\b((?:verification|security|account|login|one[- ]?time|otp)\s*(?:code)?\s*(?:is|:)?\s*)\d{4,8}\b"),
    re.compile(r"(?i)\b((?:password|passwd|token|api[_ -]?key|recovery[_ -]?code)\s*(?:is|:|=)\s*)\S+"),
)


def redact_sensitive_text(text: str, replacement: str = "[REDACTED]") -> str:
    result = text
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub(lambda m: m.group(1) + replacement, result)
    return result


def normalized_artifact(*, artifact_type: str, source_ref: str,
                        observed: Dict[str, Any], parser: str,
                        confidence: float = 1.0,
                        deleted: Optional[bool] = None) -> Dict[str, Any]:
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    out: Dict[str, Any] = {
        "artifact_type": artifact_type,
        "source_ref": source_ref,
        "observed": observed,
        "parser": parser,
        "confidence": confidence,
    }
    if deleted is not None:
        out["deleted"] = bool(deleted)
    return out
