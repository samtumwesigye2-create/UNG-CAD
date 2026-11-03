"""Safe SVG preview for UNG-CAD 2D drawings.

Converts native drafting primitives to browser-viewable vector artwork.
No external packages required. Coordinates are millimetres.
"""
from html import escape
from math import cos, sin, radians
from .drafting import Drawing, Line, Circle, Arc, Polyline, validate

def render_svg(drawing: Drawing, padding: float = 10) -> str:
    if padding < 0:
        raise ValueError("padding must be nonnegative")
    bounds = drawing.bounds()
    if bounds is None:
        bounds = (0, 0, 100, 100)
    x0, y0, x1, y1 = bounds
    width = max(x1-x0, 1)
    height = max(y1-y0, 1)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0-padding:g} {y0-padding:g} {width+2*padding:g} {height+2*padding:g}" role="img" aria-label="CAD drawing">',
             '<g fill="none" stroke="#24a8e0" stroke-width="0.5" vector-effect="non-scaling-stroke">']
    for e in drawing.entities:
        validate(e)
        layer = escape(e.layer, quote=True)
        if isinstance(e, Line):
            parts.append(f'<line data-layer="{layer}" x1="{e.start.x:g}" y1="{e.start.y:g}" x2="{e.end.x:g}" y2="{e.end.y:g}"/>')
        elif isinstance(e, Circle):
            parts.append(f'<circle data-layer="{layer}" cx="{e.center.x:g}" cy="{e.center.y:g}" r="{e.radius:g}"/>')
        elif isinstance(e, Polyline):
            coords = " ".join(f"{p.x:g},{p.y:g}" for p in e.points)
            tag = "polygon" if e.closed else "polyline"
            parts.append(f'<{tag} data-layer="{layer}" points="{coords}"/>')
        elif isinstance(e, Arc):
            start = radians(e.start_angle)
            end = radians(e.end_angle)
            sx = e.center.x + e.radius*cos(start)
            sy = e.center.y + e.radius*sin(start)
            ex = e.center.x + e.radius*cos(end)
            ey = e.center.y + e.radius*sin(end)
            delta = (e.end_angle-e.start_angle)%360
            if delta == 0 and e.end_angle != e.start_angle:
                parts.append(f'<circle data-layer="{layer}" cx="{e.center.x:g}" cy="{e.center.y:g}" r="{e.radius:g}"/>')
            else:
                large = int(delta > 180)
                parts.append(f'<path data-layer="{layer}" d="M {sx:g} {sy:g} A {e.radius:g} {e.radius:g} 0 {large} 1 {ex:g} {ey:g}"/>')
    parts.extend(["</g>","</svg>"])
    return "".join(parts)
