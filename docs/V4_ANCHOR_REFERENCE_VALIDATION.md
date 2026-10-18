# V4 independent anchor reference validation

Status: **PENDING_INDEPENDENT_ANNOTATION**, zero independent references. This is a diagnostic decomposition and a frozen collection protocol, not a geometry acceptance result. No runtime planner, matcher, transposer, guard, renderer or raster-edit behavior changes.

## What the 7.40 px discrepancy means

The old relative plan starts at the detected head's geometry center and adds the displacement between **corrected** source semantics and target semantics. For `p1:m0:n1` and `p1:m0:n2`, unchanged `read_semantics` reports raw D4 staff position 5, corrected C4 position 6, target Bb3 position 7. The persisted treble clef and original middle staff line define the semantic reference; positive positions go down from the middle line. Interline is 21.3 px.

At x=355 (also x=402), the middle line is y=501.5. Raw D4 ideal y=554.75; detected bbox center y=558; corrected C4 ideal y=565.4; target Bb3 ideal y=576.05. The relative target is 558+10.65=568.65. Thus:

`absolute_target − old_target = corrected_source_ideal − detected_center = (565.4−554.75) − (558−554.75) = 10.65−3.25 = 7.40 px`.

The discrepancy combines the semantic repair shift with the residual of the raw recognition anchor. It is not simply a one-step staff correction, proof of a physical notehead pivot, or an edit-mask displacement. Both targets are candidates until independently checked.

All five historical repairs have the same semantic sequence D4→C4→Bb3 (staff positions 5→6→7), but local staff geometry differs:

| Semantic ID | Detected x,y | Interline | Middle y at x | Raw ideal y | Corrected ideal y | Absolute target y | Old target y | Absolute−old px |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| p1:m0:n1 | 355,558 | 21.3 | 501.5 | 554.75 | 565.4 | 576.05 | 568.65 | 7.40 |
| p1:m0:n2 | 402,558 | 21.3 | 501.5 | 554.75 | 565.4 | 576.05 | 568.65 | 7.40 |
| p1:m8:n0 | 256,1326 | 21.25 | 1269.5 | 1322.625 | 1333.25 | 1343.875 | 1336.625 | 7.25 |
| p1:m15:n0 | 2027,1710 | 21.25 | 1653.5 | 1706.625 | 1717.25 | 1727.875 | 1720.625 | 7.25 |
| p1:m24:n0 | 256,2862 | 21.3125 | 2805.592527 | 2858.873777 | 2869.530027 | 2880.186277 | 2872.65625 | 7.530027 |

The last middle line is interpolated at the head's x on the original sloped polyline. This diagnostic reuses the graph's staff-wide interline, not a newly fitted local spacing. Bottom-line y values are 544,544,1312,1696,2848 respectively. Independent staff-line annotations must test both the polyline and the spacing assumption.

## Distinct anchors and evidence

All five detected boxes are 26×24 px. No head pivot is persisted for any of them, so `Geometry.center` falls back to the bbox center. Exact persisted glyph support has the same bounds as each detected box:

| Head ID suffix | Detected/support bounds, half-open | Persisted glyph pixels | Glyph-run centroid x,y |
| --- | --- | --- | --- |
| 2334 | 342,546,368,570 | 344 | 355.337209,560.523256 |
| 2335 | 389,546,415,570 | 344 | 402.389535,560.517442 |
| 2602 | 243,1314,269,1338 | 346 | 256.381503,1328.488439 |
| 2748 | 2014,1698,2040,1722 | 348 | 2027.396552,1712.428161 |
| 3124 | 243,2850,269,2874 | 342 | 256.380117,2864.549708 |

These centroids average integer raster pixel indices. The Audiveris bbox center is computed as left+width/2,top+height/2 from its integer half-open metadata. Those are different estimators with potentially different half-pixel conventions; neither is automatically an interchangeable placement anchor. They are not physical head-body or pivot references. For example, the first glyph centroid is y=560.523256, distinct from both bbox center 558 and corrected semantic ideal 565.4. Persisted glyph attribution can include or omit material around ledger/stem joins. No physical pivot, ledger center or masking truth is inferred here, and no new source ownership is assigned.

Keep four claims separate: the detected bbox center is an observation of an OMR box; semantic staff pitch is the written pitch interpreted with clef state; the absolute target is a candidate staff coordinate; a replacement glyph needs its own declared placement anchor. The last is **UNDEFINED_NOT_RENDERED**. Raw support bounds alone do not supply that future glyph contract.

## Frozen independent annotation protocol

The coordinator's canonical protocol is [V4_ANCHOR_REFERENCE_PROTOCOL.json](V4_ANCHOR_REFERENCE_PROTOCOL.json), frozen by [its SHA256](V4_ANCHOR_REFERENCE_PROTOCOL.sha256): `25057996c46ceec83720fe95bc447015002b9bf826e83924e16b8f359181d085`. The small [five-note decomposition fixture](V4_ANCHOR_REFERENCE_DECOMPOSITION.json) is explicitly derived diagnostic evidence, not a reference label set.

MATCHED refers to the unchanged existing plan status; the controls are not claimed comparable in morphology or difficulty. The selection is fixed before external annotation: all five historical repairs plus five MATCHED nonrepair controls ranked by a fixed SHA256 of semantic identity. No coordinate outcome or error is used. Cases are mixed into opaque case numbers. Source crops preserve native untouched pixels, record half-open page bounds and source/crop hashes, and retain enough staff/ledger context for observations. There is no scaling, line overlay, expected coordinate or label on the images. The annotation frame places the first pixel sample center at (0,0). Annotators record their viewer convention before marking: an edge-origin pointer uses page=local−0.5+crop origin; an index-center viewer uses page=local+crop origin. No posthoc half-pixel adjustment is permitted.

Give two independent human annotators only `validation-b-output/blind-packet/`, in separate sessions. It contains source-only crops, native-coordinate manifests, allowlisted instructions and separate empty A/B forms. **Do not give them this report, the full protocol, decomposition fixture, hidden solution key, candidate coordinates, repair status or selection recipe.** Each marks observed middle/bottom staff polylines, physical head-body bounds, plausible pivot intervals, visible ledger centerlines with uncertainty, and unresolved/occluded features. The physical pivot range is operationally a plausible center of the visible oval body after distinguishing attached strokes; it is not a software pivot or a future glyph anchor. Clipped or inseparable bodies remain unresolved. Target identity is detector-conditioned by horizontal crop centering, so reference independence is limited to candidate-blinded observations within this selected region. Neither sees the other's labels or any candidate result before both signed exports are locked and hashed. Preserve original labels through any later independent adjudication.

Once locked, compare each candidate against each annotator's intervals, report signed errors and disagreement for every fixed case, and preserve unknowns. No threshold or acceptance rule is introduced. Do not relabel against the candidate formula. Formula replay and glyph centroid agreement cannot establish independence. This avoids the circular scorer/designer check; the remaining jayu-only sample bias requires a separately preregistered held-out score set before broader acceptance.

## Reproduce and interpret

From the repository root:

```sh
PYTHONPATH=. /private/tmp/capomatic-v4-venv/bin/python scripts/omr_v4/anchor_reference_validation.py \
  --inputs /private/tmp/capomatic-v4-dual-inputs.json \
  --out /private/tmp/capomatic-v4-validation-b/validation-b-output
```

Output must be new or empty and outside the immutable evidence tree. The shared 28-file manifest is verified before and after. Source dimensions bind the crop coordinate frame; source and crop hashes bind the selected pixels. The manifest's historical limitation remains: OMR does not embed the original input SHA, so current artifact binding does not establish historical input identity. The original worktrees and prior Track B outputs remain read-only.

`derived-candidate-coordinates.json` records full staff polylines, persisted clef XML, raw/corrected/target semantic events, bbox center, optional persisted pivot, support bounds and centroid, and the algebraic residuals. `hidden-solution-key.json` maps opaque cases to IDs and groups; keep both outside the blind packet. `verification.json` records hashes and pending reference status. The generated packet contains ten cases, not ten validated anchors.

## Next implementation, conditional on evidence

Collect the two blinded annotation sets first. If independent line observations support the staff geometry and physical observations support corrected semantic staff placement, implement an explicit semantic staff-coordinate target with a separately specified replacement-glyph anchor, then validate their correspondence and uncertainty on held-out scores. If staff geometry is unsupported, address that evidence gap first. If physical pivot ranges remain ambiguous, preserve uncertainty and gather better source/reference evidence; do not tune a y offset to these five notes.

This task selects no architecture winner. Source-to-target correspondence, glyph placement, erase ownership, beam/slur layout and actual rendered collisions remain separate unvalidated requirements. No rendering, erase mask, Audiveris rerun, Docker run or Full Acceptance was performed.
