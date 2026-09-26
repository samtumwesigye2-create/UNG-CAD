"""Shared intelligence orchestration for CAD, Manufacturing, DRACO and LINK256."""
from dataclasses import dataclass
from typing import Any, Callable, Dict
from .evaluation_gate import EvaluationResult, require_pass

@dataclass
class TaskContract:
    application: str
    operation: str
    inputs: Dict[str, Any]

class IntelligenceFabric:
    def __init__(self):
        self.adapters: Dict[str, Callable] = {}

    def register(self, application: str, adapter: Callable) -> None:
        self.adapters[application.upper()] = adapter

    def execute(self, task: TaskContract, evaluation: EvaluationResult):
        require_pass(evaluation)
        key = task.application.upper()
        if key not in self.adapters:
            raise KeyError(f"no adapter registered for {task.application}")
        return self.adapters[key](task)
