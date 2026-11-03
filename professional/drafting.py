"""UNG-CAD professional 2D drafting geometry core (millimetres).

Dependency-free, deterministic geometry primitives and DXF R12 export.
This is a foundation, not a complete DWG/BIM/CAE implementation.
"""
from dataclasses import dataclass, field
from math import cos, sin, radians, hypot, isfinite
from pathlib import Path
from typing import Union

@dataclass(frozen=True)
class Point:
    x: float
    y: float

@dataclass(frozen=True)
class Line:
    start: Point
    end: Point
    layer: str = "0"

@dataclass(frozen=True)
class Circle:
    center: Point
    radius: float
    layer: str = "0"

@dataclass(frozen=True)
class Arc:
    center: Point
    radius: float
    start_angle: float
    end_angle: float
    layer: str = "0"

@dataclass(frozen=True)
class Polyline:
    points: tuple[Point, ...]
    closed: bool = False
    layer: str = "0"

Entity = Union[Line, Circle, Arc, Polyline]

@dataclass
class Drawing:
    entities: list[Entity] = field(default_factory=list)
    units: str = "mm"

    def add(self, entity: Entity) -> None:
        validate(entity)
        self.entities.append(entity)

    def bounds(self):
        pts = []
        for e in self.entities:
            if isinstance(e, Line):
                pts.extend((e.start, e.end))
            elif isinstance(e, Polyline):
                pts.extend(e.points)
            else:
                pts.extend((Point(e.center.x-e.radius,e.center.y-e.radius),
                            Point(e.center.x+e.radius,e.center.y+e.radius)))
        if not pts:
            return None
        return min(p.x for p in pts), min(p.y for p in pts), max(p.x for p in pts), max(p.y for p in pts)

def validate(e: Entity) -> None:
    if not isinstance(e.layer, str) or not e.layer or any(c in e.layer for c in "\r\n"):
        raise ValueError("Invalid layer")
    points = ([e.start, e.end] if isinstance(e, Line) else
              list(e.points) if isinstance(e, Polyline) else [e.center])
    if isinstance(e, Polyline) and len(points) < (3 if e.closed else 2):
        raise ValueError("Polyline has too few points")
    if not all(isfinite(p.x) and isfinite(p.y) for p in points):
        raise ValueError("Nonfinite coordinate")
    if isinstance(e, (Circle, Arc)) and (not isfinite(e.radius) or e.radius <= 0):
        raise ValueError("Invalid radius")
    if isinstance(e, Arc) and not all(map(isfinite, (e.start_angle, e.end_angle))):
        raise ValueError("Invalid angle")

def length(line: Line) -> float:
    return hypot(line.end.x-line.start.x, line.end.y-line.start.y)

def offset_line(line: Line, distance: float) -> Line:
    d = length(line)
    if d == 0 or not isfinite(distance):
        raise ValueError("Cannot offset degenerate line")
    dx = -(line.end.y-line.start.y)*distance/d
    dy = (line.end.x-line.start.x)*distance/d
    return Line(Point(line.start.x+dx,line.start.y+dy),
                Point(line.end.x+dx,line.end.y+dy),line.layer)

def rotate_point(p: Point, degrees: float, origin: Point = Point(0,0)) -> Point:
    a = radians(degrees)
    x, y = p.x-origin.x, p.y-origin.y
    return Point(origin.x+x*cos(a)-y*sin(a), origin.y+x*sin(a)+y*cos(a))

def dxf(drawing: Drawing) -> str:
    """Export ASCII DXF R12 entities; open in common CAD editors."""
    def pairs(*items):
        return "".join(f"{items[i]}\n{items[i+1]}\n" for i in range(0,len(items),2))
    out = [pairs(0,"SECTION",2,"HEADER",9,"$INSUNITS",70,4,0,"ENDSEC",
                 0,"SECTION",2,"ENTITIES")]
    def common(kind, layer):
        return pairs(0,kind,8,layer)
    def vertex(p):
        return pairs(10,p.x,20,p.y,30,0)
    for e in drawing.entities:
        validate(e)
        if isinstance(e, Line):
            out.append(common("LINE",e.layer)+vertex(e.start)+pairs(11,e.end.x,21,e.end.y,31,0))
        elif isinstance(e, Circle):
            out.append(common("CIRCLE",e.layer)+vertex(e.center)+pairs(40,e.radius))
        elif isinstance(e, Arc):
            out.append(common("ARC",e.layer)+vertex(e.center)+pairs(40,e.radius,50,e.start_angle,51,e.end_angle))
        elif isinstance(e, Polyline):
            out.append(common("POLYLINE",e.layer)+pairs(66,1,70,1 if e.closed else 0))
            for p in e.points:
                out.append(common("VERTEX",e.layer)+vertex(p))
            out.append(pairs(0,"SEQEND"))
    out.append(pairs(0,"ENDSEC",0,"EOF"))
    return "".join(out)

def save_dxf(drawing: Drawing, path: str) -> None:
    Path(path).write_text(dxf(drawing),encoding="ascii")
