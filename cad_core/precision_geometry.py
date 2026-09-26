from __future__ import annotations
from dataclasses import dataclass
import math

GEOMETRY_EPSILON = 1e-9

@dataclass(frozen=True)
class Point:
    x: float
    y: float

@dataclass(frozen=True)
class Line:
    start: Point
    end: Point

@dataclass(frozen=True)
class Circle:
    center: Point
    radius: float
    def __post_init__(self):
        if self.radius < 0:
            raise ValueError("radius must be non-negative")

@dataclass
class Viewport:
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0
    def __post_init__(self):
        if self.zoom <= 0:
            raise ValueError("zoom must be > 0")
    def world_to_screen(self, p: Point) -> tuple[float, float]:
        return ((p.x + self.pan_x) * self.zoom, (p.y + self.pan_y) * self.zoom)
    def screen_to_world(self, x: float, y: float) -> Point:
        return Point(x / self.zoom - self.pan_x, y / self.zoom - self.pan_y)

def points_equal(a: Point, b: Point, epsilon: float = GEOMETRY_EPSILON) -> bool:
    return abs(a.x-b.x) <= epsilon and abs(a.y-b.y) <= epsilon

def snap_to_zero(value: float, tolerance: float = GEOMETRY_EPSILON) -> float:
    return 0.0 if abs(value) < tolerance else value

def snap_value(value: float, step: float = 1.0) -> float:
    if step <= 0:
        raise ValueError("step must be > 0")
    return round(value / step) * step

def get_drawing_point(raw_x: float, raw_y: float, viewport: Viewport, grid_step: float = 1.0) -> Point:
    p=viewport.screen_to_world(raw_x, raw_y)
    return Point(snap_value(p.x,grid_step),snap_value(p.y,grid_step))

def rotate_point(point: Point, origin: Point, angle_degrees: float) -> Point:
    r=math.radians(angle_degrees)
    c=snap_to_zero(math.cos(r)); s=snap_to_zero(math.sin(r))
    dx=point.x-origin.x; dy=point.y-origin.y
    return Point(origin.x+dx*c-dy*s, origin.y+dx*s+dy*c)

def scale_point(point: Point, origin: Point, factor: float) -> Point:
    return Point(origin.x+(point.x-origin.x)*factor, origin.y+(point.y-origin.y)*factor)

def enforce_line_length(start: Point, current: Point, target_length: float) -> Point:
    if target_length < 0:
        raise ValueError("target_length must be non-negative")
    dx=current.x-start.x; dy=current.y-start.y
    length=math.hypot(dx,dy)
    if length <= GEOMETRY_EPSILON:
        return start
    k=target_length/length
    return Point(start.x+dx*k,start.y+dy*k)
