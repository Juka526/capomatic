# GT-14C — Complete second-system lyric continuation audit

GT-14C prepares a source-only owner-review packet for **three additional candidate strokes**. It does not render them or alter the confirmed A/G canvases.

Base: `5ff71fa2ec6f4f738fb674d442af2a6960653470`. Branch: `experiment/v4-gt14c-lyric-continuation-audit`. Worktree: `/private/tmp/capomatic-v4-gt14c`. The final revision is the commit containing this report, available with `git rev-parse HEAD` on this branch.

Understood as: inspect both original Korean lyric rows across printed measures 5–8, preserve the three owner-confirmed GT-14B marks and 하 interpretation, and request confirmation only for additional source-visible marks. This audit cannot authorize source edits or promote candidate evidence.

## Source and coverage

Source is the original Bb PDF page 2 raster, 2520×3564 RGB. SHA-256: `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`. Original OMR SHA-256: `857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638`.

Targets remain A major (−1 semitone) and G major (−3 semitones); neither is rendered in this audit. V3 refers to the unchanged recognition/transposition pipeline and its semantic guard.

The entire second system and both full-width lyric strips were visually inspected using source pixels, including spaces between syllables and measures with no newly observed marks. This is an **agent visual census of all eight measure-row regions**, not independent source-completeness proof. No A/G reference page or target-rendered pixels were used to identify the candidates. The full context includes a small portion of the following system's boxed context beneath the m5 lower row; that structural context is not counted as a lyric continuation stroke.

Measure boundaries retained from the frozen registration are m5 x159–639, m6 x639–1598, m7 x1598–1961 and m8 x1961–2397. Source review context is `[130,700,2430,1030)`. Full lyric strips are `[159,925,2397,970)` and `[159,970,2397,1016)`. No rotation, scaling, binarized replacement image or target overlay is applied to any source crop.

## Two-row continuation inventory

All coordinates are original-page pixel edges; right and bottom are exclusive. For existing marks, bbox values remain original persisted OMR geometry. New candidate boxes are measured dark-support envelopes (`L<127`) inside separately inspected native windows. Their surrounding antialias extent is **not** claimed as exact owned ink. The complete unthresholded review crop is retained alongside each measurement.

| Measure | Row | Stroke ID | Source bbox | Associated held syllable | Context | Evidence |
|---|---|---|---|---|---|---|
| 5 | upper | GT14C-m5-upper | [298,942,335,947) | 곳 from m4 onset 3.75 — candidate association | Bb3 whole note at onset 0, tie STOP; incoming 4798 / outgoing 4818 | AGENT_VISUAL_CANDIDATE |
| 5 | lower | sheet#1:5686 | [298,987,335,993) | 는 from m4 onset 3.75 | Same confirmed cross-system tie | OWNER_VERIFIED_SOURCE |
| 6 | upper | sheet#1:5699 | [1330,942,1368,948) | 원 from onset 2.75 | C4 at onset 3, duration 0.25, tie STOP; curve 4784 | OWNER_VERIFIED_SOURCE |
| 6 | lower | GT14C-m6-lower | [1331,987,1367,992) | 운 from onset 2.75 — candidate association | Same held C4/tie context | AGENT_VISUAL_CANDIDATE |
| 7 | upper | sheet#1:5762 | [1620,942,1658,948) | 네 from m6 onset 3.75 | Bb3 whole note at onset 0, tie STOP; curve 4772 | OWNER_VERIFIED_SOURCE |
| 7 | lower | GT14C-m7-lower | [1621,987,1657,992) | 길 from m6 onset 3.75 — candidate association | Same held Bb3/tie context | AGENT_VISUAL_CANDIDATE |
| 8 | both | none newly observed | — | — | Confirmed whole-measure rest, first ending/backward repeat | AGENT_VISUAL_ABSENCE_OBSERVATION, not independent proof |

The six stroke locations were each inspected in the original raster. The new upper-m5, lower-m6 and lower-m7 windows were independently selected at their visible source locations; no confirmed alpha mask was copied, mirrored or translated into the other row. Their dark-support counts are 88, 91 and 92 pixels respectively; these are measurement counts, not ownership or text-ground-truth denominators.

Confirmed syllables and same-pitch START/STOP events corroborate musical context, but do not themselves establish the new visible stroke's role. Both the stroke classification and its syllable association remain pending owner confirmation. There are **3 preserved owner-confirmed marks + 3 agent candidates**, not 6 confirmed extenders.

The original `sheet#1:5747` FERMATA_BELOW observation remains unchanged in raw OMR. GT-14B's owner-confirmed interpretation as a stroke of existing upper 하 at m6 onset 3.25 is preserved, excluded from the extender count, and does not create a new syllable or glyph.

## OMR limitations

The measured new upper-m5 and lower-m7 boxes have no intersecting serialized Inter bbox. Lower-m6 intersects only the broad Direction sentence `sheet#1:4179`, bbox `[1250,929,1449,1011)`. That spatial intersection does not establish recognition of the continuation mark, source-pixel ownership, or a musical attachment. The inventory retains intersecting original objects and exact persisted tie XML/relations without rewriting them.

## Owner-review packet

Final artifacts are untracked in `/private/tmp/capomatic-v4-gt14c/gt14c-final-output/`:

- `source-two-row-extender-review.png`: full source system, both complete lyric strips, and three native source context crops; labels are outside source tiles.
- `source-second-system-native.png`, `source-row-1-native.png`, `source-row-2-native.png`: untouched native source crops.
- `GT14C-m5-upper-native.png`, `GT14C-m6-lower-native.png`, `GT14C-m7-lower-native.png`: candidate context crops.
- `lyric-continuation-inventory.json`: all six marks, four preserved GT-14B interpretations, eight-region census, source/semantic context and crop SHA-256 bindings.
- `owner-review-checklist.json`: only the three new candidates; separate stroke-existence, row and syllable-association answers, corrections and uncertainty.
- `validation-summary.json`, `semantic-integrity.json`, `input-preservation.json`, `audit-freeze.json`.

Owner responses remain null. Accepted response categories are OWNER_CONFIRMED, OWNER_REJECTED and OWNER_UNCERTAIN. Existing approved strings, associations and three confirmed extenders are not submitted for duplicate confirmation. No new approval message, signature, timestamp or independent label was manufactured. The packet is an owner review of disclosed candidates, **not a blinded independent annotation protocol**.

Native images retain the source mode, dimensions and exact RGB bytes at their recorded crop-to-page offsets. The assembled review sheet uses only integer translation of native source tiles; it contains no predictions. It has been opened and visually checked. A browser/image viewer may display it scaled, so use the standalone native crops for pixel-coordinate review.

Reproduction using the existing local artifacts (fresh output path required):

```bash
cd /private/tmp/capomatic-v4-gt14c
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt14c_continuation_audit \
  --out /private/tmp/capomatic-v4-gt14c/gt14c-repeat-output
```

The earlier `gt14c-output/` is a separate development packet; the final report refers exclusively to `gt14c-final-output/`.

## Validation and separate completion outcomes

- **Source inventory coverage:** all eight measure-row regions inspected by the agent; three owner-confirmed strokes and three agent-observed candidate strokes enumerated. Independent completeness remains UNVERIFIED; three new source interpretations await the owner.
- **Renderer completeness:** unchanged GT-14B scoped layer; the 3 confirmed extenders remain rendered and **0 of the 3 candidates are rendered**. The inventory’s six observed locations are an agent census, not an accepted rendering or accuracy denominator. This is not a complete second-system lyric-continuation render.
- **Confirmed content consistency:** 13 note/rest events, 3 chords (Gm, Bb/D, Eb), 14 Korean syllables and existing tie/syllable signatures preserved.
- **Semantic guards:** unchanged V3 source roundtrip and A/G in-memory transposition plus frozen serialized MusicXML checks PASS. Event ordering, voice, duration, pitch and tie signatures match the frozen targets. These are pipeline consistency checks, not source recognition truth.
- **Tests:** 414 passed, 1 skipped (existing external MuseScore dependency), including 10 new source-audit tests. Tests cover bounded measurement, antialias uncertainty, pending classifications, failed lineage, exact crop/page mapping, eight-region census, no inferred complementary records and deterministic JSON.
- **Preservation:** original source, hash-bound OMR/graph/review evidence, GT-14A full artifact directory and GT-14B full artifact directory/prediction freeze verified unchanged. Frozen GT-12 and recorded upstream directory bindings are separately checked. No GT-14B masks or predictions were regenerated. `git diff --check` passes.

The agent generated and checked this candidate inventory; automated measurements cannot independently confirm those classifications. Separate owner responses are the next evidence step, and remain owner evidence rather than independent ground truth.

No source ink removal, original lyric-pixel composition, protection-mask change, production/API/frontend modification, ownership promotion, merge or deployment occurred. No copyrighted source images or large outputs are committed.

**Stop state: SOURCE_AUDIT_AND_OWNER_PACKET_READY.** Next action is owner review of the three new candidate strokes and their proposed associations. Independent source completeness remains unverified beyond that review; a confirmed note, tie or lyric string alone does not confirm the new stroke. No new extender rendering is authorized by this audit.

Report quality check: a fresh-context wording review identified possible confusion between a six-location agent census and six confirmed rendering targets. The report explicitly separates the three confirmed marks from three pending candidates. This check did not supply source labels or optical validation. Historical GT-14B classifications remain canonical for approved marks; the GT-14C protocol defines only the new candidate windows. No historical records were consolidated or rewritten.
