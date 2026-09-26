"""Complex-number and phasor primitives for UNG engineering analysis."""
from dataclasses import dataclass
import cmath, math

TAU=2*math.pi

@dataclass(frozen=True)
class Phasor:
    amplitude: float
    phase_rad: float
    frequency_hz: float=0.0
    def value(self, time_s: float=0.0) -> complex:
        return self.amplitude*cmath.exp(1j*(TAU*self.frequency_hz*time_s+self.phase_rad))
    def derivative(self, time_s: float=0.0) -> complex:
        return 1j*TAU*self.frequency_hz*self.value(time_s)

def euler(theta_rad: float) -> complex:
    return cmath.exp(1j*theta_rad)

def unit_circle(theta_rad: float) -> tuple[float,float]:
    z=euler(theta_rad); return z.real,z.imag

def magnitude(z: complex) -> float:
    return abs(z)

def phase(z: complex) -> float:
    return cmath.phase(z)

def three_phase(amplitude: float, frequency_hz: float, time_s: float=0.0) -> tuple[complex,complex,complex]:
    return tuple(Phasor(amplitude,p,frequency_hz).value(time_s) for p in (0,-2*math.pi/3,2*math.pi/3))

def euler_identity_error() -> float:
    return abs(cmath.exp(1j*math.pi)+1)
