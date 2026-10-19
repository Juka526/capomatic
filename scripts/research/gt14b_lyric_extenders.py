"""Add only owner-reclassified lyric continuation strokes to frozen GT14A canvases."""

import argparse
import copy
from fractions import Fraction
from pathlib import Path

import numpy as np
from music21 import converter, stream
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt11_complete_measure import events_of, event_signature, read, require
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.gt13a5_lyric_layout import union, contacts, verify_freeze
from scripts.research.gt13a2_provisional import ink_distance
from scripts.research.gt14a_confirmed_context import SOURCE, SOURCE_DIR, SIZE, VIEW, native
from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes

ROOT = Path(__file__).resolve().parents[2]
PRIOR = Path('/private/tmp/capomatic-v4-gt14a/gt14a-output')
PROTOCOL = ROOT / 'docs/V4_GT14B_PROTOCOL.json'
BINDING = ROOT / 'docs/evidence/GT14B_OWNER_BINDING.json'


def verify_binding(path=BINDING):
    binding = read(path)
    require(binding['classification'] == 'OWNER_VERIFIED_SOURCE', 'Owner classification required')
    require(binding['independent_ground_truth'] is False, 'Not independent ground truth')
    require(
        sha(path.parent / binding['approval_file']) == binding['approval_sha256'],
        'Approval changed',
    )
    for name, digest in binding['files'].items():
        require(sha(Path(name)) == digest, f'Frozen evidence mismatch: {name}')
    return binding


def extender(size, bbox, dy, viewport):
    """New 2px straight stroke; bbox is source geometry, never a removal mask."""
    require(len(bbox) == 4 and all(type(v) is int for v in bbox), 'Integer geometry required')
    require(type(dy) is int and dy >= 0, 'Invalid row displacement')
    x0, y0, x1, y1 = bbox
    require(x0 < x1 and y0 < y1, 'Empty geometry')
    y = (y0 + y1 - 1) // 2 + dy
    bounds = (x0, y, x1, y + 2)
    require(
        viewport[0] <= x0 < x1 <= viewport[2]
        and viewport[1] <= y < y + 2 <= viewport[3]
        and 0 <= x0 < x1 <= size[0]
        and 0 <= y < y + 2 <= size[1],
        'Clipped extender',
    )
    mask = Image.new('L', size)
    ImageDraw.Draw(mask).rectangle((x0, y, x1 - 1, y + 1), fill=255)
    return mask


def safety(extenders, base, lyrics):
    added = union(list(extenders.values()))
    old = np.asarray(base) > 0
    text = np.asarray(union(list(lyrics.values()))) > 0
    support = np.asarray(added) > 0
    pairs = contacts({**lyrics, **extenders})
    return {
        'extender_to_music_contacts': int(np.count_nonzero(support & old & ~text)),
        'extender_to_lyric_contacts': int(np.count_nonzero(support & text)),
        'lyric_lyric_and_extender_pairs': pairs,
        'minimum_extender_to_existing_ink_distance_px': float(ink_distance(base)[support].min()),
        'added_pixels': int(support.sum()),
        'existing_alpha_preserved': bool(
            np.array_equal(
                np.maximum(np.asarray(base), np.asarray(added))[~support],
                np.asarray(base)[~support],
            )
        ),
    }


def event(score, measure, onset):
    m = list(score.parts[0].getElementsByClass(stream.Measure))[measure - 1]
    found = [n for n in events_of(m) if Fraction(n.getOffsetInHierarchy(m)) == Fraction(onset)]
    require(len(found) == 1, 'Unique source event required')
    return found[0]


def context(record, graph, source):
    symbol = graph['symbols'][record['symbol_id']]
    require(symbol['shape'] == record['original_shape'], 'Raw OMR observation changed')
    require(symbol['geometry']['bbox'] == record['source_bbox'], 'Source bbox changed')
    n = event(source, record['measure'], record['onset'])
    relations = [r for r in graph['relations'] if record['symbol_id'] in (r['source'], r['target'])]
    require(relations, 'Original SIG lineage missing')
    result = {
        **record,
        'original_symbol': symbol,
        'original_relations': relations,
        'classification': 'OWNER_VERIFIED_SOURCE',
        'independent_ground_truth': False,
        'row_context_basis': 'SOURCE_ONLY_VISUAL_ROW_POSITION_AND_CONFIRMED_LYRIC_TIE_CONTEXT',
        'context_pitch': n.pitch.nameWithOctave,
    }
    if record['interpretation'] == 'LYRIC_EXTENDER':
        prior = event(source, record['syllable_source_measure'], record['syllable_onset'])
        require(
            n.tie and n.tie.type == 'stop' and prior.tie and prior.tie.type == 'start',
            'Tie context missing',
        )
        require(n.pitch == prior.pitch, 'Held syllable endpoints differ')
        syllable = [x.text for x in prior.lyrics if int(x.number) == record['row']]
        require(syllable == [record['held_syllable']], 'Confirmed held syllable mismatch')
        require(
            record['tie_relation'] in graph['symbols'],
            'Source tie object missing',
        )
        result['held_note_pitch'] = prior.pitch.nameWithOctave
        result['new_syllables'] = 0
    else:
        require(
            [x.text for x in n.lyrics if int(x.number) == record['row']] == ['하'],
            'Existing 하 missing',
        )
        result['new_glyph'] = False
        result['reason'] = (
            'Already represented by existing confirmed upper 하; do not duplicate source stroke'
        )
    return result


def panel(image, title):
    out = Image.new('RGB', (image.width, image.height + 150), 'white')
    draw = ImageDraw.Draw(out)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20)
    for i, line in enumerate(
        [
            'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING',
            title,
            'OWNER_VERIFIED_SOURCE / NOT_INDEPENDENT_GROUND_TRUTH; 3 classified lyric extenders added.',
            'Newly typeset text only; no source ink removal or original lyric-pixel composition.',
        ]
    ):
        draw.text((10, 8 + i * 30), line, font=font, fill='black')
    out.paste(image, (0, 150))
    return out


def run(out):
    require(not out.exists(), 'Fresh output directory required')
    binding = verify_binding()
    verify_freeze(PRIOR)
    history = file_hashes(PRIOR)
    protocol = read(PROTOCOL)
    require(protocol['stroke_width_px'] == 2, 'Frozen stroke contract changed')
    source = converter.parse(str(PRIOR / 'owner-augmented-source.musicxml'))
    graph = read(SOURCE_DIR / 'visual-graph.json')
    interpretations = [context(r, graph, source) for r in protocol['interpretations']]
    require(len(interpretations) == 4, 'Four owner interpretations required')
    records = [r for r in interpretations if r['interpretation'] == 'LYRIC_EXTENDER']
    require(len(records) == 3 and len({r['symbol_id'] for r in records}) == 3, 'Duplicate extender')
    out.mkdir()
    dump(out / 'owner-interpretation-layer.json', interpretations)
    dump(
        out / 'input-freeze.json',
        {
            'owner_binding': binding,
            'protocol_sha256': sha(PROTOCOL),
            'producer_sha256': sha(Path(__file__)),
            'history_files': history,
        },
    )
    reports, panels, guards = [], [], {}
    original = panel(Image.open(SOURCE).crop(VIEW), 'Unchanged Bb source second system')
    original.save(out / 'original-bb.png')
    source_copy = copy.deepcopy(source)
    guards['source_roundtrip'] = validate(
        source, converter.parse(str(PRIOR / 'owner-augmented-source.musicxml')), 0, 'key'
    ).to_dict()
    for old_report, target, shift in zip(
        read(PRIOR / 'rendering-validation.json'), ['A', 'G'], [-1, -3]
    ):
        require(
            old_report['target'] == target and old_report['collision_safety'] == 'PASS',
            'Prior rendering unsafe',
        )
        predicted = copy.deepcopy(source)
        summary = transpose_score(predicted, shift, 'key')
        disk = converter.parse(str(PRIOR / f'{target}-transposed.musicxml'))
        guards[target] = {
            'in_memory': validate(source, predicted, shift, 'key', summary).to_dict(),
            'frozen_serialized': validate(source, disk, shift, 'key', summary).to_dict(),
        }
        require(all(v['ok'] for v in guards[target].values()), 'Full V3 guard failed')
        require(full_lyric_signature(source) == full_lyric_signature(disk), 'Lyrics changed')
        require(
            [event_signature(m) for m in predicted.parts[0].getElementsByClass(stream.Measure)]
            == [event_signature(m) for m in disk.parts[0].getElementsByClass(stream.Measure)],
            'Frozen event geometry/semantics changed',
        )
        base = Image.open(PRIOR / f'{target}-combined-alpha.png').copy()
        require(base.size == SIZE and base.mode == 'L', 'Raster alignment mismatch')
        lyrics = {p.stem: Image.open(p).copy() for p in PRIOR.glob(f'{target}-lyric-*-alpha.png')}
        require(len(lyrics) == 14, '14 existing lyric syllables required')
        parts, placement = {}, []
        for record in records:
            sid = record['symbol_id'].split(':')[-1]
            dy = old_report['lyric_displacement_dy']
            mask = extender(SIZE, record['source_bbox'], dy, VIEW)
            parts[f'extender-{sid}'] = mask
            placement.append(
                {
                    'symbol_id': record['symbol_id'],
                    'row': record['row'],
                    'held_syllable': record['held_syllable'],
                    'source_bbox': record['source_bbox'],
                    'row_dy': dy,
                    'rendered_bounds': list(mask.getbbox()),
                    'source_x_width_preserved': True,
                    'source_line_center_residual_y_px': (
                        (mask.getbbox()[1] + mask.getbbox()[3] - 1) / 2
                        - (record['source_bbox'][1] + record['source_bbox'][3] - 1) / 2
                        - dy
                    ),
                    'semantic_attachment': 'HELD_SYLLABLE_AT_TIED_STOP_NO_NEW_TOKEN',
                }
            )
            mask.save(out / f'{target}-extender-{sid}-alpha.png')
        metrics = safety(parts, base, lyrics)
        require(
            not metrics['extender_to_music_contacts']
            and not metrics['extender_to_lyric_contacts']
            and not metrics['lyric_lyric_and_extender_pairs']
            and metrics['minimum_extender_to_existing_ink_distance_px'] > 0,
            'New extender collision; do not silently move frozen layers',
        )
        alpha = union([base, *parts.values()])
        alpha.save(out / f'{target}-combined-alpha.png')
        image = panel(
            native(alpha).crop(VIEW),
            f'{target} major: 13 events / 3 chords / 14 syllables / 3 new extenders',
        )
        image.save(out / f'predicted-{target.lower()}.png')
        panels.append(image)
        report = {
            'target': target,
            **metrics,
            'placement': placement,
            'clipping': [],
            'events': 13,
            'chords': 3,
            'lyric_syllables': 14,
            'new_extenders': 3,
            'new_music_articulations': 0,
            '5747_extra_glyphs': 0,
            'existing_notehead_max_residual_px': old_report['old_notehead_max_residual_px'],
            'existing_lyric_music_contacts': old_report['lyric_music_unique_contact_pixels'],
            'previous_masks_byte_unchanged': True,
            'SOURCE_VERIFICATION': 'OWNER_VERIFIED_SCOPED_CONTENT_NOT_INDEPENDENT',
            'RENDERING_COMPLETENESS': 'SCOPED_THREE_EXTENDERS_RENDERED_NOT_A_FULL_SCORE',
            'VISUAL_QUALITY': 'PENDING_POST_FREEZE_AGENT_INSPECTION',
        }
        reports.append(report)
    sheet = Image.new('RGB', (original.width, original.height * 3), 'white')
    for i, p in enumerate([original, *panels]):
        sheet.paste(p, (0, original.height * i))
    sheet.save(out / 'comparison-contact-sheet.png')
    require(guards['source_roundtrip']['ok'], 'Source guard failed')
    require(full_lyric_signature(source_copy) == full_lyric_signature(source), 'Source mutated')
    require(
        file_hashes(PRIOR) == history and sha(SOURCE) == binding['files'][str(SOURCE)],
        'Historical source changed',
    )
    dump(out / 'semantic-integrity.json', guards)
    dump(out / 'rendering-validation.json', reports)
    dump(
        out / 'validation-summary.json',
        {
            'status': 'SCOPED_RENDER_COMPLETE_PENDING_VISUAL_REVIEW',
            'independent_labels': 0,
            'ownership_or_composition_authorized': False,
            'history_unchanged': True,
            'full_V3_guards': 'PASS',
        },
    )
    dump(
        out / 'prediction-freeze.json',
        {
            'files': file_hashes(out),
            'phase': 'BEFORE_AGENT_VISUAL_INSPECTION_NO_TARGET_REFERENCE_ACCESS',
        },
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    run(parser.parse_args().out)
