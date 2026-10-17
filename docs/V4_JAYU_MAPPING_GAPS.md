# V4 Phase 1.6: jayu mapping gap audit

**Decision: READY_FOR_MATCHER_FIX. Phase 2 remains unauthorized.**

Analyzed commit: `c044a675ef32b108dce010da7e0aa452c97abc61`, branch
`feature/score-v4-layout-preserve`. Inputs are the existing
`v4-jayu-diagnostic-retry/` artifacts. No Audiveris run, new matching result,
matcher/parser policy change, pixel erasure, replacement rendering, font, runtime
route, merge or deployment was performed in this pass.

The result remains **244 MATCHED, 0 AMBIGUOUS, 5 UNMATCHED** out of 249 semantic
notes and 249 heads. The audit's orange candidate markers are evidence for human
review; they do not promote any original UNMATCHED result.

## Findings and provenance

All five failures have primary classification **B: head exists but staff-pitch
differs**, confidence **HIGH**. Each raw Audiveris note is **D4**, with a unique
head at staff pitch **+5**, and a unique nonsuspicious BEGIN at the correct part,
measure, staff and offset. V3's unchanged `cleanup.fix_missed_ledgers()` changes
that semantic D4 to C4 when its existing pixel check detects a missed ledger. V4
then matches the **corrected** MusicXML (expected staff pitch **+6**) against the
**uncorrected** SIG pitch **+5**, without carrying per-note repair provenance.

This is not a missing head, missing BEGIN, dropped SIG relation, duplicate/unison,
split measure, hidden/grace note, or staff-lineage failure. All five are visibly
printed middle C on a ledger in the source crops. The same V3 `_has_ledger`
predicate returns true for all five on the existing source raster. The report
records `ledger_notes_fixed: 5`. No corresponding ledger symbol is retained at
these five head x positions: the pixel evidence exists despite Audiveris missing
the ledger segmentation. There is no serialized ledger-head edge to recover.

This explains the identity gap; it does not establish a final glyph pivot or safe
future edit mask. In particular, these heads' OCR bounds/centers are affected by
the ledger recognition error and must not be silently snapped or normalized.

| Gap | Semantic ID | Measure @ quarter offset | Duration | Head / chord | SIG staff | Grade / ctx | Primary cause | Pairing |
|---|---|---|---|---|---|---|---|---|
| 1 | `p1:m0:n1` | 1 @ 1/2 | 1/4 | 2334 / 6928 | sheet#1:1 | 0.196 / 0.572 | B / HIGH | OBVIOUS_COUNTERPART |
| 2 | `p1:m0:n2` | 1 @ 3/4 | 1/4 | 2335 / 6929 | sheet#1:1 | 0.196 / 0.603 | B / HIGH | OBVIOUS_COUNTERPART |
| 3 | `p1:m8:n0` | 9 @ 0 | 1 | 2602 / 7001 | sheet#1:3 | 0.203 / 0.57 | B / HIGH | OBVIOUS_COUNTERPART |
| 4 | `p1:m15:n0` | 16 @ 3/2 | 1/2 | 2748 / 7057 | sheet#1:4 | 0.206 / 0.577 | B / HIGH | OBVIOUS_COUNTERPART |
| 5 | `p1:m24:n0` | 25 @ 0 | 1/4 | 3124 / 7101 | sheet#1:7 | 0.19 / 0.591 | B / HIGH | OBVIOUS_COUNTERPART |

Each event has semantic part 1, staff number 1, voice **absent/null** in recognized
MusicXML, written pitch **C4**, expected staff pitch **+6**, singleton chord size 1
and member index 0. The visual staff IDs are page-global (1, 3, 4, 7), whereas the
semantic staff number 1 is local to part 1. That difference is correctly resolved
by the graph; the visual BEGIN voice is 1, but voice is advisory in the matcher.

## Exhaustive candidate audit

The structured file is
`v4-jayu-diagnostic-retry/gaps/candidate-audit.json`. It enumerates **42 candidate
rows**, including all same-measure/same-staff heads before pitch filtering, full
bounds, exact slot-region intervals, raw BEGIN/CONTINUE values, parent/membership,
original match ownership, independent checks and attachment relation payloads.
The two measure-1 gaps intentionally repeat their common pool; there are 32
unique candidate heads. No candidate is chosen by Euclidean proximity, grade or
matching unmatched counts.

Tables below retain all candidates. `B slot@offset/v1` means a unique BEGIN in
voice 1, suspicious=false; **none of these candidates has CONTINUE evidence**.
`P` = staff-pitch rejection, `T` = onset rejection. All other audited static checks
pass: unique measure, explicit measure membership, unique parent/BEGIN, usable
slot/geometry, matching singleton chord size and correct staff/part. Where T fails,
the current matcher short-circuits at that onset check; P is also shown as an
independent fact rather than hidden behind the first rejection. For the exact
onset counterpart, P is the sole rejection, and the full chord staff-pitch tuple
also disagrees for the same reason. Grades never decide ownership.

Relations use `S` stem, `B` beam/hook and `C` slur/tie IDs, all prefixed `sheet#1:`.
Containment head-chord IDs are explicit in each row. Ledger candidates here are
x-overlap evidence, **not** a manufactured head-ledger relation. Full relation
attributes and source/target IDs are in JSON.

### Gap 1: `p1:m0:n1`

Measure `sheet#1:system:1:part:1:measure:1`; bounds `[83.0, 458.6, 794.0, 544.0]`; exact-slot x region `[327.5, 377.5]`. Chord `p1:m0:e1`, size 1.

| Head | Center x,y | Bbox x1,y1,x2,y2 | Pitch | Grade/ctx | Parent chord | Slot evidence | S / B / C / ledger candidates | Reject | Existing semantic owner |
|---|---|---|---:|---|---|---|---|---|---|
| 2303 | [302.0, 565.5] | [288.0, 554.0, 316.0, 577.0] | 6.0 | 0.706/0.931 | 6927 | BEGIN 1@0/v1 | S 3727; B 1486; C none; L sheet#1:1801 | T | p1:m0:n0 |
| 2334 | [355.0, 558.0] | [342.0, 546.0, 368.0, 570.0] | 5.0 | 0.196/0.572 | 6928 | BEGIN 2@1/2/v1 | S 3742; B 1486,1492; C none; L none | P | unowned |
| 2335 | [402.0, 558.0] | [389.0, 546.0, 415.0, 570.0] | 5.0 | 0.196/0.603 | 6929 | BEGIN 3@3/4/v1 | S 3728; B 1486,1492; C 7225; L none | T,P | unowned |
| 2307 | [448.0, 565.5] | [434.0, 554.0, 462.0, 577.0] | 6.0 | 0.708/0.953 | 6930 | BEGIN 4@1/v1 | S 3731; B 1444; C 7225; L sheet#1:1807 | T | p1:m0:n3 |
| 2171 | [499.5, 512.0] | [485.0, 500.0, 514.0, 524.0] | 1.0 | 0.793/0.955 | 6931 | BEGIN 5@3/2/v1 | S 3745; B 1444,1456; C none; L none | T,P | p1:m0:n4 |
| 2175 | [543.5, 512.0] | [529.0, 500.0, 558.0, 524.0] | 1.0 | 0.768/0.955 | 6932 | BEGIN 6@7/4/v1 | S 3732; B 1444,1456; C 7265; L none | T,P | p1:m0:n5 |
| 2177 | [588.0, 512.0] | [574.0, 500.0, 602.0, 524.0] | 1.0 | 0.776/0.953 | 6933 | BEGIN 7@2/v1 | S 3729; B 1446; C 7265; L none | T,P | p1:m0:n6 |
| 2205 | [639.5, 523.0] | [625.0, 511.0, 654.0, 535.0] | 2.0 | 0.754/0.95 | 6934 | BEGIN 8@5/2/v1 | S 3746; B 1446,1470; C none; L none | T,P | p1:m0:n7 |
| 2209 | [684.5, 523.0] | [670.0, 511.0, 699.0, 535.0] | 2.0 | 0.744/0.951 | 6935 | BEGIN 9@11/4/v1 | S 3730; B 1446,1470; C 7324; L none | T,P | p1:m0:n8 |
| 2213 | [728.5, 523.0] | [714.0, 511.0, 743.0, 535.0] | 2.0 | 0.739/0.936 | 6936 | BEGIN 10@3/v1 | S 3758; B none; C 7324; L none | T,P | p1:m0:n9 |

**B / HIGH; OBVIOUS_COUNTERPART = sheet#1:2334.** The raw D4 and corrected C4 share the exact onset and duration; only the semantic pitch changes. Both note event and head/chord exist. The slot join and raw semantic pitch provide independent evidence, not count-based pairing.

Crop: `v4-jayu-diagnostic-retry/gaps/gap-01.png` (untouched source panel beside annotation panel).

### Gap 2: `p1:m0:n2`

Measure `sheet#1:system:1:part:1:measure:1`; bounds `[83.0, 458.6, 794.0, 544.0]`; exact-slot x region `[377.5, 424.0]`. Chord `p1:m0:e2`, size 1.

| Head | Center x,y | Bbox x1,y1,x2,y2 | Pitch | Grade/ctx | Parent chord | Slot evidence | S / B / C / ledger candidates | Reject | Existing semantic owner |
|---|---|---|---:|---|---|---|---|---|---|
| 2303 | [302.0, 565.5] | [288.0, 554.0, 316.0, 577.0] | 6.0 | 0.706/0.931 | 6927 | BEGIN 1@0/v1 | S 3727; B 1486; C none; L sheet#1:1801 | T | p1:m0:n0 |
| 2334 | [355.0, 558.0] | [342.0, 546.0, 368.0, 570.0] | 5.0 | 0.196/0.572 | 6928 | BEGIN 2@1/2/v1 | S 3742; B 1486,1492; C none; L none | T,P | unowned |
| 2335 | [402.0, 558.0] | [389.0, 546.0, 415.0, 570.0] | 5.0 | 0.196/0.603 | 6929 | BEGIN 3@3/4/v1 | S 3728; B 1486,1492; C 7225; L none | P | unowned |
| 2307 | [448.0, 565.5] | [434.0, 554.0, 462.0, 577.0] | 6.0 | 0.708/0.953 | 6930 | BEGIN 4@1/v1 | S 3731; B 1444; C 7225; L sheet#1:1807 | T | p1:m0:n3 |
| 2171 | [499.5, 512.0] | [485.0, 500.0, 514.0, 524.0] | 1.0 | 0.793/0.955 | 6931 | BEGIN 5@3/2/v1 | S 3745; B 1444,1456; C none; L none | T,P | p1:m0:n4 |
| 2175 | [543.5, 512.0] | [529.0, 500.0, 558.0, 524.0] | 1.0 | 0.768/0.955 | 6932 | BEGIN 6@7/4/v1 | S 3732; B 1444,1456; C 7265; L none | T,P | p1:m0:n5 |
| 2177 | [588.0, 512.0] | [574.0, 500.0, 602.0, 524.0] | 1.0 | 0.776/0.953 | 6933 | BEGIN 7@2/v1 | S 3729; B 1446; C 7265; L none | T,P | p1:m0:n6 |
| 2205 | [639.5, 523.0] | [625.0, 511.0, 654.0, 535.0] | 2.0 | 0.754/0.95 | 6934 | BEGIN 8@5/2/v1 | S 3746; B 1446,1470; C none; L none | T,P | p1:m0:n7 |
| 2209 | [684.5, 523.0] | [670.0, 511.0, 699.0, 535.0] | 2.0 | 0.744/0.951 | 6935 | BEGIN 9@11/4/v1 | S 3730; B 1446,1470; C 7324; L none | T,P | p1:m0:n8 |
| 2213 | [728.5, 523.0] | [714.0, 511.0, 743.0, 535.0] | 2.0 | 0.739/0.936 | 6936 | BEGIN 10@3/v1 | S 3758; B none; C 7324; L none | T,P | p1:m0:n9 |

**B / HIGH; OBVIOUS_COUNTERPART = sheet#1:2335.** The raw D4 and corrected C4 share the exact onset and duration; only the semantic pitch changes. Both note event and head/chord exist. The slot join and raw semantic pitch provide independent evidence, not count-based pairing.

Crop: `v4-jayu-diagnostic-retry/gaps/gap-02.png` (untouched source panel beside annotation panel).

### Gap 3: `p1:m8:n0`

Measure `sheet#1:system:3:part:1:measure:9`; bounds `[83.0, 1227.0, 822.0, 1312.0]`; exact-slot x region `[169.0, 316.0]`. Chord `p1:m8:e0`, size 1.

| Head | Center x,y | Bbox x1,y1,x2,y2 | Pitch | Grade/ctx | Parent chord | Slot evidence | S / B / C / ledger candidates | Reject | Existing semantic owner |
|---|---|---|---:|---|---|---|---|---|---|
| 2602 | [256.0, 1326.0] | [243.0, 1314.0, 269.0, 1338.0] | 5.0 | 0.203/0.57 | 7001 | BEGIN 1@0/v1 | S 4517; B none; C none; L none | P | unowned |
| 2488 | [378.5, 1259.0] | [364.0, 1247.0, 393.0, 1271.0] | -1.0 | 0.783/0.946 | 7002 | BEGIN 2@1/v1 | S 4512; B none; C none; L none | T,P | p1:m8:n1 |
| 2490 | [502.5, 1259.0] | [488.0, 1247.0, 517.0, 1271.0] | -1.0 | 0.774/0.955 | 7003 | BEGIN 3@2/v1 | S 4490; B 1583; C none; L none | T,P | p1:m8:n2 |
| 2498 | [585.5, 1269.5] | [571.0, 1258.0, 600.0, 1281.0] | 0.0 | 0.748/0.933 | 7004 | BEGIN 4@5/2/v1 | S 4506; B 1583; C none; L none | T,P | p1:m8:n3 |
| 2512 | [668.5, 1280.0] | [654.0, 1268.0, 683.0, 1292.0] | 1.0 | 0.792/0.94 | 7005 | BEGIN 5@3/v1 | S 4507; B 1583; C none; L none | T,P | p1:m8:n4 |
| 2514 | [751.0, 1280.0] | [737.0, 1268.0, 765.0, 1292.0] | 1.0 | 0.78/0.944 | 7006 | BEGIN 6@7/2/v1 | S 4491; B 1583; C 7206; L none | T,P | p1:m8:n5 |

**B / HIGH; OBVIOUS_COUNTERPART = sheet#1:2602.** The raw D4 and corrected C4 share the exact onset and duration; only the semantic pitch changes. Both note event and head/chord exist. The slot join and raw semantic pitch provide independent evidence, not count-based pairing.

Crop: `v4-jayu-diagnostic-retry/gaps/gap-03.png` (untouched source panel beside annotation panel).

### Gap 4: `p1:m15:n0`

Measure `sheet#1:system:4:part:1:measure:16`; bounds `[1841.0, 1611.0, 2398.0, 1696.0]`; exact-slot x region `[1953.0, 2063.5]`. Chord `p1:m15:e0`, size 1.

| Head | Center x,y | Bbox x1,y1,x2,y2 | Pitch | Grade/ctx | Parent chord | Slot evidence | S / B / C / ledger candidates | Reject | Existing semantic owner |
|---|---|---|---:|---|---|---|---|---|---|
| 2748 | [2027.0, 1710.0] | [2014.0, 1698.0, 2040.0, 1722.0] | 5.0 | 0.206/0.577 | 7057 | BEGIN 2@3/2/v1 | S 4917; B none; C none; L none | P | unowned |
| 2656 | [2100.5, 1664.0] | [2086.0, 1652.0, 2115.0, 1676.0] | 1.0 | 0.796/0.957 | 7058 | BEGIN 3@2/v1 | S 4885; B 1610; C none; L none | T,P | p1:m15:n1 |
| 2626 | [2175.0, 1653.5] | [2161.0, 1642.0, 2189.0, 1665.0] | 0.0 | 0.717/0.92 | 7059 | BEGIN 4@5/2/v1 | S 4909; B 1610; C none; L none | T,P | p1:m15:n2 |
| 2711 | [2250.0, 1696.0] | [2236.0, 1684.0, 2264.0, 1708.0] | 4.0 | 0.752/0.954 | 7060 | BEGIN 5@3/v1 | S 4910; B 1610; C none; L none | T,P | p1:m15:n3 |
| 2693 | [2324.5, 1686.0] | [2310.0, 1674.0, 2339.0, 1698.0] | 3.0 | 0.783/0.961 | 7061 | BEGIN 6@7/2/v1 | S 4886; B 1610; C 7209; L none | T,P | p1:m15:n4 |

**B / HIGH; OBVIOUS_COUNTERPART = sheet#1:2748.** The raw D4 and corrected C4 share the exact onset and duration; only the semantic pitch changes. Both note event and head/chord exist. The slot join and raw semantic pitch provide independent evidence, not count-based pairing.

Crop: `v4-jayu-diagnostic-retry/gaps/gap-04.png` (untouched source panel beside annotation panel).

### Gap 5: `p1:m24:n0`

Measure `sheet#1:system:7:part:1:measure:25`; bounds `[83.0, 2762.5, 780.0, 2848.0]`; exact-slot x region `[169.0, 278.0]`. Chord `p1:m24:e0`, size 1.

| Head | Center x,y | Bbox x1,y1,x2,y2 | Pitch | Grade/ctx | Parent chord | Slot evidence | S / B / C / ledger candidates | Reject | Existing semantic owner |
|---|---|---|---:|---|---|---|---|---|---|
| 3124 | [256.0, 2862.0] | [243.0, 2850.0, 269.0, 2874.0] | 5.0 | 0.19/0.591 | 7101 | BEGIN 1@0/v1 | S 5778; B 1723,1729; C none; L none | P | unowned |
| 3101 | [302.0, 2869.5] | [288.0, 2858.0, 316.0, 2881.0] | 6.0 | 0.689/0.914 | 7102 | BEGIN 2@1/4/v1 | S 5809; B 1723,1729; C none; L sheet#1:2047 | T | p1:m24:n1 |
| 3105 | [349.0, 2869.5] | [335.0, 2858.0, 363.0, 2881.0] | 6.0 | 0.693/0.915 | 7103 | BEGIN 3@1/2/v1 | S 5810; B 1723,1729; C none; L sheet#1:2039 | T | p1:m24:n2 |
| 3109 | [396.5, 2869.5] | [382.0, 2858.0, 411.0, 2881.0] | 6.0 | 0.711/0.938 | 7104 | BEGIN 4@3/4/v1 | S 5779; B 1723,1729; C 7223; L sheet#1:2043 | T | p1:m24:n3 |
| 3113 | [443.5, 2869.5] | [429.0, 2858.0, 458.0, 2881.0] | 6.0 | 0.704/0.952 | 7105 | BEGIN 5@1/v1 | S 5794; B 1688; C 7223; L sheet#1:2041 | T | p1:m24:n4 |
| 2937 | [493.5, 2816.0] | [479.0, 2804.0, 508.0, 2828.0] | 1.0 | 0.793/0.955 | 7106 | BEGIN 6@3/2/v1 | S 5808; B 1688,1702; C none; L none | T,P | p1:m24:n5 |
| 2941 | [535.5, 2816.0] | [521.0, 2804.0, 550.0, 2828.0] | 1.0 | 0.793/0.96 | 7107 | BEGIN 7@7/4/v1 | S 5795; B 1688,1702; C 7263; L none | T,P | p1:m24:n6 |
| 2945 | [579.5, 2816.0] | [565.0, 2804.0, 594.0, 2828.0] | 1.0 | 0.782/0.954 | 7108 | BEGIN 8@2/v1 | S 5790; B 1690; C 7263; L none | T,P | p1:m24:n7 |
| 2979 | [629.5, 2827.0] | [615.0, 2815.0, 644.0, 2839.0] | 2.0 | 0.759/0.95 | 7109 | BEGIN 9@5/2/v1 | S 5800; B 1690,1713; C none; L none | T,P | p1:m24:n8 |
| 2983 | [674.5, 2827.0] | [660.0, 2815.0, 689.0, 2839.0] | 2.0 | 0.756/0.954 | 7110 | BEGIN 10@11/4/v1 | S 5791; B 1690,1713; C 7330; L none | T,P | p1:m24:n9 |
| 2987 | [717.5, 2827.0] | [703.0, 2815.0, 732.0, 2839.0] | 2.0 | 0.759/0.941 | 7111 | BEGIN 11@3/v1 | S 5818; B none; C 7330; L none | T,P | p1:m24:n10 |

**B / HIGH; OBVIOUS_COUNTERPART = sheet#1:3124.** The raw D4 and corrected C4 share the exact onset and duration; only the semantic pitch changes. Both note event and head/chord exist. The slot join and raw semantic pitch provide independent evidence, not count-based pairing.

Crop: `v4-jayu-diagnostic-retry/gaps/gap-05.png` (untouched source panel beside annotation panel).

## Unmatched visual heads and relation coverage

The five unowned heads are 2334, 2335, 2602, 2748 and 3124, paired respectively
with gaps 1–5 above. Each is **OBVIOUS_COUNTERPART** for the correspondence audit;
none is newly MATCHED. Their coordinates, staff pitches, measures and exact BEGIN
slots are in the tables. No other same-staff head shares those onsets. Raw D4,
SIG +5, unchanged duration, singleton membership and V3's documented correction
establish one-to-one lineage independently for each pair.

For all five, the raw head containment and head-stem relation exist and survive
V4 parsing. The parent chords are explicitly listed by the correct raw measure;
the BEGIN references resolve to existing slots. Beam-stem relations exist for the
beamed cases, flag-stem for the flagged case, and slur-head for head 2335. There is
no valid missing SIG edge that would make these failures category J. Absence of
ledger objects at these x positions is an upstream visual recognition limitation,
not evidence that the head itself is absent or the semantic C is spurious.

## Protected-region audit: 30 pairs, four physical overlap components

The unique affected protected objects are two lyric lines (6499, 6590) and two
contained lyric items (6510 inside 6499; 6594 inside 6590). Their full text boxes
are not the same thing as individual ink regions. Connected components below are
computed from **intersection rectangles**, never from whole lyric-line boxes, so
distant overlaps along one lyric row are not collapsed artificially.

Primary classifications (exclusive, total 30):

- **6 expected conservative envelope overlaps:** line-only overlaps; no retained
  individual lyric-item box is intersected by that same edit at those locations.
  These are broad envelope alarms, not established note/text ink collisions.
- **12 duplicate nested text-protection pairs:** the same edit already intersects
  the containing lyric line. These are redundant accounting for protected pixels,
  not permission to remove lyric-item or lyric-line protection.
- **0 proven genuine note/text conflicts:** the existing page crops show separate
  note/beam/slur and text ink. This does not prove future target ink clearance.
- **12 unresolved/missing-ownership cases:** primary line pairs also overlapping
  the nested lyric items. Source/target sweep boxes include groups and curves;
  exact future ink ownership and clearance cannot be decided from these envelopes.
  They remain blockers, not benign collisions waived by the audit.

Each nested duplicate also inherits the uncertainty of its primary pair. This
classification distinguishes accounting from safety; no masks were generated and
no protection was reduced. Underlying note, group and curve envelopes can also
repeat the same physical area even after removing nested duplicates: 30 pairs ->
18 edit/protection occurrences -> **four** connected physical overlap areas.

| Physical component | Original-coordinate intersection bbox | Pair count | Interpretation |
|---|---|---:|---|
| R1 | `[481.95, 1349.0, 864.0, 1355.625]` | 5 | line-only conservative envelope |
| R2 | `[1403.0, 1349.0, 1450.0, 1355.625]` | 1 | line-only conservative envelope |
| R3 | `[1585.95, 1349.0, 1879.0, 1355.625]` | 10 | nested accounting plus unresolved ink ownership |
| R4 | `[843.5, 1735.0, 1277.0, 1745.625]` | 14 | nested accounting plus unresolved ink ownership |

All 30 pairs, in original plan order:

| Pair | Edit ID | Protected ID | Primary classification |
|---|---|---|---|
| 1 | sheet#1:1583 | sheet#1:6499 | expected conservative envelope overlap |
| 2 | sheet#1:1585 | sheet#1:6499 | unresolved / missing ownership |
| 3 | sheet#1:1585 | sheet#1:6510 | duplicate nested text protection |
| 4 | sheet#1:1630 | sheet#1:6590 | unresolved / missing ownership |
| 5 | sheet#1:1630 | sheet#1:6594 | duplicate nested text protection |
| 6 | sheet#1:2490 | sheet#1:6499 | expected conservative envelope overlap |
| 7 | sheet#1:2494 | sheet#1:6499 | unresolved / missing ownership |
| 8 | sheet#1:2494 | sheet#1:6510 | duplicate nested text protection |
| 9 | sheet#1:2498 | sheet#1:6499 | expected conservative envelope overlap |
| 10 | sheet#1:2506 | sheet#1:6499 | unresolved / missing ownership |
| 11 | sheet#1:2506 | sheet#1:6510 | duplicate nested text protection |
| 12 | sheet#1:2512 | sheet#1:6499 | expected conservative envelope overlap |
| 13 | sheet#1:2514 | sheet#1:6499 | expected conservative envelope overlap |
| 14 | sheet#1:2521 | sheet#1:6499 | unresolved / missing ownership |
| 15 | sheet#1:2521 | sheet#1:6510 | duplicate nested text protection |
| 16 | sheet#1:2523 | sheet#1:6499 | unresolved / missing ownership |
| 17 | sheet#1:2523 | sheet#1:6510 | duplicate nested text protection |
| 18 | sheet#1:2586 | sheet#1:6499 | expected conservative envelope overlap |
| 19 | sheet#1:2612 | sheet#1:6590 | unresolved / missing ownership |
| 20 | sheet#1:2612 | sheet#1:6594 | duplicate nested text protection |
| 21 | sheet#1:2618 | sheet#1:6590 | unresolved / missing ownership |
| 22 | sheet#1:2618 | sheet#1:6594 | duplicate nested text protection |
| 23 | sheet#1:2642 | sheet#1:6590 | unresolved / missing ownership |
| 24 | sheet#1:2642 | sheet#1:6594 | duplicate nested text protection |
| 25 | sheet#1:2729 | sheet#1:6590 | unresolved / missing ownership |
| 26 | sheet#1:2729 | sheet#1:6594 | duplicate nested text protection |
| 27 | sheet#1:2733 | sheet#1:6590 | unresolved / missing ownership |
| 28 | sheet#1:2733 | sheet#1:6594 | duplicate nested text protection |
| 29 | sheet#1:7241 | sheet#1:6590 | unresolved / missing ownership |
| 30 | sheet#1:7241 | sheet#1:6594 | duplicate nested text protection |

The focused source regions were visually inspected. In R1/R2, lyric-line-wide
vertical extents reach x locations whose glyph tops are lower; in R3/R4,
text and curve/group bounding boxes are too coarse to certify future separation.
There is no final-mask claim here, and future rendering must still fail closed.

## Two unresolved beam groups

| Beam-group plan ID | Beams | Missing target-delta heads | Cause |
|---|---|---|---|
| 1486 | 1486, 1492 | 2334, 2335 | gaps 1/2; existing stem/beam connectivity is present |
| 1723 | 1723, 1729 | 3124 | gap 5; existing stem/beam connectivity is present |

Group 1486 also contains head 2303 and stems 3727/3728/3742. Group 1723 also
contains heads 3101/3105/3109 and stems 5778/5779/5809/5810. The null deltas are
expected propagation of unresolved note correspondence, not a parser gap or
missing beam relation. Heads 2602 and 2748 do not cause unresolved beam groups:
2602 is an unbeamed quarter note; 2748 is flagged. No group was reconstructed or
reclassified using hypothesized note matches.

## Five unlinked slur/tie segments

| Segment | Raw endpoints and extension | Primary cause |
|---|---|---|
| 7225 | LEFT 2335; RIGHT 2307; no extension | gap 2; both slur-head edges exist, but head 2335 has no accepted move |
| 7209 | LEFT 2693; right-extension 7229 | cross-system continuation, not a missing relation |
| 7229 | RIGHT 2816; left-extension 7209 | other half of the preceding cross-system tie |
| 7197 | LEFT 2818; right-extension 7231 | cross-system continuation, not a missing relation |
| 7231 | RIGHT 2903; left-extension 7197 | other half of the preceding cross-system tie |

All referenced non-gap heads are already matched. The extension pairs are
7209 (end system 4) -> 7229 (start system 5), and 7197 (end system 5) -> 7231
(start system 6). Raw attributes and both directed extension references survive
parsing. The current planner intentionally requires two local endpoints and no
extension to report linked=true. Therefore **five unlinked segments represent
three logical curves**: one local slur blocked by a gap and two complete but
unsupported cross-system tie chains. This is not genuine endpoint ambiguity;
it is a deferred planner capability. No missing/unsupported SIG relation explains
these four segments, and no curve was transformed.

## Unsupported-node categories and original-pixel policy

| Category | Count | Classification | Audit disposition |
|---|---:|---|---|
| articulation | 38 | MAY_MOVE_WITH_NOTE | all have chord-articulation links; cannot categorically freeze once owning heads/stems move |
| fermata | 2 | MAY_MOVE_WITH_NOTE | 8171 -> chord 6984, 8512 -> chord 7079; both owners are pitched head-chords |
| dynamics | 1 | RENDER-IRRELEVANT_FOR_KEY_TRANSPOSE | 8404, chord-dynamics -> 7042: timing anchor does not require pitch-following vertical movement; preserve original pixels |
| pedal | 1 | RENDER-IRRELEVANT_FOR_KEY_TRANSPOSE | 8688, chord-pedal -> 7165: preserve original mark/position; harmonic timing association is not a pitch displacement |
| barline | 45 | STRUCTURAL | preserve at original horizontal layout; protect from future masks |
| staff-barline | 41 | STRUCTURAL | preserve structural groups/positions; not mutable just because adjacent notes transpose |

No category here is classified UNKNOWN at the taxonomy level. Whether an individual
recognized articulation/fermata is real notation or a false positive remains an
ownership/recognition question. V3 stripped 38 articulations and 2 fermatas from
its semantic output, but V4's pixel-preserving design must not erase or move the
underlying original pixels based only on that cleanup decision. Linked chord
IDs and geometry remain retained in the SIG even for unsupported categories.
Dynamics/pedal and structural bars may safely remain *no-edit by default* under
key transposition with fixed x/layout, but that is not permission for a future
mask to overwrite them. Collision handling is still required.

## Smallest principled next change: proposal only

**READY_FOR_MATCHER_FIX**, specifically a V4-only **repair-provenance/lineage fix**,
not a widened pitch rule. Five independent failures show the same lost boundary
between raw OMR semantics and repaired V3 semantics.

1. Retain raw semantic event identity and written/staff pitch before V3 cleanup.
   Record before/after per-event repair provenance in V4, without changing V3's
   repair function or mutating original SIG pitch/geometry.
2. Establish a unique raw semantic-to-head association using exact part, measure,
   staff, BEGIN onset, full chord membership and raw source pitch. Where a verified
   one-to-one semantic repair leaves identity/rhythm intact, carry that head ID to
   the corrected event and record both pitches plus the repair evidence.
3. Keep transposition displacement based on **corrected source -> V3 target**
   diatonic numbers. Never compute D4 -> target as though raw D4 were the corrected
   source. Preserve original geometry and flag uncertain pivots separately.
4. If either join is ambiguous, any rhythm/identity changes, the repair lacks
   provenance, or pixel evidence is absent, retain AMBIGUOUS/UNMATCHED. No nearest
   fallback, grade tiebreak, generic +/-1 tolerance, or measure-specific override.
5. Add fixture tests for a repaired ledger note, unchanged neighbors, duplicate
   raw onsets/chords, missing correction evidence and corrected-source movement.

This proposal is structurally motivated by the existing repair stage, not by a
jayu measure list. No part of it was implemented in this audit. A separate future
planner change may join reciprocal cross-system curve extensions, with explicit
chain identity and per-endpoint matching; this is not needed to explain the five
note gaps and does not authorize rendering.

Before Phase 2, review source head pivots, the unresolved protection ownership,
attached articulation/fermata policy, and cross-system curve representation. A
future increase to 249/249 correspondence would still not prove pixel-edit safety.

## Reproduction and verification

Developer-only helper, no binaries/recognition or production code:

```bash
python -m scripts.omr_v4.audit_mapping v4-jayu-diagnostic-retry
python -m pytest tests/test_omr_v4_audit.py -q
```

The helper prints/writes the full structured candidate audit and writes five
`gaps/gap-XX.png` files. Each shows an untouched source crop next to an independent
annotation panel, with expected semantic label, head IDs, all candidate boxes,
slot positions, staff polylines, measure x bounds and explicit rejection labels.
It verifies that the source PNG file hash stays unchanged. Candidate checks are
human audit context only; the helper never invokes `match_notes` or updates plans.
Tests cover keeping pitch-mismatched and other-slot candidates, nested protection
accounting without deleting protection, deterministic evidence and source-image
preservation. **3 tests passed**. Existing matcher/runtime files are unchanged.

Local evidence paths:

- `v4-jayu-diagnostic-retry/gaps/candidate-audit.json`
- `v4-jayu-diagnostic-retry/gaps/gap-01.png` through `gap-05.png`
- Original input artifact hashes: `v4-jayu-diagnostic-retry/gaps/evidence-sha256.json`

Generated crops/JSON are local diagnostic evidence, not production outputs or
approved edit masks. This pass commits only this document, the developer helper
and its tests. No runtime, matcher, renderer, protection, V1 or V3 source behavior
changed; no Phase 2 work, merge or deployment occurred.
