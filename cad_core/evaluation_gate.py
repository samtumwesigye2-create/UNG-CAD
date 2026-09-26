"""Mandatory evaluation gate between model output and operational action."""
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass(frozen=True)
class EvaluationResult:
    passed: bool
    metrics: Dict[str, float] = field(default_factory=dict)
    failures: List[str] = field(default_factory=list)

def evaluate(metrics: Dict[str, float], requirements: Dict[str, tuple]) -> EvaluationResult:
    failures = []
    for name, (op, threshold) in requirements.items():
        if name not in metrics:
            failures.append(f"missing metric: {name}")
            continue
        value = metrics[name]
        ok = (value >= threshold) if op == ">=" else (value <= threshold) if op == "<=" else False
        if not ok:
            failures.append(f"{name} {value} violates {op} {threshold}")
    return EvaluationResult(not failures, dict(metrics), failures)

def require_pass(result: EvaluationResult) -> None:
    if not result.passed:
        raise RuntimeError("UNG evaluation gate blocked action: " + "; ".join(result.failures))
