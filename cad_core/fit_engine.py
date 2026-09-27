"""Named mechanical-fit allowances, kept separate from process compensation."""
from dataclasses import dataclass
@dataclass(frozen=True)
class FitProfile:
 name:str;diametral_allowance_mm:float
FIT_PROFILES={
 "press":FitProfile("press",-0.10),"snug":FitProfile("snug",0.05),"slip":FitProfile("slip",0.20),
 "free":FitProfile("free",0.40),"screw_clearance":FitProfile("screw_clearance",0.30),
 "heat_set_insert":FitProfile("heat_set_insert",-0.15),"connector":FitProfile("connector",0.25),
}
def apply_fit(nominal_mm:float,profile:str)->float:
 if nominal_mm<=0:raise ValueError("nominal dimension must be positive")
 if profile not in FIT_PROFILES:raise ValueError(f"unknown fit profile: {profile}")
 value=nominal_mm+FIT_PROFILES[profile].diametral_allowance_mm
 if value<=0:raise ValueError("fit allowance produced invalid dimension")
 return value
