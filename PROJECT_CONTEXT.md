CLAUDE.md — Transchord Project Instructions
Project

Transchord is a web-based chord transposition tool for guitarists, starting with Korean church worship team sheet music.

Users upload a sheet image, the system detects chord symbols above the staff, transposes them by target key or capo logic, and returns an image with transposed chord overlays.

MVP rule

Do not transpose staff notes

Only change the printed chord symbols above the staff

Target users

Korean church worship team guitarists

Acoustic / strumming players

Users working with Korean worship sheet formats

This is a personal editing/transposition tool, not a score-selling platform.

Product principles

Detect first, transpose second

OCR / AI only detects chords

Transposition must remain deterministic in code

Local OCR first, AI fallback second

Paddle OCR is the primary path

AI fallback is a backup for hard pages

Optimize for the target domain first

Korean worship sheets are the current domain

Domain-focused tuning is acceptable

Avoid overfitting to only one publisher/style

Measure before changing

Any OCR change must be evaluated with metrics:

coverage

OCR time

predict time

stitched image size

fallback rate

Current architecture
Chord logic

Deterministic and already implemented:

normalize chord text

parse chord strings

transpose chords

handle slash chords, sus/add/dim/aug, maj/min, enharmonic policy

OCR pipeline

Current flow:

detect staff systems

crop chord bands above staff systems

stitch bands

run Paddle OCR

strict filter

recovery pass

quality gate

optional AI fallback

Hybrid engine

Paddle OCR remains primary

Quality gate decides if OCR result is reliable

AI fallback returns row-wise chord text only

AI does not transpose

AI does not provide production-ready overlay coordinates yet

Current implementation status
Stable / implemented

chord normalization / parser / transpose engine

staff-aware chord-band cropping

stitched OCR input

OCR normalization and recovery

hybrid quality gate + AI fallback structure

labeled eval fixtures

tests for parser, transpose, gate, fallback parsing

Current bottleneck

Main latency bottleneck is Paddle detector inference

server_det is accurate but slow

mobile_det was tested and rejected as default:

much faster

but unacceptable coverage drop on dense chord sheets

Current default should remain:

server detector

mobile recognizer

Current product scope
In scope

PNG / JPG input

chord detection above staff

target key transposition

capo-based transposition

two overlay modes later:

orange chord beside original

semi-transparent white box + new chord

async job-based flow later

Korean worship sheet focus

Out of scope for now

PDF support

full note/staff transposition

strong skew/photo correction

exact AI bbox overlay

generic score support for every sheet style

UI polish before backend reliability

Important chord rules

Support slash chords, sus4, add9, maj7, dim, aug, 6/7/9/11/13

Use compact normalized style:

Esus4, A7sus4, etc.

Follow target-key-friendly enharmonic output

Avoid impractical spellings like E#, Cb, Fb, B#

Dataset / evaluation rules

Use labeled fixtures for every OCR change

Track:

coverage

OCR time

predict time

stitched shape / pixel count

gate pass/fail

fallback usage

Add more non-gifted Korean worship sheets over time

Do not tune only against one style

Current engineering priorities
Priority 1

Reduce OCR latency without breaking coverage.
When experimenting:

prefer small, isolated changes

compare before/after on the fixture set

keep debug metadata visible

Priority 2

Validate on more unseen Korean worship sheets.

Priority 3

Bridge final detected chords into transposition-ready structured output and overlay pipeline.

Change guidelines for Claude Code

When editing this repo:

keep changes minimal and local

do not refactor unrelated modules

preserve deterministic chord parsing/transposition

preserve eval/debug visibility

keep server detector as default unless new evidence proves otherwise

always report:

files changed

metrics before/after

test result

whether coverage changed

Immediate non-goals

Do not spend time on:

PDF

perfect AI coordinates

staff note transposition

replacing deterministic transpose with AI

broad generalization outside Korean worship sheets too early

Near-term success definition

Good progress means:

keep coverage near current level

reduce detector latency meaningfully

preserve hybrid fallback architecture

move toward a usable image overlay result
