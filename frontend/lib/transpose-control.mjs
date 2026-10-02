// Capo stepper shared by the mobile board and the desktop selector. All state stays in the page's single `semitones`
// value: capo N is `semitones = -N` (chords written N semitones lower so the
// capo'd guitar sounds in the original key). Past the capo range the stepper
// keeps transposing without a capo, up to the API limit.
export const CAPO_MAX = 7;
export const SHIFT_LIMIT = 11;

/** Capo fret for a semitone shift, or 0 when the shift is not a capo shift. */
export function capoFromSemitones(semitones) {
  return semitones <= -1 && semitones >= -CAPO_MAX ? -semitones : 0;
}

/**
 * Describe the stepper for the current shift.
 *
 * `+` raises the capo one fret (semitones - 1); past fret 7 it keeps lowering
 * the key without a capo. `−` lowers the capo one fret (semitones + 1); below
 * fret 0 it keeps raising the key without a capo.
 */
export function transposeStepper(semitones) {
  const capo = capoFromSemitones(semitones);
  let label;
  if (semitones <= 0 && semitones >= -CAPO_MAX) label = { kind: "capo", capo };
  else if (semitones > 0) label = { kind: "keyUp", semitones };
  else label = { kind: "keyDown", semitones };
  return {
    capo,
    label,
    plus: {
      next: semitones - 1,
      disabled: semitones <= -SHIFT_LIMIT,
      action: semitones <= 0 && semitones > -CAPO_MAX ? "capoUp" : "keyDown",
    },
    minus: {
      next: semitones + 1,
      disabled: semitones >= SHIFT_LIMIT,
      action: semitones < 0 && semitones >= -CAPO_MAX ? "capoDown" : "keyUp",
    },
  };
}

/**
 * Text for a stepper: the small label, the value, and the two buttons'
 * accessible names. `t` is the page's translation table.
 */
export function stepperText(stepper, t) {
  const { label, plus, minus } = stepper;
  return {
    caption: label.kind === "capo" ? t.capoPosition : label.kind === "keyUp" ? t.mKeyUpNoCapo : t.mOutOfRangeDown,
    value: label.kind === "capo" ? String(label.capo) : t.mSemitoneValue(label.semitones),
    plusLabel: plus.action === "capoUp" ? t.mCapoUp : t.mKeyDownStep,
    minusLabel: minus.action === "capoDown" ? t.mCapoDown : t.mKeyUpStep,
  };
}

/** Board header suffix: "카포 N" inside the capo range, otherwise a signed semitone count. */
export function shiftSummary(semitones) {
  const capo = capoFromSemitones(semitones);
  return capo ? { kind: "capo", capo } : { kind: "semitones", semitones };
}
