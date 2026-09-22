"""Material consumption helpers."""
import math
def filament_grams(extrusion_mm,diameter_mm=1.75,density_g_cm3=1.24):
    volume_mm3=math.pi*(diameter_mm/2)**2*max(0,extrusion_mm)
    return round(volume_mm3/1000*density_g_cm3,2)
def affordable(remaining_g,needed_g,reserve_g=5):
    return float(remaining_g)>=float(needed_g)+float(reserve_g)
