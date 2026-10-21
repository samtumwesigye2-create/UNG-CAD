const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const sourcePath = path.join(__dirname, '..', 'public', 'ung-electrical.js');
assert.ok(fs.existsSync(sourcePath), 'ung-electrical.js must exist');

const context = { window: {} };
vm.createContext(context);
vm.runInContext(fs.readFileSync(sourcePath, 'utf8'), context, { filename: sourcePath });
const E = context.window.UNGElectrical;
assert.ok(E, 'window.UNGElectrical must be exported');

function close(actual, expected, tolerance = 1e-9) {
  assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} != ${expected}`);
}

close(E.peakToRms(Math.sqrt(2)), 1);
close(E.rmsToPeak(1), Math.sqrt(2));

const p = E.phasor(2, Math.PI / 2);
close(p.re, 0, 1e-12);
close(p.im, 2, 1e-12);

const z = E.impedanceRLC({ R: 10, L: 0.01, C: Infinity, frequency: 50 });
close(z.re, 10);
close(z.im, 2 * Math.PI * 50 * 0.01);

const current = E.acCurrent({ voltageRms: 120, R: 12, frequency: 60 });
close(current.currentRms, 10);
close(current.phase, 0);

const w = E.wave({ E0: 300, frequency: 1e6 });
close(w.wavelength, 299.792458, 1e-6);
close(w.B0, 300 / 299792458, 1e-15);

const s = E.sinusoid({ amplitude: 2, frequency: 10, phase: 0, offset: 1 });
close(s.period, 0.1);
close(s.value(0), 1);
const samples = E.sampleWaveform(s, s.period, 8);
assert.strictEqual(samples.length, 9);
close(samples[0].t, 0);
close(samples[8].t, s.period);

assert.throws(() => E.sinusoid({ frequency: 0 }), /frequency/i);
assert.throws(() => E.wave({ frequency: -1 }), /frequency/i);
assert.throws(() => E.impedanceRLC({ R: NaN, frequency: 60 }), /finite/i);
assert.throws(() => E.impedanceRLC({ C: 0, frequency: 60 }), /capacitance/i);
assert.throws(() => E.acCurrent({ voltageRms: 120, R: 0, L: 0, C: Infinity, frequency: 60 }), /zero impedance/i);
assert.throws(() => E.sampleWaveform(s, s.period, 0), /points/i);

console.log('ung-electrical regression tests passed');
