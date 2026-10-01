export const CAPO_MAX: 7;
export const SHIFT_LIMIT: 11;
export type StepAction = "capoUp" | "capoDown" | "keyUp" | "keyDown";
export type StepperLabel =
  | { kind: "capo"; capo: number }
  | { kind: "keyUp"; semitones: number }
  | { kind: "keyDown"; semitones: number };
export function capoFromSemitones(semitones: number): number;
export interface Stepper {
  capo: number;
  label: StepperLabel;
  plus: { next: number; disabled: boolean; action: StepAction };
  minus: { next: number; disabled: boolean; action: StepAction };
}
export function transposeStepper(semitones: number): Stepper;
export interface StepperStrings {
  capoPosition: string; mKeyUpNoCapo: string; mOutOfRangeDown: string; mSemitoneValue: (n: number) => string;
  mCapoUp: string; mCapoDown: string; mKeyDownStep: string; mKeyUpStep: string;
}
export function stepperText(stepper: Stepper, t: StepperStrings): { caption: string; value: string; plusLabel: string; minusLabel: string };
export function shiftSummary(semitones: number):
  | { kind: "capo"; capo: number }
  | { kind: "semitones"; semitones: number };
