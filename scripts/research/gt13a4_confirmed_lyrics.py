"""Separate post-owner-reply run, with fixed source lyric baseline and strict collision audit."""

import argparse
import copy
from fractions import Fraction
from pathlib import Path

import numpy as np
from fontTools.ttLib import TTFont
from music21 import converter, stream
from PIL import Image, ImageFont

from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt11_complete_measure import event_signature, events_of, require, read
from scripts.research.gt12_render_context import (
    KOREAN_FONT,
    canonical_box,
    ink_bbox,
    text_mask,
)
from scripts.research.gt13a_full_system import CROP, GT12, scaffold
from scripts.research.gt13a4_system_notation import ROOT, PRIOR, PROTOCOL, panel
from scripts.research.paired_ground_truth_01 import dump, file_hashes, sha

INITIAL = ROOT / 'gt13a4-output'
APPROVAL = ROOT / 'docs/evidence/GT13A4_OWNER_ASSOCIATION_REPLY.json'


def full_lyric_signature(score):
    """GT12's signature is m3-only; this new study checks every measure and event."""
    return [
        [
            [[(l.number, l.text, l.syllabic) for l in n.lyrics] for n in events_of(m)]
            for m in part.getElementsByClass(stream.Measure)
        ]
        for part in score.parts
    ]


def approved_associations(audit, record):
    require(
        record['classification'] == 'OWNER_VERIFIED_LYRIC_ASSOCIATION'
        and record['independent_ground_truth'] is False,
        'Actual owner association confirmation required; no independent claim',
    )
    require(
        record['messages'][0]['answer'] == '원본 대조 후 대응 후보 전체 확인',
        'Association approval missing',
    )
    require(
        record['messages'][1]['answer'] == '아직 미확인 — 목적지는 보류'
        and record['tie_destination_owner_verified'] is False,
        'Tie withholding must remain explicit',
    )
    result = copy.deepcopy(audit)
    result['status'] = 'OWNER_VERIFIED_LYRIC_ASSOCIATION'
    for m in result['measures']:
        m['note_association_status'] = 'OWNER_VERIFIED_LYRIC_ASSOCIATION'
        for e in m['events']:
            e['association_status'] = 'OWNER_VERIFIED_LYRIC_ASSOCIATION'
            e['prior_classification'] = e['classification']
            e['classification'] = 'OWNER_VERIFIED_LYRIC_ASSOCIATION'
    return result


def apply_lyrics(score, audit):
    result = copy.deepcopy(score)
    measures = list(result.parts[0].getElementsByClass(stream.Measure))
    for m in audit['measures']:
        source = measures[m['printed_measure'] - 1]
        events = events_of(source)
        require(len(events) == len(m['events']), 'Lyric event mismatch')
        for n, e in zip(events, m['events']):
            require(
                Fraction(n.getOffsetInHierarchy(source)) == Fraction(e['onset'])
                and Fraction(n.quarterLength) == Fraction(e['duration'])
                and (n.pitch.nameWithOctave if n.isNote else None) == e['pitch']
                and getattr(n.tie, 'type', None) == e['tie'],
                'Owner association event identity differs',
            )
            n.lyrics = []
            if e['candidate_relation'] == 'SYLLABLE_START':
                require(n.isNote, 'Rest cannot receive syllable')
                for row, key in enumerate(('upper_candidate', 'lower_candidate'), 1):
                    n.addLyric(e[key], lyricNumber=row)
    return result


def render_lyric_parts(size, audit, source):
    font = ImageFont.truetype(str(KOREAN_FONT), 44)
    cmap = TTFont(KOREAN_FONT).getBestCmap()
    descent = max(canonical_box(font, c)[3] - 2 * font.size for c in '주님의사막')
    baselines = [
        ink_bbox(source, w)[3] - descent for w in [[1480, 588, 1730, 632], [1480, 635, 1730, 688]]
    ]
    masks = {}
    rows = []
    for m in audit['measures']:
        for e in m['events']:
            if e['pitch'] is None:
                continue
            for row, key in enumerate(('upper_candidate', 'lower_candidate')):
                continuation = e['candidate_relation'] == 'TIED_CONTINUATION_NO_NEW_SYLLABLE'
                char = '—' if continuation else e[key]
                require(all(ord(c) in cmap for c in char), 'Font lacks confirmed lyric glyph')
                x = (e['source_bbox'][0] + e['source_bbox'][2]) / 2
                mask, info = text_mask(size, font, char, center_x=x, baseline=baselines[row])
                name = f'm{m["printed_measure"]}-{e["event_id"]}-row{row+1}'
                masks[name] = mask
                rows.append(
                    {
                        'component': name,
                        'event_id': e['event_id'],
                        'printed_measure': m['printed_measure'],
                        'row': row + 1,
                        'text': char,
                        'new_syllable': not continuation,
                        'continued_syllable': e[key] if continuation else None,
                        'evidence': 'OWNER_VERIFIED_LYRIC_ASSOCIATION',
                        **info,
                    }
                )
    return masks, rows, baselines


def lyric_contacts(lyric_parts, music):
    union = np.zeros(np.asarray(music).shape, bool)
    contacts = []
    mm = np.asarray(music) > 0
    for name, mask in lyric_parts.items():
        overlap = (np.asarray(mask) > 0) & mm
        if overlap.any():
            contacts.append({'component': name, 'pixels': int(overlap.sum())})
            union |= overlap
    return contacts, Image.fromarray(union.astype('uint8') * 255)


def run(out):
    require(not out.exists(), 'New follow-up run required')
    frozen = read(INITIAL / 'prediction-freeze.json')
    require(
        all(sha(INITIAL / p) == h for p, h in frozen['files'].items()),
        'Initial header predictions changed',
    )
    require(
        sha(INITIAL / 'producer-snapshot-gt13a4_system_notation.py') == frozen['producer_sha256'],
        'Initial producer snapshot mismatch',
    )
    require(
        sha(APPROVAL) == read(PROTOCOL)['owner_association_followup']['approval_sha256'],
        'Actual owner reply bytes changed',
    )
    histories = {
        str(p): file_hashes(p)
        for p in (
            INITIAL,
            PRIOR,
            GT12,
            Path('/private/tmp/capomatic-v4-gt13a2/gt13a2-final-output'),
        )
    }
    audit = approved_associations(read(INITIAL / 'lyric-association-audit.json'), read(APPROVAL))
    source_path = Path(
        '/private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output/predictions/baseline-exec/source/source.png'
    )
    require(
        sha(source_path) == read(INITIAL / 'input-freeze.json')['source_sha256'], 'Source changed'
    )
    source = Image.open(source_path)
    size = (source.width, 750)
    inv = read(PRIOR / 'source-event-inventory.json')
    staff = inv['staff']
    out.mkdir()
    (out / 'actual-owner-association-reply.json').write_bytes(APPROVAL.read_bytes())
    dump(out / 'lyric-association-audit.json', audit)
    (out / 'outgoing-tie-evidence.json').write_bytes(
        (INITIAL / 'outgoing-tie-evidence.json').read_bytes()
    )
    dump(
        out / 'input-freeze.json',
        {
            'base': read(PROTOCOL)['base'],
            'history_files': histories,
            'source_sha256': sha(source_path),
            'protocol_sha256': sha(PROTOCOL),
            'actual_owner_reply_sha256': sha(APPROVAL),
            'owner_reply_context': {
                'source_review_packet_sha256': sha(INITIAL / 'owner-review/packet.json'),
                'proposed_association_audit_sha256': sha(INITIAL / 'lyric-association-audit.json'),
            },
            'binding': 'Post-reply coordinator binding; no digital owner signature or independent reviewer claim',
        },
    )
    source_score = converter.parse(str(INITIAL / 'source-with-header-context.musicxml'))
    augmented = apply_lyrics(source_score, audit)
    augmented.write('musicxml', fp=str(out / 'owner-associated-source.musicxml'))
    parsed_source = converter.parse(str(out / 'owner-associated-source.musicxml'))
    guards = {'source_roundtrip': validate(augmented, parsed_source, 0, 'key').to_dict()}
    require(
        guards['source_roundtrip']['ok']
        and full_lyric_signature(augmented) == full_lyric_signature(parsed_source),
        'Source lyric/semantic roundtrip failed',
    )
    new_parts, lyric_rows, baselines = render_lyric_parts(size, audit, source)
    # No retuning after this actual run: source baselines, font44 and all note coordinates fixed.
    boundaries = [m['physical_boundary_candidates'][1] for m in inv['measures']]
    graph = read(
        Path(
            '/private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output/predictions/baseline-exec/source/visual-graph.json'
        )
    )
    base = scaffold(
        size, staff, boundaries, {2400: graph['symbols']['sheet#1:4581']['geometry']['bbox']}
    )
    panels = [
        panel(
            source.crop(CROP),
            'Unchanged original Bb source comparison',
            associations_confirmed=True,
        )[0]
    ]
    reports = []
    for target, shift in [('A', -1), ('G', -3)]:
        score = copy.deepcopy(augmented)
        summary = transpose_score(score, shift, 'key')
        mem = validate(augmented, score, shift, 'key', summary).to_dict()
        score.write('musicxml', fp=str(out / f'{target}-transposed.musicxml'))
        parsed = converter.parse(str(out / f'{target}-transposed.musicxml'))
        disk = validate(augmented, parsed, shift, 'key', summary).to_dict()
        require(
            mem['ok']
            and disk['ok']
            and full_lyric_signature(parsed) == full_lyric_signature(augmented),
            'Full target guard or lyric roundtrip failed',
        )
        prior = converter.parse(str(INITIAL / f'{target}-transposed.musicxml'))
        require(
            [event_signature(m) for m in parsed.parts[0].getElementsByClass(stream.Measure)]
            == [event_signature(m) for m in prior.parts[0].getElementsByClass(stream.Measure)],
            'Frozen event signatures changed',
        )
        guards[target] = {'in_memory': mem, 'serialized': disk}
        musical = Image.open(PRIOR / f'{target}-confirmed-music-event-alpha.png').copy()
        header_ink = Image.open(INITIAL / f'{target}-header-alpha.png').copy()
        fixed = [base, musical, header_ink, Image.open(PRIOR / f'{target}-new-chord-alpha.png')]
        for p in (GT12 / 'confirmed-context').glob(target + '-*-alpha.png'):
            if '-chord-' in p.name or '-lyric-' in p.name:
                fixed.append(Image.open(p).crop((0, 0, *size)))
        contacts, collision = lyric_contacts(new_parts, musical)
        letter_pairs = []
        names = list(new_parts)
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                ba, bb = new_parts[a].getbbox(), new_parts[b].getbbox()
                box = (max(ba[0], bb[0]), max(ba[1], bb[1]), min(ba[2], bb[2]), min(ba[3], bb[3]))
                if box[2] <= box[0] or box[3] <= box[1]:
                    continue
                n = int(
                    np.count_nonzero(
                        (np.asarray(new_parts[a].crop(box)) > 0)
                        & (np.asarray(new_parts[b].crop(box)) > 0)
                    )
                )
                if n:
                    letter_pairs.append({'a': a, 'b': b, 'pixels': n})
        clipping = []
        for name, mask in new_parts.items():
            b = mask.getbbox()
            if b[0] < CROP[0] or b[1] < CROP[1] or b[2] > CROP[2] or b[3] > CROP[3]:
                clipping.append(name)
            mask.save(out / f'{target}-lyric-{name.replace(":","_")}.png')
        # The retained m1 lyric contract must remain exactly the same bitmap, now confirmed.
        old_masks = Path('/private/tmp/capomatic-v4-gt13a2/gt13a2-final-output')
        for e in audit['measures'][0]['events']:
            if e['pitch'] is None:
                continue
            for row in (0, 1):
                key = f'm1-{e["event_id"]}-row{row+1}'
                old = Image.open(
                    old_masks / f'{target}-lyric_{row}_{e["event_id"].replace(":","_")}.png'
                )
                require(
                    new_parts[key].tobytes() == old.tobytes(), 'Confirmed m1 text geometry moved'
                )
        alpha = Image.fromarray(
            np.maximum.reduce([np.asarray(p) for p in fixed + list(new_parts.values())])
        )
        native = Image.composite(
            Image.new('RGB', size, 'black'), Image.new('RGB', size, 'white'), alpha
        ).crop(CROP)
        m3 = (1374 - CROP[0], 0, 1783 - CROP[0], CROP[3] - CROP[1])
        require(
            native.crop(m3).tobytes()
            == Image.open(PRIOR / f'{target}-native-notation-viewport.png').crop(m3).tobytes(),
            'Original GT12 m3 changed',
        )
        count = int(np.count_nonzero(np.asarray(collision)))
        rendered, ann = panel(
            native,
            f'{target} major: owner-confirmed lyric associations; lyric/music contacts {count}; outgoing tie pending',
            target=target,
            music=Image.fromarray(np.maximum(np.asarray(musical), np.asarray(header_ink))).crop(
                CROP
            ),
            all_ink=alpha.crop(CROP),
            associations_confirmed=True,
            lyric_contacts=count,
        )
        rendered.save(out / f'predicted-{target.lower()}.png')
        panels.append(rendered)
        collision.save(out / f'{target}-lyric-music-collision-mask.png')
        alpha.save(out / f'{target}-notation-alpha.png')
        (out / f'{target}-owner-confirmed-event-alpha.png').write_bytes(
            (PRIOR / f'{target}-confirmed-music-event-alpha.png').read_bytes()
        )
        reports.append(
            {
                'target': target,
                'music_events': 26,
                'owner_verified_music_events': 26,
                'chords': 2,
                'new_association_status': 'OWNER_VERIFIED_LYRIC_ASSOCIATION',
                'baselines': baselines,
                'new_syllables': sum(r['new_syllable'] for r in lyric_rows),
                'cached_m3_syllables': 6,
                'continuation_markers': sum(not r['new_syllable'] for r in lyric_rows),
                'lyric_rows': lyric_rows,
                'lyric_music_contact_pairs': contacts,
                'lyric_music_unique_contact_pixels': count,
                'lyric_lyric_contacts': letter_pairs,
                'clipping': clipping,
                'annotations': ann,
                'visual_safety': (
                    'BLOCKED_COLLISION'
                    if count or letter_pairs or clipping
                    else 'PASS_SCOPED_MASK_CHECKS'
                ),
                'm3_unchanged': True,
                'music_geometry_unchanged': True,
                'no_post_result_retuning': True,
                'outgoing_tie_destination': 'UNVERIFIED; owner explicitly deferred',
                'overall': 'FULL_SYSTEM_INCOMPLETE',
            }
        )
    source.crop(CROP).save(out / 'original-bb.png')
    sheet = Image.new('RGB', (panels[0].width, sum(p.height for p in panels)), 'white')
    for i, p in enumerate(panels):
        sheet.paste(p, (0, i * p.height))
    sheet.save(out / 'comparison-contact-sheet.png')
    dump(out / 'aligned-lyric-validation.json', reports)
    dump(out / 'semantic-integrity.json', guards)
    dump(
        out / 'remaining-blockers.json',
        {
            'status': 'FULL_SYSTEM_INCOMPLETE',
            'lyric_associations': 'OWNER_VERIFIED; no duplicate transcription request',
            'blockers': [
                'Outgoing tie destination owner confirmation and cross-system rendering contract',
                'Any measured target lyric/music contact',
                'Independent optical and musician validation',
            ],
            'source_ink_edit_authorization': False,
            'independent_ground_truth': False,
        },
    )
    require(
        all(file_hashes(Path(p)) == h for p, h in histories.items()), 'Historical artifacts changed'
    )
    dump(
        out / 'prediction-freeze.json',
        {
            'producer_sha256': sha(Path(__file__)),
            'panel_producer_sha256': sha(ROOT / 'scripts/research/gt13a4_system_notation.py'),
            'files': file_hashes(out),
            'phase': 'BEFORE_TARGET_REFERENCE_OR_AGENT_VISUAL_REVIEW',
        },
    )


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    run(p.parse_args().out)
