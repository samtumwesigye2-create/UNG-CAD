"""Deterministic polynomial identities used by CAD/geometry reasoning."""
def difference_of_squares(x,y): return (x-y)*(x+y)
def difference_of_cubes(x,y): return (x-y)*(x*x+x*y+y*y)
def square_ring_area(outer,inner):
    if outer < inner or inner < 0: raise ValueError("require outer >= inner >= 0")
    return difference_of_squares(outer,inner)
def cubic_shell_volume(outer,inner):
    if outer < inner or inner < 0: raise ValueError("require outer >= inner >= 0")
    return difference_of_cubes(outer,inner)
def verify_difference_of_squares(x,y,tol=1e-12): return abs((x*x-y*y)-difference_of_squares(x,y)) <= tol
def verify_difference_of_cubes(x,y,tol=1e-12): return abs((x**3-y**3)-difference_of_cubes(x,y)) <= tol
