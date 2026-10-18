# Independent ink collection: offline runbook

The [frozen protocol](V4_INDEPENDENT_INK_PROTOCOL.json) remains authoritative. This helper prepares source-only human collection; it supplies no physical truth, ownership decision, guard change, or implementation authorization. Its tests use clearly synthetic images and labels.

## Present readiness

`reference-prep-a-output/readiness.json` reports **NOT_READY**, **0 official selected anchors**, and planned maxima of 96 prevalence plus 32 diagnostic anchors. No eligible human roster, training exclusions, or completed independent source-only screening nominations were supplied. Absence of screening is never interpreted as zero nominations. The kit contains the exact original source file, a row-major clipped 64 × 64 tile manifest and all 2,145 native tile PNGs with hashes, empty nomination/roster/training/signature forms, screening instructions/schema and annotation instructions/schema. Tile bounds index the full source image; `screening-tiles/` contains the entire page partition, including clipped edge tiles. These source-only viewing crops are not selected evaluation anchors. The kit does not construct an official sample or distribute primary packets.

Inspect the existing kit, or choose a fresh output directory when rerunning preparation. Run from this checkout with the existing environment:

```sh
PY=/private/tmp/capomatic-v4-venv/bin/python
$PY -m scripts.omr_v4.collect_independent_ink prepare --out reference-prep-a-output-new
```

Outputs must stay outside the immutable evidence root; symlink paths are rejected. The command requires a new output directory and checks the protocol digest, all 28 shared input hashes, source identity and dimensions before and after preparation. It never rewrites the original evidence or previous validation output.

## Custodian prerequisites

Recruit distinct human A, B, adjudicator, independent source-only screener, and custodian/packet maker. A, B and the adjudicator must have no excluded role from the protocol. Record identities, expertise, conflicts, exposure and eligibility attestations in the roster form. Freeze separate consented training pages and instructions; excluded page hashes cannot equal this evaluation source. Entire training pages are excluded from all evaluation and future holdout use.

Make working copies of the kit forms outside the kit. Complete each signature form with `person_id`, nonblank `signature`, and timezone-aware `signed_at`. Freeze roster and training first, signed by the custodian. The independent screener then examines every tile in manifest order using only original source appearance. Each tile must explicitly be `examined`, `unavailable` or `unclassifiable`; the latter two require a reason and no nominations. Explicit empty nomination lists are valid only on completed screening tiles. Each examined tile permits at most one anchor per motif from the protocol's four motif names. Nomination coordinates are global original-source integers inside that tile. Do not show screening tags to primary annotators.

```sh
$PY -m scripts.omr_v4.collect_independent_ink freeze-input --kind roster --input roster.json --signer custodian-signature.json --output private/roster-frozen.json
$PY -m scripts.omr_v4.collect_independent_ink freeze-input --kind training --input training.json --signer custodian-signature.json --output private/training-frozen.json
$PY -m scripts.omr_v4.collect_independent_ink freeze-input --kind screening --input screening.json --signer screener-signature.json --output private/screening-frozen.json
$PY -m scripts.omr_v4.collect_independent_ink packet --out primary-packet --audit private/audit.json --roster private/roster-frozen.json --training private/training-frozen.json --screening private/screening-frozen.json
```

A freeze writes a new envelope and `.receipt.json` with the file digest, then makes both read-only. Keep receipts separately under custodian control and record who received which files and when. Sampling validates all prerequisite content/signatures and chronology before ranking any pixel. Do not backdate records or treat attestations as verified human independence. Changing the protocol, roster, source or prerequisites requires a new study version and untouched sample under the frozen contract.

## Primary collection and freeze

The packet mixes both arms in opaque presentation-ID order. It contains the untouched full-page source and separate native focus/context crops, with target coordinates local to each crop. Edge clipping, 65/513 dimensions, rank encodings and quotas follow the protocol exactly. The custodian-only audit mapping is outside the packet and contains global coordinates, strata, motifs, denominators, prerequisites and overlap statistics. Never distribute it to A, B, or the source-only adjudicator.

Give identical packets separately to A and B, plus distinct working copies of `submission-template.json`. Each completes every case in packet order, role `A` or `B`, their frozen identity/signature metadata and `source_only_independent: true`. Every row needs nonempty physical/boundary enum sets, certainty and rationale. `MIXED` means selecting multiple valid physical/contribution choices; it is **not** an additional physical enum. UNKNOWN can coexist with other labels. Preserve uncertainty, UNKNOWN and ABSTAIN. Source-only ownership stays `{"contributors": [], "unresolved": true}`; later attachment evidence is separate work.

```sh
$PY -m scripts.omr_v4.collect_independent_ink submit --out primary-packet --audit private/audit.json --archive private/primary-freezes --role A --input A-complete.json
$PY -m scripts.omr_v4.collect_independent_ink submit --out primary-packet --audit private/audit.json --archive private/primary-freezes --role B --input B-complete.json
```

Blank templates, missing/duplicate cases, invalid enum sets, missing rationale, wrong identity, changed hashes, or predicted ownership cannot freeze. Submission, row and signature fields have exact allowlists: extra prediction/evidence fields are rejected. Packet verification rejects unexpected files, directories and symlinks; private archives and reports must remain outside the packet. Each primary file is archived separately without overwriting; the command returns only its receipt, never the other primary's labels. Originals remain intact. A mistaken signed file needs a documented versioned correction preserving the first freeze; this helper does not replace frozen files.

## Disagreement and independent adjudication

```sh
$PY -m scripts.omr_v4.collect_independent_ink disagreements --out primary-packet --audit private/audit.json --archive private/primary-freezes --report-dir private/comparison
```

This command checks **both** primary freezes, their receipts, all case IDs, packet/source/crop hashes and frozen prerequisites before writing any report. Give the third reviewer only the source packet, `source-only-comparison.json` and `adjudication-template.json`. Keep `custodian-statistics.json` private: it separates arms and contains paired/unpaired/total counts, exact physical/boundary-set agreement, per-label 2 × 2 tables, disagreements, UNKNOWN/ABSTAIN counts, screening/cell denominators and overlap-window statistics. It is descriptive bookkeeping, not a physical accuracy test or rule acceptance result.

The adjudicator independently completes every row, retaining UNKNOWN, alternatives and unresolved ownership where warranted. They add `alternatives_and_disposition` per row, their own signature after both primary freezes, and both primary hashes already populated by the template. No automatic consensus or predicted ownership is generated.

```sh
$PY -m scripts.omr_v4.collect_independent_ink adjudicate --out primary-packet --audit private/audit.json --archive private/primary-freezes --input adjudicator-complete.json --output private/adjudication-frozen.json
```

The resulting physical-label freeze preserves both primary files. Unblinded joins, page-weighted prevalence analysis, attachment evidence, holdout acquisition and rule evaluation remain outside this preparation helper. The frozen protocol still governs any later work.

## Access and integrity limits

Local files do not enforce person-level access control, privacy, cryptographic identity, or genuine independence. Read-only modes and digest receipts detect changed content relative to retained receipts; someone able to rewrite both a file and its receipt can bypass that check. The custodian must hold receipts separately, restrict directories, distribute only permitted files, keep exposure/access records, and stop on a blinding breach. Do not put A and B in a shared archive directory they can browse. This is an offline collection workflow, not a secure submission platform.
