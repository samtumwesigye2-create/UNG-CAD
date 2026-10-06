/* UNG-CAD AC, phasor and electromagnetic-wave engineering helpers */
(function (g) {
  'use strict';

  const TAU = 2 * Math.PI;

  function finite(name, value) {
    const n = Number(value);
    if (!Number.isFinite(n)) throw new TypeError(`${name} must be finite`);
    return n;
  }

  function positive(name, value) {
    const n = finite(name, value);
    if (n <= 0) throw new RangeError(`${name} must be greater than zero`);
    return n;
  }

  function sinusoid({ amplitude = 1, frequency = 60, phase = 0, offset = 0 } = {}) {
    amplitude = finite('amplitude', amplitude);
    frequency = positive('frequency', frequency);
    phase = finite('phase', phase);
    offset = finite('offset', offset);
    const omega = TAU * frequency;
    return {
      amplitude,
      frequency,
      phase,
      offset,
      omega,
      period: 1 / frequency,
      value: (t) => offset + amplitude * Math.sin(omega * finite('time', t) + phase),
    };
  }

  function peakToRms(v) {
    return finite('peak value', v) / Math.sqrt(2);
  }

  function rmsToPeak(v) {
    return finite('RMS value', v) * Math.sqrt(2);
  }

  function phasor(magnitude, phase = 0) {
    magnitude = finite('magnitude', magnitude);
    phase = finite('phase', phase);
    return {
      re: magnitude * Math.cos(phase),
      im: magnitude * Math.sin(phase),
      magnitude,
      phase,
    };
  }

  function complex(re = 0, im = 0) {
    return { re: finite('real component', re), im: finite('imaginary component', im) };
  }

  function cadd(a, b) {
    return complex(a.re + b.re, a.im + b.im);
  }

  function cmul(a, b) {
    return complex(a.re * b.re - a.im * b.im, a.re * b.im + a.im * b.re);
  }

  function cdiv(a, b) {
    const ar = finite('numerator real component', a.re);
    const ai = finite('numerator imaginary component', a.im);
    const br = finite('denominator real component', b.re);
    const bi = finite('denominator imaginary component', b.im);
    const d = br * br + bi * bi;
    if (d === 0) throw new RangeError('Division by zero impedance');
    return complex((ar * br + ai * bi) / d, (ai * br - ar * bi) / d);
  }

  function polar(z) {
    const re = finite('real component', z.re);
    const im = finite('imaginary component', z.im);
    return { magnitude: Math.hypot(re, im), phase: Math.atan2(im, re) };
  }

  function impedanceRLC({ R = 0, L = 0, C = Infinity, frequency = 60 } = {}) {
    R = finite('resistance', R);
    L = finite('inductance', L);
    if (L < 0) throw new RangeError('inductance must be zero or greater');
    frequency = positive('frequency', frequency);

    let capacitance = C;
    if (C !== Infinity) {
      capacitance = Number(C);
      if (!Number.isFinite(capacitance)) throw new TypeError('capacitance must be finite or Infinity');
      if (capacitance <= 0) throw new RangeError('capacitance must be greater than zero or Infinity');
    }

    const omega = TAU * frequency;
    const xl = omega * L;
    const xc = capacitance === Infinity ? 0 : 1 / (omega * capacitance);
    return complex(R, xl - xc);
  }

  function acCurrent({ voltageRms = 120, R = 0, L = 0, C = Infinity, frequency = 60, sourcePhase = 0 } = {}) {
    voltageRms = finite('voltageRms', voltageRms);
    sourcePhase = finite('sourcePhase', sourcePhase);
    const impedance = impedanceRLC({ R, L, C, frequency });
    if (impedance.re === 0 && impedance.im === 0) throw new RangeError('Cannot calculate AC current with zero impedance');
    const voltage = phasor(voltageRms, sourcePhase);
    const current = cdiv(voltage, impedance);
    const currentPolar = polar(current);
    return {
      current,
      currentRms: currentPolar.magnitude,
      phase: currentPolar.phase,
      impedance,
      impedancePolar: polar(impedance),
    };
  }

  function wave({ E0 = 1, frequency = 1e6, phase = 0, c = 299792458 } = {}) {
    E0 = finite('E0', E0);
    frequency = positive('frequency', frequency);
    phase = finite('phase', phase);
    c = positive('wave speed', c);
    const omega = TAU * frequency;
    const k = omega / c;
    const B0 = E0 / c;
    return {
      E0,
      B0,
      frequency,
      omega,
      k,
      wavelength: c / frequency,
      E: (z, t) => E0 * Math.sin(k * finite('position', z) - omega * finite('time', t) + phase),
      B: (z, t) => B0 * Math.sin(k * finite('position', z) - omega * finite('time', t) + phase),
    };
  }

  function sampleWaveform(model, duration = model.period || 1, points = 256) {
    if (!model || typeof model.value !== 'function') throw new TypeError('model.value must be a function');
    duration = finite('duration', duration);
    if (duration < 0) throw new RangeError('duration must be zero or greater');
    points = Number(points);
    if (!Number.isInteger(points) || points <= 0) throw new RangeError('points must be a positive integer');
    const out = [];
    for (let i = 0; i <= points; i += 1) {
      const t = duration * i / points;
      out.push({ t, value: model.value(t) });
    }
    return out;
  }

  g.UNGElectrical = {
    sinusoid,
    peakToRms,
    rmsToPeak,
    phasor,
    complex,
    cadd,
    cmul,
    cdiv,
    polar,
    impedanceRLC,
    acCurrent,
    wave,
    sampleWaveform,
  };
})(window);
