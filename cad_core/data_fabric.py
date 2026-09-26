"""Shared UNG data contract and lightweight ingestion/validation layer."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

@dataclass(frozen=True)
class DataRecord:
    source: str
    payload: Dict[str, Any]
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    provenance: Optional[str] = None

def normalize_record(source: str, payload: Dict[str, Any], *, metadata=None, provenance=None, timestamp=None) -> DataRecord:
    if not source or not isinstance(payload, dict):
        raise ValueError("source and dictionary payload are required")
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    return DataRecord(source.strip(), dict(payload), ts, dict(metadata or {}), provenance)

def validate_records(records: Iterable[DataRecord]) -> List[DataRecord]:
    out = []
    for r in records:
        if not r.source or not r.timestamp or not isinstance(r.payload, dict):
            raise ValueError("invalid UNG data record")
        out.append(r)
    return out
