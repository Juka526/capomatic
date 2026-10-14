# research/melody (local research only; not deployed, not packaged)

Plan: `docs/plans/V2_3_MELODY.md`. Status: M0 + M1 preparation. No engine installed or run; every measurement is NOT RUN.

- `python research/melody/readiness.py` — fails closed (exit 1, `NOT READY`) until rights, hashes, humans and Lock A exist. `--selfcheck` proves the checker fires on known-bad input.
- `rights_register.json` — per-asset licence/pin/hash register. Entry usable only when `status == "cleared"` with both hashes set. Code licence never clears weights, data, fonts or language packs. oemer weights are `blocked`.
- `lock_a.template.json` — copy to `lock_a.json` (with Lock B section) and fill with real values. Humans in `roles` must be disjoint; held-out stays sealed.
- `labels.schema.json` — expected-label schema (events, anchors, text, hand-calculated transpositions). Labels come from humans reading the original image, never from model or product code.
- Acceptance scorer is `tests/omr/scorer.py`, authored by the tester; nothing here scores.

Contracts for cm2 adapters: `backend/omr/intent.py` (capo vs key_change, 422 via `IntentError`) and `backend/omr/contract.py` (original-pixel geometry, staff systems with 5 line ys, note events with `"n/d"` rationals). Self-checks: `python -m backend.omr.intent`, `python -m backend.omr.contract`.

Fixtures with refused or unknown rights (GIFTED, 친구야/hey_buddy, user uploads) must not be used.

Machine checks verify shapes, hashes against real file bytes (repo-relative paths only; symlink escapes, `.env`/secret names refused) and role disjointness. They cannot prove rights are genuinely cleared or humans independent; that needs independent review. Cleared register entries carry `license_file`/`asset_file`; the CLI requires them (library default does not).
