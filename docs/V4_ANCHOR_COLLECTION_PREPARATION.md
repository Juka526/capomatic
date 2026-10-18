# V4 anchor collection preparation

The fixed ten-case packet is **TECHNICALLY_READY** for collection. **Zero independent labels exist.** The external roster and separate human annotation sessions remain pending. Technical readiness verifies files and workflow; it does not validate physical anchors, semantic placement, future glyph anchors, rendering, or Full Acceptance.

The canonical instructions and coordinate frame remain the unchanged [frozen protocol](V4_ANCHOR_REFERENCE_PROTOCOL.json), SHA256 `25057996c46ceec83720fe95bc447015002b9bf826e83924e16b8f359181d085`. Background diagnostic evidence remains in [V4_ANCHOR_REFERENCE_VALIDATION.md](V4_ANCHOR_REFERENCE_VALIDATION.md); never distribute either coordinator document to annotators.

## Prepare the actual packet

From the existing Track B checkout, use the standalone offline helper:

```sh
PYTHONPATH=. /private/tmp/capomatic-v4-venv/bin/python scripts/omr_v4/anchor_collection.py prepare \
  --inputs /private/tmp/capomatic-v4-dual-inputs.json \
  --prior-packet validation-b-output/blind-packet \
  --out reference-prep-b-output
```

Output must be new and outside the original evidence and prior output. The helper verifies all 28 shared input hashes before and after preparation, the frozen protocol, and the exact prior `cases.json` hash (`7b56a156b9cc0ba0263fa97ad8738ce4071d9a3219c2116e01db6b21f7f37a4e`). It copies only the ten unchanged PNGs, `cases.json`, allowlisted `instructions.json`, and the original blank A/B forms. It rejects unexpected names, directories, symlinks, modified instructions or nonblank forms. The prepared packet adds only allowlisted `form-instructions.json` explaining the submission format, uncertainty and viewer declaration; all prior packet files remain byte-identical. Every copied PNG has the same file hash, native dimensions, mode and decoded pixels as its original source crop. No reselection or crop rebuild occurs. The source remains historically bound only as described by the shared manifest: OMR does not embed its original input SHA.

`binding.json` binds every packet file, protocol, selection and shared manifest. `readiness.json` records ten cases and zero references at preparation time; it is a preparation snapshot, not a live collection counter. `A/submission.json` and `B/submission.json` are separate editable drafts. The blind packet contains no key, repair labels, semantic predictions, derived targets or collected observations.

## Separate human sessions

A coordinator must recruit two humans competent to read staff notation who were not involved in correction, candidate implementation or this investigation. Verify their roles externally; do not disclose the hypothesis or selection mixture. Record the roster and independence checks outside the distributed packet. No messages are sent by this helper.

Give each annotator only `blind-packet/` and that annotator's own draft, copied into a separate session with no access to the other session. The shared local tree does not enforce role access or human independence. Keep the coordinator documents, full protocol, original diagnostic outputs, binding/readiness files, opposite draft, frozen exports and receipts away from each annotator. Archive receipt hashes through an independently controlled channel. Read-only file permissions and local checksums prevent accidental overwrite and detect ordinary edits; a person controlling both an export and its receipt can replace both. This is a local integrity workflow, not identity authentication or a cryptographic signature service.

Before marking, each annotator establishes the viewer convention from its documentation or a known pixel probe at native resolution, then records that convention. If it cannot be established, stop before marking. Native raster coordinates use x right, y down, with first sample center `(0,0)` and half-open crop bounds. An index-center viewer uses `page=local+crop_origin`; an outer-edge pointer uses `page=local-0.5+crop_origin`. At local `(0,0)` in the first convention and `(0.5,0.5)` in the second, the same page coordinate is the crop origin. No resampling, pixel edits or posthoc ±0.5 correction is allowed.

The physical pivot field means the independently observed plausible center of the visible oval head body after separating stem/ledger strokes where possible. It remains distinct from semantic pitch, OMR box center, persisted pivot and the **UNDEFINED_NOT_RENDERED** future replacement-glyph anchor. Never infer visual truth from semantic pitch or snap observations to a staff grid. Preserve unresolved head identity, clipping, blur and inseparable overlaps.

## Fill and sign a submission

Keep every existing field and all ten case IDs in their existing order. Set top-level `status` to `SIGNED_INDEPENDENT_OBSERVATION`, fill `signer` with the externally verified identity, fill timezone-bearing ISO-8601 `signed_at`, and set `independence_attestation` to `true` only after independently observing the source without candidate results or the other labels. Retain `protocol_sha256`, `binding_sha256` and `annotator`. Each case requires `annotator_signed_at` and a nonempty `uncertainty_and_visibility_reason`.

All coordinates are continuous **page pixel-index-center coordinates**, never local viewer coordinates. An interval is a finite ordered two-number array `[low, high]`; point intervals are permitted. Geometry fields use these JSON shapes:

| Field | Shape |
| --- | --- |
| `middle_staff_polyline_page`, `bottom_staff_polyline_page` | Two or more `{"x_interval":[low,high],"y_interval":[low,high]}` points, ordered with each x interval high strictly below the next x interval low |
| `head_body_bounds_page` | `{"left":[low,high],"top":[low,high],"right":[low,high],"bottom":[low,high]}`; left high < right low and top high < bottom low |
| `physical_pivot_xy_intervals_page` | `{"x":[low,high],"y":[low,high]}` |
| `ledger_centerlines_and_y_intervals_page` | List of polylines in the same interval-point format; `[]` means observed no associated ledger |
| `viewer_coordinate_convention_and_conversion` | `{"convention":"pixel-index-center","conversion":"page=local+crop_origin","declared_before_marking":true}` or `{"convention":"outer-pixel-edge","conversion":"page=local-0.5+crop_origin","declared_before_marking":true}` |

Any geometry field may remain `null`; provide a nonempty `unresolved_reason` identifying the unknown features and reasons. An entirely unknown case or submission is valid when explicitly observed, explained and signed. An all-empty unsigned template cannot freeze. For fully observed cases, `unresolved_reason` may be `null`. Record uncertainty for line, body and ledger observations through the intervals and explanations. These format requirements implement the frozen reference fields; they introduce no acceptance threshold.

## Freeze, then compare or adjudicate

The coordinator handles each signed export separately. For example, after receiving A's export in its own session:

```sh
PYTHONPATH=. /private/tmp/capomatic-v4-venv/bin/python scripts/omr_v4/anchor_collection.py freeze \
  --out reference-prep-b-output --role A --submission reference-prep-b-output/A/submission.json
```

Repeat with role B and B's own file after its independent session. Freeze validates field allowlists, every case, signatures, protocol/packet binding, finite ordered intervals, reasons and declared conversion. It preserves submitted bytes as `A/frozen.json` or `B/frozen.json`, creates a SHA256 `receipt.json`, sets both read-only and refuses replacement. Check and archive the returned receipt externally before revealing anything. A and B must have distinct signer identities; the comparison gate checks this, but external identity and eligibility checks remain mandatory.

Only after **both** freezes:

```sh
PYTHONPATH=. /private/tmp/capomatic-v4-venv/bin/python scripts/omr_v4/anchor_collection.py compare \
  --out reference-prep-b-output
```

Comparison verifies both receipts, exports and packet binding. It returns both observations, frozen primary hashes and the geometry fields that differ. This is a field-level disagreement inventory, not a numerical error score or agreement threshold. It never fabricates consensus, drops unknown cases, or supplies candidate-based relabeling. The helper blocks comparison and adjudication before both primaries freeze; ordinary filesystem access still requires coordinator controls.

Adjudication is optional when a coordinator needs a separate resolution of disagreements; equal or entirely unknown observations do not require a fabricated resolution. An independent second-pass human who meets the same competence and noninvolvement screening, and is neither primary annotator, may inspect only the source and both frozen observations. If adjudication is needed, produce a separate JSON envelope with exactly `primary_hashes` (the comparison's A/B mapping), a nonempty `reason`, and `reference`. The reference uses the submission schema above with `annotator: "ADJUDICATOR"`, a third signer, all ten cases and the same binding. Nulls with reasons remain valid; do not force consensus. Freeze this once with:

```sh
PYTHONPATH=. /private/tmp/capomatic-v4-venv/bin/python scripts/omr_v4/anchor_collection.py adjudicate \
  --out reference-prep-b-output --submission /path/to/independent-adjudication.json
```

The new `adjudication.json` preserves both primary exports and records their frozen hashes. A failed validation must be corrected in the unfrozen draft; a frozen primary cannot be edited or silently replaced. If a frozen export is wrong, stop and resolve it through an explicit future protocol decision outside this helper.

## Readiness and remaining work

Actual preparation: ten fixed source crops; zero actual independent annotation exports; external roster pending. The collection tests use synthetic labels only in temporary test directories. They establish parser/workflow behavior, not annotation validity or human independence. This selected single-score sample retains detector-conditioned targeting and cannot establish generalization; broader acceptance needs separately preregistered held-out scores and independent observations under the frozen protocol's limits.

No runtime semantics, planner, offset, guard, API, backend, renderer B2, raster-edit, Full Acceptance, merge or deployment is changed or authorized. No permission for future editing is implied by preparing or collecting these observations.
