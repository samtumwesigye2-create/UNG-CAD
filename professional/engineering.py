"""UNG-CAD Group 2: electrical, engineering and manufacturing preflight.

Preliminary calculations only. Never use as structural certification, electrical
safety sign-off, production toolpath or physical build approval.
"""
from dataclasses import dataclass, field
from math import isfinite, pi
from .parametric import Solid, positive

@dataclass(frozen=True)
class Net:
    name: str
    pins: tuple[str,...]
    def __post_init__(self):
        if not self.name or len(self.pins)<2 or len(set(self.pins))!=len(self.pins):
            raise ValueError("Net needs unique connected pins")

@dataclass
class Circuit:
    nets: list[Net]=field(default_factory=list)
    def check(self):
        errors=[]
        ownership={}
        for net in self.nets:
            for pin in net.pins:
                if pin in ownership:
                    errors.append(f"Pin {pin} appears in both {ownership[pin]} and {net.name}")
                ownership[pin]=net.name
        return errors

@dataclass(frozen=True)
class Beam:
    length_mm: float
    width_mm: float
    height_mm: float
    force_n: float
    elastic_modulus_mpa: float
    def cantilever_tip_deflection_mm(self):
        """Small-deflection Euler-Bernoulli rectangular cantilever, tip point load."""
        for name,value in (("length",self.length_mm),("width",self.width_mm),("height",self.height_mm),("modulus",self.elastic_modulus_mpa)):
            positive(name,value)
        if not isfinite(self.force_n):
            raise ValueError("Invalid force")
        inertia=self.width_mm*self.height_mm**3/12
        return self.force_n*self.length_mm**3/(3*self.elastic_modulus_mpa*inertia)
    def max_bending_stress_mpa(self):
        self.cantilever_tip_deflection_mm()
        return abs(self.force_n)*self.length_mm*(self.height_mm/2)/(self.width_mm*self.height_mm**3/12)

@dataclass(frozen=True)
class PrintProfile:
    build_x_mm: float
    build_y_mm: float
    build_z_mm: float
    material: str
    nozzle_mm: float=0.4
    def __post_init__(self):
        for n,v in (("build_x",self.build_x_mm),("build_y",self.build_y_mm),("build_z",self.build_z_mm),("nozzle",self.nozzle_mm)):
            positive(n,v)
        if not self.material:
            raise ValueError("Material required")

@dataclass(frozen=True)
class PartEnvelope:
    x_mm: float
    y_mm: float
    z_mm: float
    material: str
    min_wall_mm: float
    def __post_init__(self):
        for n,v in (("x",self.x_mm),("y",self.y_mm),("z",self.z_mm),("wall",self.min_wall_mm)):
            positive(n,v)

def manufacturing_preflight(part: PartEnvelope, profile: PrintProfile):
    """Conservative gate: failure blocks release; pass does not certify printability."""
    failures=[]
    if any(a>b for a,b in zip((part.x_mm,part.y_mm,part.z_mm),(profile.build_x_mm,profile.build_y_mm,profile.build_z_mm))):
        failures.append("Part exceeds printer build envelope in specified orientation")
    if part.material.casefold()!=profile.material.casefold():
        failures.append("Material mismatch")
    if part.min_wall_mm < 2*profile.nozzle_mm:
        failures.append("Wall thinner than two nozzle widths")
    return {"status":"BLOCK" if failures else "PRELIMINARY_PASS","failures":failures,
            "requires":["orientation and supports","tolerance fit coupon","electrical and connector compatibility","toolpath verification","operator approval"]}

def estimate_filament_g(solid: Solid, density_g_cm3: float, infill_fraction: float=1.0):
    """Upper/lower conceptual estimate; not a slicer estimate."""
    if not isfinite(infill_fraction) or not 0<infill_fraction<=1:
        raise ValueError("Infill must be in (0,1]")
    return solid.estimate_mass_g(density_g_cm3)*infill_fraction
