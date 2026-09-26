"""Tolerance-driven parametric 3D circle geometry for UNG-CAD."""
import math
from dataclasses import dataclass

_EPS = 1e-12

@dataclass(frozen=True)
class Point3D:
    x: float
    y: float
    z: float

    def norm(self) -> float:
        return math.sqrt(self.x*self.x + self.y*self.y + self.z*self.z)

    def normalized(self) -> "Point3D":
        n=self.norm()
        if n <= _EPS:
            raise ValueError("Circle normal must be non-zero.")
        return Point3D(self.x/n,self.y/n,self.z/n)

def _cross(a: Point3D,b: Point3D) -> Point3D:
    return Point3D(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x)

def _basis(normal: Point3D) -> tuple[Point3D,Point3D]:
    """Stable orthonormal basis spanning the plane perpendicular to normal."""
    n=normal.normalized()
    helper=Point3D(0,0,1) if abs(n.z)<0.9 else Point3D(1,0,0)
    u=_cross(helper,n).normalized()
    v=_cross(n,u).normalized()
    return u,v

@dataclass(frozen=True)
class CADCircle3D:
    center: Point3D
    radius: float
    normal: Point3D

    def generate_tessellated_vertices(self,tolerance: float=0.01,max_segments: int=1_000_000) -> list[Point3D]:
        """Tessellate with maximum radial chord error <= tolerance."""
        if self.radius <= 0:
            return []
        if tolerance <= 0:
            raise ValueError("Tolerance must be positive.")
        if max_segments < 12:
            raise ValueError("max_segments must be at least 12.")

        # If tolerance >= radius, 12 segments already exceeds the requested fidelity.
        c=max(-1.0,min(1.0,1.0-(tolerance/self.radius)))
        half_angle=math.acos(c)
        if half_angle <= _EPS:
            num_segments=max_segments
        else:
            num_segments=max(12,min(max_segments,int(math.ceil(math.pi/half_angle))))

        u,v=_basis(self.normal)
        out=[]
        for i in range(num_segments):
            t=2.0*math.pi*i/num_segments
            ct,st=math.cos(t),math.sin(t)
            out.append(Point3D(
                self.center.x+self.radius*(u.x*ct+v.x*st),
                self.center.y+self.radius*(u.y*ct+v.y*st),
                self.center.z+self.radius*(u.z*ct+v.z*st),
            ))
        return out

def scale_cad_circle(circle: CADCircle3D,scale_factor: float) -> CADCircle3D:
    """Uniformly scale parametric geometry, then retessellate when needed."""
    if scale_factor <= 0:
        raise ValueError("Scale factor must be positive.")
    return CADCircle3D(
        Point3D(circle.center.x*scale_factor,circle.center.y*scale_factor,circle.center.z*scale_factor),
        circle.radius*scale_factor,
        circle.normal,
    )

def _clean(v: float) -> float:
    return 0.0 if abs(v)<_EPS else v

def rotate_point_2d(x: float,y: float,angle_rad: float) -> tuple[float,float]:
    c,s=_clean(math.cos(angle_rad)),_clean(math.sin(angle_rad))
    return _clean(x*c-y*s),_clean(x*s+y*c)

def rotate_cad_circle_z(circle: CADCircle3D,angle_degrees: float) -> CADCircle3D:
    """Rotate both center and orientation around world Z; radius is invariant."""
    a=math.radians(angle_degrees)
    cx,cy=rotate_point_2d(circle.center.x,circle.center.y,a)
    nx,ny=rotate_point_2d(circle.normal.x,circle.normal.y,a)
    return CADCircle3D(Point3D(cx,cy,circle.center.z),circle.radius,Point3D(nx,ny,circle.normal.z))
