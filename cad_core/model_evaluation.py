"""Model validation utilities feeding the mandatory operational evaluation gate."""
from dataclasses import dataclass
from typing import Dict, Sequence
from .ml_analytics import mse, mae, r2, classification_metrics
from .evaluation_gate import EvaluationResult, evaluate

@dataclass(frozen=True)
class ModelReport:
    task: str
    metrics: Dict[str,float]
    gate: EvaluationResult

def evaluate_regression(y: Sequence[float], pred: Sequence[float], requirements=None) -> ModelReport:
    if len(y)!=len(pred) or not y:raise ValueError("non-empty equal-length vectors required")
    metrics={"mse":mse(y,pred),"mae":mae(y,pred),"r2":r2(y,pred)}
    return ModelReport("regression",metrics,evaluate(metrics,requirements or {}))

def evaluate_classification(y, pred, requirements=None) -> ModelReport:
    if len(y)!=len(pred) or not y:raise ValueError("non-empty equal-length vectors required")
    raw=classification_metrics(y,pred)
    metrics={k:float(v) for k,v in raw.items() if k!="confusion"}
    return ModelReport("classification",metrics,evaluate(metrics,requirements or {}))

def holdout_split(X, y, test_fraction=.2):
    if len(X)!=len(y) or len(X)<2:raise ValueError("aligned dataset with >=2 rows required")
    if not 0<test_fraction<1:raise ValueError("test_fraction must be between 0 and 1")
    n=max(1,min(len(X)-1,round(len(X)*test_fraction)))
    return (list(X[:-n]),list(y[:-n])),(list(X[-n:]),list(y[-n:]))
