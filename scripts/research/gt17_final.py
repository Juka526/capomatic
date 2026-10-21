"""One consolidated, offline GT17 research release; no production imports modified."""

import argparse
import time
import resource
import copy
from pathlib import Path
import xml.etree.ElementTree as ET
import hashlib
import json
import platform
import unicodedata

import numpy as np
from music21 import converter, harmony, stream
from music21.repeat import ExpanderException
from PIL import Image

from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt11_complete_measure import read, require, events_of
from scripts.research.gt16_fourth_system import repeat_signature
from scripts.research.gt17b_owner_integration import (
    SOURCE_DIR,
    relationship_signature,
    core_signature,
    verify_manifest,
)
from scripts.research.gt17c_accuracy_audit import OWNER, playback_review, xml_curve_audit
from scripts.research.gt17d_owner_correction import relationship_inventory, tree_fingerprint
from scripts.research.gt17f_owner_lyric_confirmation import PRIOR as GT17E, SEMANTIC
from scripts.research.gt17_final_semantics import (
    source_marks,
    lineage,
    add_extensions,
    extension_signature,
    strip_extensions,
    text_signature,
    RAW,
    GROUP_COUNTS,
)
from scripts.research.gt17_final_render import render_score, framed
from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes

ROOT = Path(__file__).resolve().parents[2]
PRIOR = Path('/private/tmp/capomatic-v4-gt17f/gt17f-final-output')
START = 'dab7562fa504130be9f13f7a9df8ca7afca9b847'


def save_xml(root, path):
    # Export labels are research metadata, never a corrected source-title transcription.
    warning = 'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING'
    identification = root.find('identification')
    if identification is None:
        identification = ET.Element('identification')
        root.insert(
            next(
                (
                    j
                    for j, e in enumerate(root)
                    if e.tag in ('defaults', 'credit', 'part-list', 'part')
                ),
                len(root),
            ),
            identification,
        )
    miscellaneous = identification.find('miscellaneous')
    if miscellaneous is None:
        miscellaneous = ET.SubElement(identification, 'miscellaneous')
    for title_path, label in [
        ('work/work-title', 'GT17OriginalUnverifiedWorkTitle'),
        ('movement-title', 'GT17OriginalUnverifiedMovementTitle'),
    ]:
        title = root.find(title_path)
        if (
            title is not None
            and title.text
            and title.text != warning
            and not any(
                f.get('name') == label for f in miscellaneous.findall('miscellaneous-field')
            )
        ):
            ET.SubElement(miscellaneous, 'miscellaneous-field', name=label).text = title.text
    work = root.find('work')
    if work is None:
        work = ET.Element('work')
        root.insert(0, work)
    title = work.find('work-title')
    if title is None:
        title = ET.SubElement(work, 'work-title')
    title.text = warning
    movement = root.find('movement-title')
    if movement is None:
        movement = ET.Element('movement-title')
        root.insert(list(root).index(identification), movement)
    movement.text = warning
    # Existing owner-approved section headings; plain words carry no repeat jump.
    for part in root.findall('part'):
        for number, label in [(9, 'Pre-Chorus'), (20, 'Chorus'), (30, 'Tag')]:
            measures = part.findall('measure')
            if len(measures) < number:
                continue
            measure = measures[number - 1]
            present = [w.text for w in measure.findall('./direction/direction-type/words')]
            if label not in present:
                direction = ET.Element('direction', placement='above')
                ET.SubElement(ET.SubElement(direction, 'direction-type'), 'words').text = label
                index = next(
                    (j for j, e in enumerate(measure) if e.tag in ('harmony', 'note')), len(measure)
                )
                measure.insert(index, direction)
    # Only generated exports use deterministic instrument IDs; original inputs remain unchanged.
    mapping = {}
    for j, inst in enumerate(root.findall('.//score-instrument'), 1):
        mapping[inst.get('id')] = f'GT17Instrument{j}'
    for e in root.iter():
        if (
            e.tag in ('score-instrument', 'midi-instrument', 'instrument')
            and e.get('id') in mapping
        ):
            e.set('id', mapping[e.get('id')])
    for d in root.findall('.//encoding-date'):
        d.text = '2026-10-21'  # fixed research configuration date, not an owner approval timestamp
    path.write_bytes(
        b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='utf-8') + b'\n'
    )


def approval_ledger(plan, marks, graph):
    items = [i for g in plan['groups'] for i in g['items']]
    byid = {i['id']: i for i in items}
    require(len(byid) == len(items), 'Duplicate approval cases')
    approved_strokes = []
    for g, n in GROUP_COUNTS.items():
        groups = [x for x in plan['groups'] if x['group_id'] == g]
        require(
            len(groups) == 1 and len(groups[0]['items']) == n, 'Owner continuation group mismatch'
        )
        for i in groups[0]['items']:
            require(
                i['id'] in {m['id'] for m in marks if m['measure'] != 28}, 'Unknown approved stroke'
            )
            approved_strokes.append(
                {
                    'case': i,
                    'classification': 'OWNER_VERIFIED_VISIBLE_LYRIC_CONTINUATION',
                    'semantic_lineage_automatically_approved': False,
                }
            )
    raw = []
    links = []
    for kind, ids in RAW.items():
        for sid in ids:
            ident = 'sheet#1:' + sid
            case = byid.get('sig-' + ident)
            require(case is not None, 'Missing raw approval case ' + ident)
            obj = graph['symbols'][ident]
            require(case['source_window'] == obj['geometry']['bbox'], 'Raw source bbox mismatch')
            raw.append(
                {
                    'id': ident,
                    'classification': kind,
                    'evidence': 'OWNER_VERIFIED_INTERPRETATION',
                    'raw_observation_unchanged': obj,
                    'review_case': case,
                }
            )
            if kind != 'LYRIC_CONTINUATION_STROKE':
                continue
            a = obj['geometry']['bbox']
            for m in marks:
                b = m['source_bbox']
                if b is None:
                    continue
                intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(
                    0, min(a[3], b[3]) - max(a[1], b[1])
                )
                small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
                if small > 0 and intersection / small >= 0.8:
                    links.append(
                        {
                            'raw_id': ident,
                            'visible_mark_id': m['id'],
                            'observed_region_overlap_fraction': intersection / small,
                            'graphical_stroke_added': False,
                        }
                    )
    require(len(raw) == 27 and len(approved_strokes) == 19, 'Owner approval scope mismatch')
    return {
        'owner_approval_verbatim': (
            ROOT / 'docs/evidence/GT17_FINAL_OWNER_APPROVAL.txt'
        ).read_text(),
        'approval_origin': 'Exact approval scope quoted in current GT17 FINAL user instruction; no signature/timestamp/independent reviewer fabricated',
        'source_bindings': {
            'GT17F_freeze_sha256': sha(PRIOR / 'output-freeze.json'),
            'GT17F_interpretation_sha256': sha(PRIOR / 'owner-interpretation-layer.json'),
            'GT17F_remaining_plan_sha256': sha(PRIOR / 'remaining-review-plan.json'),
        },
        'new_visible_classifications': approved_strokes,
        'new_raw_interpretations': raw,
        'overlapping_stroke_links': links,
        'graphical_duplication_policy': 'Render canonical 50 visible mark records once; raw SIG is interpretation only, glyph strokes and punctuation add no duplicate glyphs.',
        'retained_section_labels': {
            'Pre-Chorus': {'source_word_id': 'sheet#1:4183', 'approval_origin': 'GT15B'},
            'Chorus': {
                'source_candidates': read(OWNER / 'source-event-inventory.json')['systems'][5][
                    'section_candidates'
                ],
                'approval_origin': 'GT17B owner integration',
            },
            'Tag': {
                'source_candidates': read(OWNER / 'source-event-inventory.json')['systems'][7][
                    'section_candidates'
                ],
                'approval_origin': 'GT17B owner integration',
            },
        },
        'm28_ancestry_approved': False,
        'full_playback_approved': False,
        'independent_ground_truth': 0,
    }


def check_history(snapshots):
    additions = []
    checked = {}
    for folder, files in snapshots.items():
        actual = file_hashes(Path(folder))
        require(
            all(actual.get(n) == h for n, h in files.items()),
            'Frozen historical artifact mismatch ' + folder,
        )
        extra = set(actual) - set(files)
        require(
            not extra
            or (
                folder == '/private/tmp/capomatic-v4-gt17c/gt17c-frozen-output'
                and extra == {'.Rhistory'}
            ),
            'Unexpected unbound historical file: ' + folder,
        )
        additions.extend(
            {
                'path': str(Path(folder) / n),
                'sha256': actual[n],
                'status': 'UNBOUND_NON_EVIDENCE_DIRECTORY_ADDITION_NOT_USED_AS_INPUT',
            }
            for n in sorted(extra)
        )
        checked[folder] = actual
    return checked, additions


def run(out):
    started = time.perf_counter()
    require(not out.exists(), 'Fresh consolidated output directory required')
    verify_manifest(PRIOR, 'output-freeze.json')
    meta = read(ROOT / 'docs/V4_GT17F_VALIDATION.json')
    for name, digest in meta['artifact_sha256'].items():
        require(sha(PRIOR / name) == digest, 'GT17F freeze mismatch ' + name)
    pv = read(PRIOR / 'preservation-verification.json')
    snapshots = pv['historical_directory_file_hashes']
    snapshots, additions = check_history(snapshots)
    snapshots[str(PRIOR)] = file_hashes(PRIOR)
    src = pv['source_hashes']
    for n, k in [
        ('source.png', 'source_sha256'),
        ('recognized.omr', 'omr_sha256'),
        ('visual-graph.json', 'graph_sha256'),
    ]:
        require(sha(SOURCE_DIR / n) == src[k], 'Original source hash mismatch')
    inventory = read(OWNER / 'source-event-inventory.json')
    graph = read(SOURCE_DIR / 'visual-graph.json')
    marks = source_marks(inventory, graph)
    ledger = approval_ledger(read(PRIOR / 'remaining-review-plan.json'), marks, graph)
    source = converter.parse(str(SEMANTIC / 'corrected-source.musicxml'))
    spans, exceptions = lineage(source, marks)
    require(
        len(spans) == 49
        and len(exceptions) == 1
        and exceptions[0]['stroke_id'] == 'continuation-m28-r1-stroke-0',
        'Unexpected extension exception; inspect exact source evidence',
    )
    evidence = read(OWNER / 'owner-interpretation-layer.json')['curve_interpretations']
    out.mkdir(parents=True)
    dump(out / 'final-owner-approval-ledger.json', ledger)
    dump(
        out / 'final-source-coverage.json',
        {
            'systems': [
                {'system': s['system'], 'printed_measures': s['printed_measures']}
                for s in inventory['systems']
            ],
            'event_core_approvals': read(PRIOR / 'field-coverage-matrix.json')['event_cores'],
            'owner_confirmed_event_cores': 169,
            'owner_approved_chords': 24,
            'owner_approved_syllable_wording_and_onsets': 167,
            'source_lyric_onsets': [
                {
                    'measure': i,
                    'onset': str(n.getOffsetInHierarchy(m)),
                    'row': l.number,
                    'text': l.text,
                    'classification': 'OWNER_VERIFIED_SOURCE',
                }
                for i, m in enumerate(source.parts[0].getElementsByClass(stream.Measure), 1)
                for n in events_of(m)
                for l in n.lyrics
                if l.text
            ],
            'visible_marks': marks,
            'new_raw_classifications': 27,
            'visible_marks_owner_classified': 49,
            'm28_visible_stroke_retained': True,
            'source_completeness': 'UNVERIFIED',
            'independent_ground_truth': 0,
        },
    )
    guards = {}
    xmlreports = {}
    roundtrips = {}
    scores = {}
    signatures = {}
    for name, shift in [('Bb', 0), ('A', -1), ('G', -3)]:
        score = copy.deepcopy(source)
        summary = transpose_score(score, shift, 'key') if shift else None
        basefile = out / f'{name}-semantic-base.musicxml'
        score.write('musicxml', fp=str(basefile))
        base = ET.fromstring(basefile.read_bytes())
        save_xml(base, basefile)
        final = add_extensions(base, spans)
        save_xml(final, out / f'{name}-final-experimental.musicxml')
        sig = extension_signature(final)
        signatures[name] = sig
        require(
            tree_fingerprint(strip_extensions(final)) == tree_fingerprint(base),
            'Non-extender XML content changed',
        )
        parsed = converter.parse(str(out / f'{name}-final-experimental.musicxml'))
        guards[name] = {
            'in_memory': validate(source, score, shift, 'key', summary).to_dict(),
            'serialized': validate(source, parsed, shift, 'key', summary).to_dict(),
        }
        require(all(v['ok'] for v in guards[name].values()), 'Full V3 guard failed ' + name)
        require(text_signature(source) == text_signature(parsed), 'Lyric text/row/onset changed')
        require(repeat_signature(source) == repeat_signature(parsed), 'Repeat/ending changed')
        relationship_signature(parsed, evidence)
        require(
            relationship_inventory(parsed) == relationship_inventory(score),
            'Unexpected tie/slur change',
        )
        require(len(relationship_inventory(parsed)['slurs']) == 1, '4867 false slur returned')
        # music21 currently drops extend metadata. The research adapter reattaches the
        # independently retained, checked lineage after semantic import/export.
        for note in parsed.recurse().notesAndRests:
            note.lyrics = [l for l in note.lyrics if l.text]
        rtfile = out / f'{name}-adapter-roundtrip.musicxml'
        parsed.write('musicxml', fp=str(rtfile))
        rtbase = ET.fromstring(rtfile.read_bytes())
        raw_count = len(rtbase.findall('.//lyric/extend'))
        rt = add_extensions(rtbase, spans)
        save_xml(rt, rtfile)
        require(extension_signature(rt) == sig, 'Research adapter extension roundtrip failed')
        rtscore = converter.parse(str(rtfile))
        require(validate(source, rtscore, shift, 'key').ok, 'Roundtrip V3 guard failed')
        roundtrips[name] = {
            'adapter_signature_equal': True,
            'unadapted_music21_extend_count': raw_count,
            'transparent_limitation': 'Unadapted music21 drops extension semantics; use this research adapter. Production export remains unchanged.',
        }
        xmlreports[name] = xml_curve_audit(
            (out / f'{name}-final-experimental.musicxml').read_text()
        )
        scores[name] = score
    require(
        signatures['Bb'] == signatures['A'] == signatures['G'],
        'Transposed extender lineage mismatch',
    )
    dump(
        out / 'final-lyric-extender-validation.json',
        {
            'specification': 'https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/extend/',
            'visible_strokes': 50,
            'source_lineage_serializable_strokes': 49,
            'semantic_spans': spans,
            'exceptions': exceptions,
            'source_extent_caveat': 'Two earlier lower-row extents not persisted; prior owner-approved underlay and explicit tie endpoints retained, not mirrored source bounds.',
            'type_counts': {
                'start': len(spans),
                'continue': sum(max(0, len(s['path']) - 2) for s in spans),
                'stop': len(spans),
            },
            'roundtrips': roundtrips,
            'extension_signatures_equal_all_keys': True,
            'semantic_coverage': 'PARTIAL_M28_EXCLUDED',
            'independent_ground_truth': 0,
        },
    )
    playback = playback_review(source, graph)
    try:
        expanded = source.expandRepeats()
        route = [m.number for m in expanded.parts[0].getElementsByClass(stream.Measure)]
        playback['music21_candidate_expansion'] = {
            'route': route,
            'owner_verified': False,
            'used_for_final_performance': False,
        }
    except (ExpanderException, stream.StreamException) as e:
        playback['music21_candidate_expansion'] = {
            'error_type': type(e).__name__,
            'error': str(e),
            'used_for_final_performance': False,
        }
    playback['source_vs_conventions'] = (
        'Printed ending groups do not establish an unambiguous m15–17 repeat exit: no backward repeat at16. No fabricated repeat at16 or m28 ancestry is added.'
    )
    playback['hypotheses'] = [
        {
            'id': 'strict-printed-signs',
            'missing_information': 'm15–17 ending route is not uniquely paired with a backward repeat',
            'approved': False,
        },
        {
            'id': 'assume-unprinted-repeat-at16',
            'rejected_for_output': 'Requires a nonexistent/unapproved repeat sign',
            'approved': False,
        },
    ]
    dump(out / 'final-repeat-playback-status.json', playback)
    dump(
        out / 'final-semantic-integrity.json',
        {
            'guards': guards,
            'xml_curve_checks': xmlreports,
            'event_cores': 169,
            'chords': 24,
            'syllable_wording_rows_and_onsets': 167,
            'only_new_semantic_elements': 'Explicit checked lyric extensions and three previously approved section headings. No note/rest cores, harmonies, lyric wording/onsets, ties/slurs or repeat signs changed. Research export warnings added; inherited unverified title preserved in miscellaneous metadata.',
            '4867_slur_absent': True,
            'source_completeness': 'UNVERIFIED',
            'full_repeat_playback': 'UNRESOLVED',
            'independent_ground_truth': 0,
        },
    )
    print('Semantic source/A/G and 49 extension paths validated', flush=True)
    images = []
    renders = []
    for name in ['A', 'G']:
        picture, report = render_score(name, scores[name], inventory, graph, marks, evidence, out)
        images.append(picture)
        renders.append(report)
        require(
            report['events_rendered'] == 169
            and report['syllables_rendered'] == 167
            and report['chords_rendered'] == 24
            and report['continuation_strokes_rendered'] == 50,
            'Incomplete render components',
        )
        print(name, 'newly rendered 9 systems', flush=True)
    original = framed(
        Image.open(SOURCE_DIR / 'source.png'),
        'Original Bb source evidence only; immutable original page raster',
    )
    original.save(out / 'Bb-source-evidence.png')
    heights = [round(p.height * 1000 / p.width) for p in [original, *images]]
    comp = Image.new('RGB', (3000, max(heights)), 'white')
    for j, (p, h) in enumerate(zip([original, *images], heights)):
        comp.paste(p.resize((1000, h), Image.Resampling.LANCZOS), (j * 1000, 0))
    comp.save(out / 'Bb-A-G-final-comparison.png')
    dump(
        out / 'final-rendering-validation.json',
        {
            'targets': renders,
            'warning': 'DEVELOPER-ONLY / INCOMPLETE / NOT FOR PERFORMANCE OR PRINTING',
            'independent_optical_validation': False,
        },
    )
    require(
        all(file_hashes(Path(folder)) == files for folder, files in snapshots.items()),
        'Historical file changed',
    )
    for n, k in [
        ('source.png', 'source_sha256'),
        ('recognized.omr', 'omr_sha256'),
        ('visual-graph.json', 'graph_sha256'),
    ]:
        require(sha(SOURCE_DIR / n) == src[k], 'Original source changed')
    dump(
        out / 'final-preservation-verification.json',
        {
            'source_hashes': src,
            'historical_directory_file_hashes': snapshots,
            'all_historical_files_unchanged': True,
            'unbound_directory_additions': additions,
            'frozen_artifact_content_waivers': 0,
            'raw_omr_and_protection_masks_unchanged': True,
            'production_files_modified': False,
            'source_pdf_modified': False,
        },
    )
    dump(
        out / 'final-runtime.json',
        {
            'wall_seconds_before_freeze': time.perf_counter() - started,
            'parent_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'child_peak_rss_bytes': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            'rss_units': 'bytes on Darwin; separate parent/child peaks, not aggregate simultaneous memory',
            'platform': platform.platform(),
        },
    )
    dump(
        out / 'prediction-freeze.json',
        {
            'files': file_hashes(out),
            'before_agent_visual_inspection': True,
            'base_sha': START,
            'protocol_sha256': sha(ROOT / 'docs/V4_GT17_FINAL_PROTOCOL.json'),
            'producer_sha256': {
                p.name: sha(p)
                for p in [
                    Path(__file__),
                    ROOT / 'scripts/research/gt17_final_semantics.py',
                    ROOT / 'scripts/research/gt17_final_render.py',
                    ROOT / 'scripts/research/gt17b_notation.py',
                ]
            },
            'software': {
                'python': platform.python_version(),
                'music21': __import__('music21').__version__,
                'Pillow': __import__('PIL').__version__,
            },
        },
    )
    print('Prediction freeze complete:', out, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    run(p.parse_args().output)
