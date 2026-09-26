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

def svm_linear_predict(features,weights,bias=0.0):
    score=linear_regression_predict(features,weights,bias).value
    return Prediction(1.0 if score>=0 else 0.0,None,"linear-svm")

def decision_stump_predict(features,feature_index,threshold,left_value=0.0,right_value=1.0):
    if feature_index<0 or feature_index>=len(features): raise ValueError("feature index out of range")
    return Prediction(float(left_value if features[feature_index]<=threshold else right_value),None,"decision-tree")

def random_forest_predict(features,trees):
    if not trees: raise ValueError("trees required")
    values=[decision_stump_predict(features,**tree).value for tree in trees]
    votes={}
    for v in values: votes[v]=votes.get(v,0)+1
    value,count=max(votes.items(),key=lambda x:x[1])
    return Prediction(float(value),count/len(values),"random-forest")

def boosting_predict(features,learners,bias=0.0):
    score=bias
    for learner in learners:
        weight=float(learner.get("weight",1.0))
        args={k:v for k,v in learner.items() if k!="weight"}
        score+=weight*decision_stump_predict(features,**args).value
    return Prediction(score,None,"boosting")

def neural_network_predict(features,hidden_weights,hidden_bias,output_weights,output_bias=0.0):
    if len(hidden_weights)!=len(hidden_bias) or len(hidden_weights)!=len(output_weights): raise ValueError("network shape mismatch")
    hidden=[]
    for row,b in zip(hidden_weights,hidden_bias):
        if len(row)!=len(features): raise ValueError("network shape mismatch")
        z=b+sum(x*w for x,w in zip(features,row))
        hidden.append(max(0.0,z))
    value=output_bias+sum(h*w for h,w in zip(hidden,output_weights))
    return Prediction(value,None,"neural-network")
