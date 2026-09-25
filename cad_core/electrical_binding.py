"""Bind electrical properties to CAD component geometry and material metadata."""
from dataclasses import dataclass, replace
from .electrical import conductor_resistance

@dataclass(frozen=True)
class ElectricalMaterial:
    name: str
    resistivity_ohm_m: float
    temperature_coefficient_per_c: float = 0.0
    reference_temperature_c: float = 20.0

COPPER = ElectricalMaterial("copper", 1.68e-8, 0.00393)
ALUMINUM = ElectricalMaterial("aluminum", 2.82e-8, 0.00403)

@dataclass(frozen=True)
class ConductorGeometry:
    path_length_mm: float
    cross_section_mm2: float

@dataclass(frozen=True)
class ElectricalBinding:
    artifact_id: str
    geometry: ConductorGeometry
    material: ElectricalMaterial = COPPER
    current_a: float = 0.0
    temperature_c: float = 20.0

    @property
    def resistance_ohm(self):
        base=conductor_resistance(self.material.resistivity_ohm_m,self.geometry.path_length_mm/1000.0,self.geometry.cross_section_mm2*1e-6)
        return base*(1+self.material.temperature_coefficient_per_c*(self.temperature_c-self.material.reference_temperature_c))

    @property
    def copper_loss_w(self):
        return self.current_a*self.current_a*self.resistance_ohm

    def with_geometry(self, *, path_length_mm=None, cross_section_mm2=None):
        g=replace(self.geometry,
            path_length_mm=self.geometry.path_length_mm if path_length_mm is None else path_length_mm,
            cross_section_mm2=self.geometry.cross_section_mm2 if cross_section_mm2 is None else cross_section_mm2)
        return replace(self,geometry=g)

class ElectricalBindingRegistry:
    def __init__(self): self._bindings={}
    def bind(self,binding):
        if binding.geometry.path_length_mm<0 or binding.geometry.cross_section_mm2<=0: raise ValueError("invalid conductor geometry")
        self._bindings[binding.artifact_id]=binding
        return binding
    def get(self,artifact_id): return self._bindings[artifact_id]
    def update_geometry(self,artifact_id,**changes):
        b=self.get(artifact_id).with_geometry(**changes); self._bindings[artifact_id]=b; return b
