"""UNG shared scientific research: quantum-gravity toy models.

Educational/research calculations only. This module does not claim a complete
theory of quantum gravity. The simplified spin-1/2 LQG entropy comparison uses
an Immirzi parameter chosen to reproduce the Bekenstein-Hawking coefficient.
"""
import math
from typing import Iterable

G=6.67430e-11
C=2.99792458e8
HBAR=1.054571817e-34
KB=1.380649e-23
M_SUN=1.98847e30
YEAR=3.15576e7
GAMMA_SIMPLE=math.log(2)/(math.pi*math.sqrt(3))

def planck_units():
    lp=math.sqrt(HBAR*G/C**3); mp=math.sqrt(HBAR*C/G); ep=mp*C**2
    return {"length_m":lp,"time_s":lp/C,"mass_kg":mp,
            "energy_J":ep,"temperature_K":ep/KB}

def lqg_area(spins: Iterable[float], gamma: float=GAMMA_SIMPLE):
    spins=list(spins)
    if gamma <= 0 or any(j <= 0 or abs(2*j-round(2*j))>1e-12 for j in spins):
        raise ValueError("gamma must be positive and spins must be positive half-integers")
    lp2=HBAR*G/C**3
    return 8*math.pi*gamma*lp2*sum(math.sqrt(j*(j+1)) for j in spins)

def area_spectrum(max_j: float=3.0):
    if max_j < 0.5: return []
    return [(j/2,lqg_area([j/2])) for j in range(1,int(math.floor(2*max_j))+1)]

def black_hole(mass_kg: float):
    if mass_kg <= 0: raise ValueError("mass_kg must be positive")
    lp2=HBAR*G/C**3
    rs=2*G*mass_kg/C**2
    area=4*math.pi*rs**2
    return {"radius_m":rs,"area_m2":area,"entropy_kB":area/(4*lp2),
            "temperature_K":HBAR*C**3/(8*math.pi*G*mass_kg*KB),
            "evaporation_years":5120*math.pi*G**2*mass_kg**3/(HBAR*C**4)/YEAR}

def simplified_lqg_entropy(mass_kg: float, gamma: float=GAMMA_SIMPLE):
    area=black_hole(mass_kg)["area_m2"]
    n=area/lqg_area([0.5],gamma)
    s=n*math.log(2)
    return {"puncture_count_continuous":n,"entropy_kB":s,
            "model":"simplified_spin_half_lqg_entropy",
            "toy_model":True,
            "gamma":gamma,
            "gamma_chosen_for_bh_coefficient":abs(gamma-GAMMA_SIMPLE)<1e-15}

def entropy_comparison(mass_kg: float, gamma: float=GAMMA_SIMPLE):
    bh=black_hole(mass_kg)["entropy_kB"]
    lqg=simplified_lqg_entropy(mass_kg,gamma)
    return {"bekenstein_hawking_entropy_kB":bh,
            "simplified_lqg_entropy_kB":lqg["entropy_kB"],
            "ratio":lqg["entropy_kB"]/bh,
            "metadata":{"toy_model":True,
                        "warning":"A matching ratio with GAMMA_SIMPLE is calibration of this simplified counting model, not proof of quantum gravity."}}
