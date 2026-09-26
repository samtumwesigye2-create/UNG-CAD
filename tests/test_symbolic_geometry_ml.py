from cad_core.symbolic_geometry import *
from cad_core.supervised_ml import *
def test_algebra_geometry_identities():
    assert difference_of_squares(10,4)==84
    assert square_ring_area(10,4)==84
    assert difference_of_cubes(5,2)==117
    assert cubic_shell_volume(5,2)==117
    assert verify_difference_of_squares(3.5,1.2)
    assert verify_difference_of_cubes(3.5,1.2)
def test_invalid_shell_dimensions():
    import pytest
    with pytest.raises(ValueError): square_ring_area(2,3)
def test_regression_predictions():
    assert linear_regression_predict([2,3],[4,5],1).value==24
    assert .5 < logistic_regression_predict([1],[1]).value < 1
def test_knn_and_registry():
    p=knn_predict([0],[([0],1),([.1],1),([10],0)],2)
    assert p.value==1 and p.confidence==1
    assert {"svm","decision_tree","random_forest","boosting","neural_network"} <= set(SUPPORTED_MODEL_FAMILIES)
    assert DETERMINISTIC_GATE_POLICY=="predictions_do_not_override_release_gate"
