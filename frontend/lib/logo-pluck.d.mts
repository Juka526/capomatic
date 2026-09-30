export const PLUCK_MODES: { n: number; a: number; tau: number }[];
export const PLUCK_F1: number;
export const STOP_ENERGY: number;
export const REST_M_PATH: string;
export function mPath(vibration: ((u: number) => number) | null): string;
export function pluckEnergy(t: number): number;
export function pluckVibration(t: number): (u: number) => number;
export function pluckFrame(t: number): string | null;
