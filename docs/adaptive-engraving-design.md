# Adaptive optical engraving: research policy 1.0

DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE — INCOMPLETE — NOT FOR PERFORMANCE OR PRINTING

This is a proposal for generated standalone notation layers. It grants no source-ink replacement, production renderer, independent-accuracy or performance-readiness approval. GT-16C implements only bounded lyric spacing and selected diagonal-beam raster alternatives.

## Inputs and invariants

Keep semantic score data separate from layout, rasterization and evidence. Preserve written and sounding pitches, duration, voice, chord identity/alterations/bass, lyric strings and associations, tie identities and explicit repeat notation. Store owner interpretations separately from raw OMR and withheld objects. A renderer cannot establish source completeness by drawing every recognized event.

Layout inputs need a complete component graph: note-specific glyph anchors; stems and beam members; local/cross-system tie roles; chord ink widths; two Korean lyric rows with exact note association and continuation identities; fixed staff/measure registration. Original font-outline centers, source-detector centers, semantic staff coordinates and actual raster-bbox centers remain distinct.

## Optical spacing

Measure actual nonzero-alpha ink, including antialias coverage, against all notation/context and adjacent systems. Distinguish center distance from the distance between closed unit pixel squares. Retain zero unexpected contacts and clipping as hard safety requirements. GT-16C's 6px native center-distance goal is an exploratory heuristic, not an engraving standard, and does not establish readability at another display scale.

First retain source horizontal anchors and typography. Translate each system's two lyric rows and associated marks together by the minimum feasible nonnegative integer displacement within its explicitly registered lyric allocation. Fixed-notation strip boundaries are not lyric boundaries: a lyric can validly extend below a context-strip split. Establish admissible lyric domains from actual frozen/source-derived registration, and test known-valid baseline controls before declaring infeasibility. Do not narrow a domain to manufacture page-height failure.

If no feasible solution exists, increase inter-system allocation and translate an entire system's notation, chords and lyrics by one explicit offset. This preserves its local note-to-staff coordinates. Cross-system ties retain two separate segments, one in each translated system; never draw a line through the page gap. Recheck all neighboring context and measure labels. A larger diagnostic canvas is a distinct layout, not preservation of original page registration.

If all systems cannot fit the intended page height, propose pagination or a taller diagnostic canvas. Do not compress the glyphs, overlap lyrics, hide components, shift text horizontally or silently change the sounding octave. Four displayed systems fitting a canvas says nothing about whether all nine source systems fit a page.

## Beam rasterization

Keep a semantic beam group, exact centerline endpoints, membership and stem geometry immutable. Evaluate finite 2×/3×/4× area-sampling candidates in page pixel-center coordinates; use BOX averaging to avoid filter ringing and hidden alpha cutoffs. Store alternatives separately, including nonzero support, coverage area, profile error, connection counts and changed-pixel bounds. Expected raster support changes are not required to be byte-identical.

Accept only candidates that preserve every required stem contact, create no unrelated contact, remain connected, and clip no ink. Numerical profile smoothness measures raster consistency, not professional beam optics. Inspect native and reduced-size output before freezing. Preserve mixed beams/hooks when their complete recomposition contract is not yet supported; do not extrapolate simple-beam success to them.

## Extreme register and future octave notation

A requested ±12/±24-semitone transposition must first preserve that exact musical interval. Recalculate written-pitch and ledger envelopes, stem/beam/curve extents and lyric/chord exclusions. Use those bounds to trigger extra vertical allocation or page breaks; do not decide from interval size alone. Moderately high notes usually pressure upper chord/context space, while low notes pressure lyric space, but actual masks and attachment graphs must determine feasibility.

8va/8vb could later be offered as a separately authorized notation transform that retains the requested sounding pitches while explicitly changing written octave and engraving the full octave line, labels, span and endpoints. It needs a semantic representation, user intent, range validation and independent musical review. Never substitute an unmarked octave change to make a cramped result fit. GT-16C adds no octave notation or sounding-pitch change.

## Evidence and release boundaries

Freeze source/owner/semantic inputs and every candidate's protocol, geometry, masks and hashes. Keep failed alternatives and design revisions. Report source completeness, semantic consistency, rendering coverage, optical agent inspection and independent musician review separately. A shared renderer/geometry checker proves internal consistency; independently collected musical and optical evidence remains necessary for stronger claims. Do not promote unresolved SIG objects or infer repeat playback from a legible bracket. MusicXML lyric-extender serialization needs its own future research contract.
