"""Dependency-free supervised-learning primitives for engineering predictions."""
from dataclasses import dataclass
from math import exp
@dataclass(frozen=True)
class Prediction:
    value: float
    confidence: float|None
    model: str
    version: str="1"
def linear_regression_predict(features,weights,bias=0.0):
    if len(features)!=len(weights): raise ValueError("feature/weight mismatch")
    return Prediction(bias+sum(x*w for x,w in zip(features,weights)),None,"linear-regression")
def logistic_regression_predict(features,weights,bias=0.0):
    z=linear_regression_predict(features,weights,bias).value
    p=1/(1+exp(-max(-709,min(709,z))))
    return Prediction(p,max(p,1-p),"logistic-regression")
def knn_predict(point,samples,k=3):
    if k<1 or not samples: raise ValueError("samples required and k >= 1")
    ranked=sorted(samples,key=lambda s:sum((a-b)**2 for a,b in zip(point,s[0])))[:k]
    votes={}
    for _,label in ranked: votes[label]=votes.get(label,0)+1
    label,count=max(votes.items(),key=lambda x:x[1])
    return Prediction(float(label),count/len(ranked),"knn")
SUPPORTED_MODEL_FAMILIES=("linear_regression","logistic_regression","knn","svm","decision_tree","random_forest","boosting","neural_network")
DETERMINISTIC_GATE_POLICY="predictions_do_not_override_release_gate"
