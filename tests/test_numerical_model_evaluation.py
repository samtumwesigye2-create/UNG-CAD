import math
import pytest
from cad_core.numerical_solvers import bisection,newton,numerical_gradient,numerical_jacobian,numerical_hessian
from cad_core.model_evaluation import evaluate_regression,evaluate_classification,holdout_split

def test_root_solvers():
    assert bisection(lambda x:x*x-2,0,2).x==pytest.approx(math.sqrt(2),rel=1e-7)
    assert newton(lambda x:x*x-2,lambda x:2*x,1).x==pytest.approx(math.sqrt(2),rel=1e-7)

def test_gradient_jacobian_hessian():
    f=lambda v:v[0]**2+3*v[1]**2
    assert numerical_gradient(f,[2,1])==pytest.approx([4,6],rel=1e-4)
    J=numerical_jacobian(lambda v:[v[0]+v[1],v[0]*v[1]],[2,3])
    assert J[0]==pytest.approx([1,1],rel=1e-4)
    assert J[1]==pytest.approx([3,2],rel=1e-4)
    H=numerical_hessian(f,[2,1])
    assert H[0][0]==pytest.approx(2,rel=1e-3)
    assert H[1][1]==pytest.approx(6,rel=1e-3)

def test_model_evaluation_feeds_gate():
    r=evaluate_regression([1,2,3],[1,2,3],{"mae":("<=",0.01),"r2":(">=",.99)})
    assert r.gate.passed
    c=evaluate_classification([0,1,1],[0,1,0],{"accuracy":(">=",.6)})
    assert c.gate.passed
    train,test=holdout_split([[1],[2],[3],[4]],[1,2,3,4],.25)
    assert len(train[0])==3 and len(test[0])==1
