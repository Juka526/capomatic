"""Owner-confirmed additions only; reuse frozen notation and lyric geometry."""

import argparse
import copy
from pathlib import Path

import numpy as np
from music21 import converter, stream, harmony
from PIL import Image

from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from backend.omr_v3.chords import chord_text
from scripts.research.gt11_complete_measure import read, require, events_of, event_signature
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.gt13a5_lyric_layout import union, contacts, verify_freeze
from scripts.research.gt14b_lyric_extenders import (
    SOURCE,
    SOURCE_DIR,
    SIZE,
    VIEW,
    extender,
    safety,
    panel,
    native,
    verify_binding,
)
from scripts.research.gt14c_continuation_audit import GT14A, GT14B, candidate_record
from scripts.research.gt13a2_provisional import ink_distance
from scripts.research.paired_ground_truth_01 import dump, file_hashes, sha

ROOT = Path(__file__).resolve().parents[2]
GT14C = Path('/private/tmp/capomatic-v4-gt14c/gt14c-final-output')
BINDING = ROOT / 'docs/evidence/GT14D_OWNER_BINDING.json'
PROTOCOL = ROOT / 'docs/V4_GT14D_PROTOCOL.json'


def approved_records(binding_path, candidates):
    binding = read(binding_path)
    require(
        binding['classification'] == 'OWNER_VERIFIED_SOURCE'
        and binding['independent_ground_truth'] is False
        and binding['source_ink_replacement_authorized'] is False,
        'Invalid approval scope',
    )
    require(
        sha(binding_path.parent / binding['approval_file']) == binding['approval_sha256'],
        'Approval changed',
    )
    require(binding['packet_files'], 'Missing packet binding')
    for name, digest in binding['packet_files'].items():
        require(sha(Path(name)) == digest, f'Changed review packet: {name}')
    require(
        len(candidates) == len(binding['approved_ids']) == 3
        and len({r['id'] for r in candidates}) == len(set(binding['approved_ids'])) == 3
        and {r['id'] for r in candidates} == set(binding['approved_ids']),
        'Approval/case identity mismatch',
    )
    result = copy.deepcopy(candidates)
    for r in result:
        require(
            r['classification'] == 'AGENT_VISUAL_CANDIDATE' and r['owner_response'] is None,
            'Historical candidate changed',
        )
        r['historical_classification'] = r['classification']
        r['classification'] = 'OWNER_VERIFIED_SOURCE'
        r['owner_response'] = 'OWNER_CONFIRMED'
        r['independent_ground_truth'] = False
        r['new_rendering_authorized'] = 'STANDALONE_EXPERIMENT_ONLY'
        r['note_context']['new_stroke_association_evidence'] = 'OWNER_VERIFIED_SOURCE'
        r['approval_sha256'] = binding['approval_sha256']
    return result


def additions_metrics(parts, base, lyrics, prior_extenders):
    require(
        len(parts) == 3 and len(prior_extenders) == 3 and len(lyrics) == 14,
        'Component count mismatch',
    )
    text = {**lyrics, **prior_extenders}
    metrics = safety(parts, base, text)
    all_text = union([*text.values(), *parts.values()])
    old_text = union(list(text.values()))
    fixed_support = (np.asarray(base) > 0) & ~(np.asarray(old_text) > 0)
    all_support = np.asarray(all_text) > 0
    metrics['all_lyric_music_contact_pixels'] = int(np.count_nonzero(fixed_support & all_support))
    metrics['all_text_component_contact_pairs'] = contacts({**text, **parts})
    distance = ink_distance(Image.fromarray(fixed_support.astype('uint8') * 255))
    metrics['minimum_all_lyrics_to_fixed_ink_distance_px'] = float(distance[all_support].min())
    added = union(list(parts.values()))
    combined = union([base, added])
    metrics['old_ink_intensities_unchanged'] = bool(
        np.array_equal(
            np.asarray(combined)[np.asarray(base) > 0], np.asarray(base)[np.asarray(base) > 0]
        )
    )
    require(
        not metrics['extender_to_music_contacts']
        and not metrics['extender_to_lyric_contacts']
        and not metrics['all_lyric_music_contact_pixels']
        and not metrics['all_text_component_contact_pairs']
        and metrics['minimum_extender_to_existing_ink_distance_px'] > 0
        and metrics['minimum_all_lyrics_to_fixed_ink_distance_px'] > 0
        and metrics['old_ink_intensities_unchanged'],
        'Collision or preservation failure',
    )
    return combined, metrics


def run(out):
    require(not out.exists(), 'Fresh output directory required')
    verify_binding()
    verify_freeze(GT14A)
    verify_freeze(GT14B)
    for name, digest in read(GT14C / 'audit-freeze.json')['files'].items():
        require(sha(GT14C / name) == digest, 'GT14C audit changed')
    histories = {str(p): file_hashes(p) for p in (GT14A, GT14B, GT14C)}
    inventory = read(GT14C / 'lyric-continuation-inventory.json')
    records = approved_records(BINDING, inventory['new_candidates'])
    protocol = read(PROTOCOL)
    require(sha(SOURCE) == inventory['source_sha256'], 'Wrong source')
    graph = read(SOURCE_DIR / 'visual-graph.json')
    original = Image.open(SOURCE)
    source = converter.parse(str(GT14A / 'owner-augmented-source.musicxml'))
    for r in inventory['new_candidates']:
        again = candidate_record(r, original, graph, source)
        require(
            again['source_bbox'] == r['source_bbox']
            and again['note_context'] == r['note_context']
            and again['tie_source_record'] == r['tie_source_record']
            and again['tie_relations'] == r['tie_relations'],
            'Candidate source/context mismatch',
        )
    measures = list(source.parts[0].getElementsByClass(stream.Measure))
    require(sum(len(events_of(m)) for m in measures[4:8]) == 13, '13 music events required')
    require(
        sum(len(n.lyrics) for m in measures[4:8] for n in events_of(m)) == 14,
        '14 syllables required',
    )
    require(
        [chord_text(c) for m in measures[4:8] for c in m.getElementsByClass(harmony.ChordSymbol)]
        == ['Gm', 'Bb/D', 'Eb'],
        '3 confirmed chords required',
    )
    require(
        read(GT14B / 'owner-interpretation-layer.json') == inventory['confirmed_records'],
        'Old interpretation changed',
    )
    out.mkdir()
    dump(out / 'owner-confirmed-interpretation-layer.json', records)
    dump(
        out / 'input-freeze.json',
        {
            'history_files': histories,
            'protocol_sha256': sha(PROTOCOL),
            'approval_binding_sha256': sha(BINDING),
            'source_sha256': sha(SOURCE),
            'producer_sha256': sha(Path(__file__)),
        },
    )
    reports, images, guards = [], [], {}
    guards['source_roundtrip'] = validate(
        source, converter.parse(str(GT14A / 'owner-augmented-source.musicxml')), 0, 'key'
    ).to_dict()
    for prior, target, shift in zip(
        read(GT14B / 'rendering-validation.json'), ['A', 'G'], [-1, -3]
    ):
        old_report = next(
            r for r in read(GT14A / 'rendering-validation.json') if r['target'] == target
        )
        dy = protocol['baseline_displacement'][target]
        require(
            old_report['lyric_displacement_dy'] == dy and prior['target'] == target,
            'Frozen layout mismatch',
        )
        base = Image.open(GT14B / f'{target}-combined-alpha.png').copy()
        require(base.mode == 'L' and base.size == SIZE, 'Page-coordinate mismatch')
        lyrics = {p.name: Image.open(p).copy() for p in GT14A.glob(f'{target}-lyric-*-alpha.png')}
        old_extenders = {
            p.name: Image.open(p).copy() for p in GT14B.glob(f'{target}-extender-*-alpha.png')
        }
        parts, placements = {}, []
        for r in records:
            name = r['id']
            parts[name] = extender(SIZE, r['source_bbox'], dy, VIEW)
            b = parts[name].getbbox()
            require(
                np.count_nonzero(np.asarray(parts[name])) == (b[2] - b[0]) * 2,
                'Stroke component lost',
            )
            placements.append(
                {
                    'id': name,
                    'row': r['row'],
                    'held_syllable': r['associated_syllable_candidate'],
                    'source_bbox': r['source_bbox'],
                    'rendered_bounds': list(b),
                    'dy': dy,
                    'source_bbox_pixel_center_residual_y': (b[1] + b[3] - 1) / 2
                    - (r['source_bbox'][1] + r['source_bbox'][3] - 1) / 2
                    - dy,
                    'width_preserved': b[2] - b[0] == r['source_bbox'][2] - r['source_bbox'][0],
                    'attachment': 'CONFIRMED_HELD_SYLLABLE_AT_TIED_STOP_NO_NEW_TOKEN',
                }
            )
            parts[name].save(out / f'{target}-{name}-alpha.png')
        alpha, metrics = additions_metrics(parts, base, lyrics, old_extenders)
        require(
            prior['existing_notehead_max_residual_px'] <= 0.5, 'Existing notehead criterion failed'
        )
        score = copy.deepcopy(source)
        summary = transpose_score(score, shift, 'key')
        disk = converter.parse(str(GT14A / f'{target}-transposed.musicxml'))
        guards[target] = {
            'in_memory': validate(source, score, shift, 'key', summary).to_dict(),
            'frozen_serialized': validate(source, disk, shift, 'key', summary).to_dict(),
        }
        require(all(r['ok'] for r in guards[target].values()), 'Full V3 guard failure')
        require(
            full_lyric_signature(source) == full_lyric_signature(disk), 'Lyric semantics changed'
        )
        require(
            [event_signature(m) for m in score.parts[0].getElementsByClass(stream.Measure)]
            == [event_signature(m) for m in disk.parts[0].getElementsByClass(stream.Measure)],
            'Frozen notes/ties changed',
        )
        image = panel(
            native(alpha).crop(VIEW),
            f'{target} major: 13 events / 3 chords / 14 syllables / 6 confirmed extenders (3 added)',
        )
        image.save(out / f'predicted-{target.lower()}.png')
        alpha.save(out / f'{target}-combined-alpha.png')
        images.append(image)
        reports.append(
            {
                'target': target,
                **metrics,
                'placements': placements,
                'clipping': [],
                'confirmed_events': 13,
                'confirmed_chords': 3,
                'confirmed_syllables': 14,
                'prior_extenders_preserved': 3,
                'new_confirmed_extenders': 3,
                'total_extenders': 6,
                'extra_syllable_glyphs': 0,
                '5747_interpretation_preserved': True,
                'old_notehead_max_anchor_residual_px': prior['existing_notehead_max_residual_px'],
                'SOURCE_VERIFICATION': 'OWNER_VERIFIED_SCOPED_CONTENT_NOT_INDEPENDENT_COMPLETENESS',
                'RENDERING_COMPLETENESS': 'SIX_INVENTORIED_CONTINUATION_MARKS_RENDERED',
                'VISUAL_QUALITY': 'PENDING_POST_FREEZE_AGENT_REVIEW',
            }
        )
    require(guards['source_roundtrip']['ok'], 'Source roundtrip failure')
    orig = panel(original.crop(VIEW), 'Unchanged original Bb source, second system')
    sheet = Image.new('RGB', (orig.width, orig.height * 3), 'white')
    for i, p in enumerate([orig, *images]):
        sheet.paste(p, (0, orig.height * i))
    sheet.save(out / 'comparison-contact-sheet.png')
    dump(out / 'lyric-extender-validation.json', reports)
    dump(out / 'semantic-integrity.json', guards)
    require(
        all(file_hashes(Path(p)) == h for p, h in histories.items()), 'Historical artifacts changed'
    )
    require(sha(SOURCE) == inventory['source_sha256'], 'Original source changed')
    dump(
        out / 'validation-summary.json',
        {
            'status': 'SIX_CONFIRMED_EXTENDERS_RENDERED_PENDING_VISUAL_REVIEW',
            'history_unchanged': True,
            'full_V3_guards': 'PASS',
            'independent_labels': 0,
            'new_syllables': 0,
            'new_music_events': 0,
            'composition_or_ink_replacement_authorized': False,
        },
    )
    dump(
        out / 'prediction-freeze.json',
        {'files': file_hashes(out), 'phase': 'BEFORE_AGENT_VISUAL_INSPECTION_NO_REFERENCE_ACCESS'},
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    run(parser.parse_args().out)
