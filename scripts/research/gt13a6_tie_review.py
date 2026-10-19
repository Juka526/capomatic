"""Source-only GT13A6 packet and raw OMR/semantic cross-check; no score rendering."""

import argparse
import copy
import zipfile
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

from music21 import converter, key, stream
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt11_complete_measure import events_of, read, require
from scripts.research.gt13a4_system_notation import tie_evidence, GT02
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.gt13a5_lyric_layout import OLD, SOURCE, verify_freeze
from scripts.research.paired_ground_truth_01 import dump, file_hashes, sha

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = SOURCE.parent
PREVIOUS = Path('/private/tmp/capomatic-v4-gt13a5/gt13a5-output')
BOXES = {
    'source-outgoing-tie.png': (140, 390, 2430, 720),
    'source-incoming-tie.png': (140, 750, 1050, 1080),
    'source-outgoing-closeup.png': (2300, 480, 2420, 600),
    'source-incoming-closeup.png': (245, 840, 390, 960),
}
QUESTION = (
    'Does the last Bb3 in printed measure 4 tie to the first Bb3 whole note in printed measure 5?'
)


def raw_evidence(xml):
    root = ET.fromstring(xml)
    slurs = {}
    for ident in ('4818', '4798'):
        found = [e for e in root.iter('slur') if e.get('id') == ident]
        require(len(found) == 1, 'Missing or ambiguous raw curve')
        slurs[ident] = found[0]
    require(
        slurs['4818'].get('right-extension') == '4798'
        and slurs['4798'].get('left-extension') == '4818',
        'Nonreciprocal raw extensions',
    )
    records = []
    for ident, head, side in [('4818', '1852', 'LEFT'), ('4798', '1923', 'RIGHT')]:
        element = slurs[ident]
        require(
            element.get('tie') == 'true' and element.get('above') == 'false',
            'Unsupported curve role',
        )
        rels = [
            r
            for r in root.iter('relation')
            if r.get('source') == ident and r.find('slur-head') is not None
        ]
        require(
            len(rels) == 1
            and rels[0].get('target') == head
            and rels[0].find('slur-head').get('side') == side,
            'Raw head relation differs',
        )
        heads = [e for e in root.iter('head') if e.get('id') == head]
        require(len(heads) == 1, 'Raw head missing')
        records.append(
            {
                'id': ident,
                'attributes': dict(element.attrib),
                'curve': dict(element.find('curve').attrib),
                'source_xml': ET.tostring(element, encoding='unicode'),
                'head_relation_xml': ET.tostring(rels[0], encoding='unicode'),
                'head_xml': ET.tostring(heads[0], encoding='unicode'),
            }
        )
    return records


def endpoint_pair(score, expected):
    measures = list(score.parts[0].getElementsByClass(stream.Measure))
    endpoints = []
    for index, onset, duration, role in [
        (3, Fraction(15, 4), Fraction(1, 4), 'start'),
        (4, Fraction(0), Fraction(4), 'stop'),
    ]:
        m = measures[index]
        notes = [n for n in events_of(m) if Fraction(n.getOffsetInHierarchy(m)) == onset]
        require(len(notes) == 1 and notes[0].isNote, 'Missing/ambiguous semantic endpoint')
        n = notes[0]
        require(
            n.pitch.nameWithOctave == expected
            and Fraction(n.quarterLength) == duration
            and n.tie is not None
            and n.tie.type == role,
            'Endpoint pitch/duration/tie mismatch',
        )
        endpoints.append(
            {
                'printed_measure_candidate': index + 1,
                'xml_measure_number': m.number,
                'onset': str(onset),
                'duration': str(duration),
                'pitch': n.pitch.nameWithOctave,
                'midi': n.pitch.midi,
                'tie': n.tie.type,
            }
        )
    return endpoints


def run(out):
    require(not out.exists(), 'New run directory required')
    verify_freeze(PREVIOUS)
    verify_freeze(OLD)
    history = {str(p): file_hashes(p) for p in (PREVIOUS, OLD)}
    require(sha(SOURCE) == read(OLD / 'input-freeze.json')['source_sha256'], 'Source hash mismatch')
    omr = SOURCE_DIR / 'recognized.omr'
    provenance_path = SOURCE_DIR.parents[2] / 'coordinator/pdf-provenance.json'
    provenance = read(provenance_path)
    require(provenance['source_page'] == 2, 'Wrong PDF source page')
    require(sha(Path(provenance['path'])) == provenance['sha256'], 'Original PDF hash mismatch')
    require(
        sha(SOURCE_DIR.parents[2] / 'source-only/source.png') == sha(SOURCE),
        'Frozen PDF raster and OMR input differ',
    )
    graph_path = SOURCE_DIR / 'visual-graph.json'
    graph = read(graph_path)
    with zipfile.ZipFile(omr) as z:
        raw = z.read('sheet#1/sheet#1.xml')
    records = raw_evidence(raw)
    for r in records:
        symbol = graph['symbols']['sheet#1:' + r['id']]
        require(dict(symbol['attributes']) == r['attributes'], 'Raw/graph attributes disagree')
        curve = r['curve']
        cp = [
            [float(curve[a]), float(curve[b])]
            for a, b in [('x1', 'y1'), ('ctrlx1', 'ctrly1'), ('ctrlx2', 'ctrly2'), ('x2', 'y2')]
        ]
        require(cp == symbol['geometry']['curve'], 'Raw/graph curve differs')
    score = converter.parse(str(OLD / 'owner-associated-source.musicxml'))
    evidence = tie_evidence(
        graph, read(GT02 / 'note-correspondence-diagnostic.json')['events']['Bb'], score
    )
    require(
        evidence['start_event']['omr_measure_index'] == 3
        and evidence['destination_candidate']['omr_measure_index'] == 4,
        'Wrong measure order',
    )
    source_endpoints = endpoint_pair(score, 'B-3')
    keys = list(score.recurse().getElementsByClass(key.KeySignature))
    require(keys and keys[0].sharps == -2, 'Source Bb key context missing')
    guards = {}
    target_endpoints = {}
    for target, shift, pitch in [('A', -1, 'A3'), ('G', -3, 'G3')]:
        target_score = copy.deepcopy(score)
        summary = transpose_score(target_score, shift, 'key')
        guards[target] = {
            'in_memory': validate(score, target_score, shift, 'key', summary).to_dict()
        }
        target_endpoints[target] = endpoint_pair(target_score, pitch)
        frozen = converter.parse(str(OLD / f'{target}-transposed.musicxml'))
        require(
            endpoint_pair(frozen, pitch) == target_endpoints[target],
            'Frozen target endpoints differ',
        )
        guards[target]['frozen_serialized'] = validate(score, frozen, shift, 'key').to_dict()
        require(
            all(v['ok'] for v in guards[target].values())
            and full_lyric_signature(score) == full_lyric_signature(frozen),
            'Unchanged full guard failed',
        )
    out.mkdir()
    source = Image.open(SOURCE)
    tiles = []
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 22)
    for name, box in BOXES.items():
        crop = source.crop(box)
        crop.save(out / name)
        require(crop.size == (box[2] - box[0], box[3] - box[1]), 'Crop geometry')
        tiles.append((name, crop))
    sheet = Image.new('RGB', (3280, 650), 'white')
    d = ImageDraw.Draw(sheet)
    d.text((20, 10), 'OWNER SOURCE REVIEW - ORIGINAL Bb PAGE 2 ONLY', font=font, fill='black')
    placements = {}
    for x, (name, crop) in zip((20, 2350), tiles[:2]):
        d.text((x, 55), name + ' / native 1:1 pixels', font=font, fill='black')
        sheet.paste(crop, (x, 85))
        placements[name] = [x, 85, x + crop.width, 85 + crop.height]
    y = 455
    for i, (name, crop) in enumerate(tiles[2:]):
        x = 20 + i * 700
        d.text((x, y), name + ' / native 1:1', font=font, fill='black')
        sheet.paste(crop, (x, y + 35))
        placements[name] = [x, y + 35, x + crop.width, y + 35 + crop.height]
    for name, crop in tiles:
        require(sheet.crop(placements[name]).tobytes() == crop.tobytes(), 'Review pixels differ')
    sheet.save(out / 'source-tie-review-sheet.png')
    crop_binding = {
        n: {'bbox': b, 'sha256': sha(out / n), 'size': Image.open(out / n).size}
        for n, b in BOXES.items()
    }
    dump(
        out / 'tie-owner-checklist.json',
        {
            'question': QUESTION,
            'allowed_answers': ['OWNER_CONFIRMED', 'OWNER_REJECTED', 'OWNER_UNCERTAIN'],
            'status': 'PENDING_OWNER_RESPONSE',
            'owner_response': None,
            'source_sha256': sha(SOURCE),
            'review_sheet_sha256': sha(out / 'source-tie-review-sheet.png'),
            'review_sheet_layout': 'SIDE_BY_SIDE_NATIVE_1_TO_1',
            'review_sheet_placements': placements,
            'crops': crop_binding,
            'classification': 'OWNER_REVIEW_NOT_INDEPENDENT_GROUND_TRUTH',
            'actual_prior_reply': '아직 미확인 — 목적지는 보류',
            'prior_reply_remains_unchanged': True,
        },
    )
    dump(
        out / 'tie-source-evidence.json',
        {
            'classification': 'OMR_SUPPORTED_CANDIDATE_PENDING_OWNER',
            'source_sha256': sha(SOURCE),
            'omr_sha256': sha(omr),
            'graph_sha256': sha(graph_path),
            'source_pdf_provenance': provenance,
            'source_pdf_provenance_sha256': sha(provenance_path),
            'source_pdf_hash_verified': True,
            'raw_member': 'sheet#1/sheet#1.xml',
            'raw_member_sha256': __import__('hashlib').sha256(raw).hexdigest(),
            'raw_records': records,
            'existing_graph_evidence': evidence,
            'source_endpoints': source_endpoints,
            'target_endpoints': target_endpoints,
            'source_key_fifths': -2,
            'coordinate_system': 'Original raster integer coordinates; no rescaling',
            'source_context': 'Treble/key context visible in full system crops; crop-specific key interpretation is not a new human label',
        },
    )
    dump(out / 'semantic-integrity.json', guards)
    protocol = read(ROOT / 'docs/V4_GT13A6_TIE_PROTOCOL.json')
    dump(out / 'tie-rendering-protocol.json', protocol)
    require(all(file_hashes(Path(p)) == h for p, h in history.items()), 'Historical change')
    dump(
        out / 'validation-summary.json',
        {
            'SOURCE_VERIFICATION': 'PENDING_OWNER_CONFIRMATION',
            'TIE_RENDERING_COMPLETENESS': 'BLOCKED_REAL_SCORE_CONTINUATION',
            'VISUAL_QUALITY': 'UNVERIFIED_REAL_SCORE_RENDERING',
            'system_status': 'FULL_SYSTEM_INCOMPLETE',
            'raw_reciprocal_extensions_verified': True,
            'full_V3_guards': 'PASS',
            'historical_files_unchanged': True,
            'actual_new_tie_rendered': False,
            'independent_labels': 0,
            'source_sha256': sha(SOURCE),
        },
    )
    dump(
        out / 'input-freeze.json',
        {
            'history_files': history,
            'source_sha256': sha(SOURCE),
            'omr_sha256': sha(omr),
            'producer_sha256': sha(Path(__file__)),
            'protocol_sha256': sha(ROOT / 'docs/V4_GT13A6_TIE_PROTOCOL.json'),
        },
    )
    dump(
        out / 'review-freeze.json',
        {'files': file_hashes(out), 'purpose': 'SOURCE_ONLY_OWNER_REVIEW_NO_REFERENCE_ACCESS'},
    )


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    run(p.parse_args().out)
