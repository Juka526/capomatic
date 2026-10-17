"""One-page V4 diagnostic: INPUT --semitones N --out DIR (never an API path)."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import tempfile
from pathlib import Path
from dataclasses import replace
from xml.etree import ElementTree as ET

from backend.omr_v4.diagnostic import write_diagnostics
from backend.omr_v4.integrity import classify_integrity
from backend.omr_v4.matcher import match_notes, read_semantics
from backend.omr_v4.plan import build_plan
from backend.omr_v4.visual_graph import load_visual_graph, safe_xml


def _stable_export_ids(path: Path) -> None:
    # music21 generates UUID part/notation IDs at each export. Give part IDs a
    # deterministic, explicitly non-Audiveris name; never pretend this proves
    # multi-part correspondence. Notation IDs are irrelevant to semantic events.
    root = safe_xml(path.read_bytes(), musicxml=True)
    definitions = root.findall('part-list/score-part')
    mapping = {part.get('id'): f'V4Part{i}' for i, part in enumerate(definitions, 1)}
    for element in root.iter():
        if element.tag in {'part', 'score-part'} and element.get('id') in mapping:
            element.set('id', mapping[element.get('id')])
    path.write_bytes(ET.tostring(root, encoding='utf-8', xml_declaration=True))


def inspect_recognized(
    raster: Path, book: Path, recognized: Path, semitones: int, out: Path
) -> dict:
    """Reuse V3 cleanup/transposition/integrity on one recognized development page."""
    from music21 import converter, stream
    from backend.omr_v3 import cleanup
    from backend.omr_v3.geometry import GeometryError, load_geometry
    from backend.omr_v3.transpose import transpose_score, validate_request

    validate_request('key', semitones)
    graph = load_visual_graph(book)
    if len(graph.pages) != 1:
        raise ValueError('The diagnostic CLI accepts exactly one raster sheet')
    score = converter.parse(str(recognized))
    if not score.parts:
        raise ValueError('No recognized parts')
    repairs = {
        'rest_only_voices_removed': cleanup.drop_rest_only_voices(score),
        'lyrics_removed': cleanup.clean_lyrics(score),
        'chord_words': cleanup.chord_words_to_symbols(score),
        'marks_removed': cleanup.strip_marks(score),
        'layout': cleanup.normalize_layout(score),
    }
    # Do not pass malformed V4 coordinates into V3's optional spatial repair.
    if graph.invalid_geometry_count == 0:
        try:
            geometry = load_geometry(book)
        except GeometryError:
            geometry = None
        measures = list(score.parts[0].getElementsByClass(stream.Measure))
        aligned = geometry is not None and (
            geometry.remap_to_measures([m.measureNumberWithSuffix() for m in measures])
            or geometry.measure_count == len(measures)
        )
        if aligned:
            repairs['ledger_notes_fixed'] = cleanup.fix_missed_ledgers(score, geometry, raster)
    out.mkdir(parents=True, exist_ok=True)
    source_xml, target_xml = out / 'recognized.musicxml', out / 'transposed.musicxml'
    score.write('musicxml', fp=str(source_xml))
    transposed = copy.deepcopy(score)
    transposition = transpose_score(transposed, semitones)
    transposed.write('musicxml', fp=str(target_xml))
    _stable_export_ids(source_xml)
    _stable_export_ids(target_xml)
    before, after = converter.parse(str(source_xml)), converter.parse(str(target_xml))
    integrity = classify_integrity(before, after, semitones)
    (out / 'semantic-report.json').write_text(
        json.dumps(
            {
                'repairs': repairs,
                'transposition': transposition,
                'integrity': integrity['full_guard'],
                'semantic_integrity': integrity,
                'recognition': 'V3 Audiveris; Audiveris chord text only (no separate Paddle pass)',
                'purpose': 'Offline diagnostic, not a V3 gate/acceptance or release decision',
            },
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + '\n',
        encoding='utf-8',
    )
    if integrity['overall'] == 'fail':
        raise ValueError(f"V4 diagnostic semantic integrity failed: {integrity['fatal_issues']}")
    source, target = read_semantics(source_xml), read_semantics(target_xml)
    matches = match_notes(source, graph)
    plan = build_plan(graph, source, target, matches)
    if integrity['overall'] == 'warning':
        plan = replace(
            plan,
            blockers=tuple(
                sorted(
                    set(plan.blockers)
                    | {
                        'Chord integrity warning (diagnostic only): ' + issue
                        for issue in integrity['chord_issues']
                    }
                )
            ),
        )
    return write_diagnostics(raster, graph, plan, out, semantic_integrity=integrity)


def main() -> None:
    """Run bounded V3 rasterization and recognition, then V4 diagnostic planning."""
    from backend.omr_v3.core import MAX_BYTES, rasterize, run_audiveris, validate
    from backend.omr_v3.transpose import validate_request

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--semitones', type=int, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    validate_request('key', args.semitones)
    source, out = args.input.resolve(), args.out.resolve()
    if source.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.pdf'}:
        parser.error('INPUT must be a single-page PDF or PNG/JPEG raster')
    if source.stat().st_size > MAX_BYTES:
        parser.error('INPUT exceeds V3 upload size bound')
    validate(source.read_bytes(), source.suffix.lower())
    if out.exists() and any(out.iterdir()):
        parser.error('--out must be empty or new; existing artifacts are never overwritten')
    with tempfile.TemporaryDirectory(prefix='capomatic-v4-') as temporary:
        work = Path(temporary)
        home = work / 'tool-home'
        home.mkdir()
        raster = work / 'source.png'
        rasterize(source, source.suffix.lower(), raster, 60, home)
        recognized, book = run_audiveris(raster, work / 'omr', 300, home)
        if book is None:
            raise ValueError('Audiveris produced no .omr visual evidence')
        summary = inspect_recognized(raster, book, recognized, args.semitones, out)
        shutil.copy2(raster, out / 'source.png')
        shutil.copy2(book, out / 'recognized.omr')
        shutil.copy2(recognized, out / ('audiveris' + recognized.suffix))
    print(json.dumps(summary, sort_keys=True, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
