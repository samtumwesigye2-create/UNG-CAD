import math
from ung_shared.calculus_field import derivative, integrate, accumulation, evaluate_antiderivative, geometric_sum, taylor, gradient, divergence, curl, line_integral, surface_flux

def close(a,b,tol=1e-5): assert abs(a-b) < tol

def test_derivative_and_integral():
    close(derivative(lambda x:x*x,3),6)
    close(integrate(lambda x:x*x,0,1),1/3)

def test_ftc():
    f=lambda x:x*x
    A=lambda x:accumulation(f,0,x)
    close(derivative(A,0.7),f(0.7),1e-4)
    close(evaluate_antiderivative(lambda x:x**3/3,0,2),8/3)

def test_series_and_taylor():
    close(geometric_sum(1,.5),2)
    close(taylor([lambda x:1,lambda x:1,lambda x:1,lambda x:1],1), 1+1+.5+1/6)

def test_vector_ops():
    f=lambda x,y,z:x*x+y*y+z*z
    g=gradient(f,(1,2,3))
    assert all(abs(a-b)<1e-4 for a,b in zip(g,(2,4,6)))
    F=lambda x,y,z:(x,y,z)
    close(divergence(F,(2,3,4)),3)
    assert all(abs(v)<1e-5 for v in curl(F,(1,2,3)))

def test_line_and_surface_integrals():
    F=lambda x,y,z:(x,y,z)
    path=lambda t:(t,0,0)
    close(line_integral(F,path,0,1),.5,1e-4)
    plane=lambda u,v:(u,v,1)
    close(surface_flux(lambda x,y,z:(0,0,2),plane,0,1,0,1,20,20),2,1e-4)
