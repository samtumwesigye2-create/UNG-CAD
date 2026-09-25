from cad_core import CADMath

def test_cad_math_adapter_continuous():
    assert abs(CADMath.derivative(lambda x: x*x, 2.0) - 4.0) < 1e-5
    assert abs(CADMath.integrate(lambda x: x, 0.0, 2.0) - 2.0) < 1e-5

def test_cad_math_discrete_histories():
    assert CADMath.rate([0.0, 2.0, 6.0], 2.0) == [1.0, 2.0]
    assert abs(CADMath.accumulated([0.0, 2.0, 4.0], 1.0) - 4.0) < 1e-12

def test_cad_math_vector_field():
    F=lambda x,y,z:(x,y,z)
    assert abs(CADMath.divergence(F,(1,2,3))-3.0) < 1e-4
