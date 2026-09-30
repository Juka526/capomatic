// The wordmark's m is drawn as a plucked string: a frozen wave at rest, plus a
// decaying vibration (fundamental and two harmonics) after a pluck. Ported from
// the design handoff's capomatic-logo-final.html.
import { M_TYPES, M_XY, M_X_MIN, M_X_MAX, WAVE_AMPLITUDE, X_HEIGHT } from "./logo-geometry.mjs";

// Amplitudes are in x-height = 100 units. Higher modes die out faster.
export const PLUCK_MODES = [
  { n: 1, a: 9, tau: 0.75 },
  { n: 2, a: 13, tau: 0.5 },
  { n: 3, a: 4, tau: 0.28 },
];
export const PLUCK_F1 = 2.4; // Hz
export const STOP_ENERGY = 0.05;
const UNIT = X_HEIGHT / 100;

const round1 = (n) => Math.round(n * 10) / 10;

/**
 * Outline of the m. `vibration(u)` is an extra vertical displacement along the
 * string (u = 0 at the left end, 1 at the right); null draws the rest shape.
 * The weight w is 0 on the baseline, so the bottoms of the stems never move.
 */
export function mPath(vibration) {
  let out = "";
  let k = 0;
  for (const type of M_TYPES) {
    if (type === "Z") { out += "Z"; continue; }
    const x = M_XY[k++];
    const y = M_XY[k++];
    const t = (x - M_X_MIN) / (M_X_MAX - M_X_MIN);
    const w = Math.pow(Math.max(0, Math.min(1, -y / X_HEIGHT)), 1.6);
    const dy = WAVE_AMPLITUDE * Math.sin(2 * Math.PI * t) * w + (vibration ? vibration(t) * w : 0);
    out += type + round1(x + WAVE_AMPLITUDE * 0.55 * w * Math.sin(Math.PI * t)) + " " + round1(y - dy);
  }
  return out;
}

export const REST_M_PATH = mPath(null);

/** Remaining vibration energy t seconds after the pluck (26 at t = 0). */
export function pluckEnergy(t) {
  return PLUCK_MODES.reduce((sum, m) => sum + m.a * Math.exp(-t / m.tau), 0);
}

/** String displacement along u in [0, 1] at time t; zero at both fixed ends. */
export function pluckVibration(t) {
  return (u) => -PLUCK_MODES.reduce(
    (y, m) => y + m.a * UNIT * Math.exp(-t / m.tau) * Math.sin(m.n * Math.PI * u) * Math.cos(2 * Math.PI * PLUCK_F1 * m.n * t),
    0,
  );
}

/** Path for animation frame t, or the rest shape once the energy has died down. */
export function pluckFrame(t) {
  return pluckEnergy(t) <= STOP_ENERGY ? null : mPath(pluckVibration(t));
}
