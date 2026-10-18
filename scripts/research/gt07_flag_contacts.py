"""Post-freeze source-support collision diagnosis; never regenerates notation."""

import json
from pathlib import Path
import numpy as np
from PIL import Image
from backend.omr_v4.ink import glyphs_from_omr, KINDS
from scripts.research.paired_ground_truth_01 import file_hashes, sha, dump
from scripts.research.ground_truth_02 import verify_inputs


def contact_pixels(mask, pixels):
    if any(not 0 <= x < mask.shape[1] or not 0 <= y < mask.shape[0] for x, y in pixels):
        raise ValueError('Source support coordinate mismatch')
    return {(x, y) for x, y in pixels if mask[y, x]}


def audit(gt01, inputs, prototype, out):
    if out.exists() or any(
        root.resolve() == out.resolve() or root.resolve() in out.resolve().parents
        for root in [gt01, inputs, prototype]
    ):
        raise ValueError('New contact report required')
    frozen = json.loads((prototype / 'prototype-freeze.json').read_text())
    files = file_hashes(prototype)
    files.pop('prototype-freeze.json')
    if files != frozen['files']:
        raise ValueError('Frozen prototype changed')
    if sha(inputs / 'selection.json') != frozen['selection_sha256']:
        raise ValueError('Frozen selection changed')
    verify_inputs(gt01)
    base = gt01 / 'predictions/baseline-exec'
    spec = json.loads((inputs / 'selection.json').read_text())
    if (
        sha(base / 'source/visual-graph.json') != spec['source_graph_sha256']
        or sha(base / 'source/recognized.omr') != spec['source_omr_sha256']
    ):
        raise ValueError('Frozen graph/OMR changed')
    graph = json.loads((base / 'source/visual-graph.json').read_text())
    glyphs = glyphs_from_omr(base / 'source/recognized.omr')
    move = next(
        n
        for n in json.loads((base / 'A/plan.json').read_text())['note_moves']
        if n['semantic_id'] == spec['event']['id']
    )
    owned = {i for _, ids in move['connected_symbols'] for i in ids}
    text = {'word', 'sentence', 'lyric-line', 'lyric-item', 'chord-name'}
    musical = KINDS | {
        'ledger',
        'rest',
        'clef',
        'key',
        'key-alter',
        'time-number',
        'time-whole',
        'articulation',
        'fermata',
        'slur',
    }
    result = {}
    for key in ['A', 'G']:
        mask = np.asarray(Image.open(prototype / f'{key}-music-only-alpha.png')) > 0
        if (mask.shape[1], mask.shape[0]) != Image.open(inputs / 'source.png').size:
            raise ValueError('Source/prototype coordinate mismatch')
        unions = {
            k: set()
            for k in [
                'UNRELATED_MUSICAL_SUPPORT',
                'STRUCTURAL_SUPPORT',
                'TEXT_SUPPORT_CANDIDATE',
                'OTHER_SUPPORT_UNKNOWN',
            ]
        }
        pairs = []
        for ident, s in graph['symbols'].items():
            if ident in owned:
                continue
            gid = dict(s['attributes']).get('glyph')
            pixels = glyphs.get(s['page'] + ':' + str(gid)) or frozenset()
            hit = contact_pixels(mask, pixels)
            if not hit:
                continue
            kind = (
                'TEXT_SUPPORT_CANDIDATE'
                if s['kind'] in text
                else (
                    'STRUCTURAL_SUPPORT'
                    if s['kind'] in {'barline', 'staff-barline'}
                    else (
                        'UNRELATED_MUSICAL_SUPPORT'
                        if s['kind'] in musical
                        else 'OTHER_SUPPORT_UNKNOWN'
                    )
                )
            )
            unions[kind].update(hit)
            pairs.append(
                {'symbol_id': ident, 'kind': s['kind'], 'category': kind, 'pixels': len(hit)}
            )
        result[key] = {
            'unique_pixels': {k: len(v) for k, v in unions.items()},
            'symbol_pairs': pairs,
        }
    report = {
        'targets': result,
        'prototype_freeze_sha256': sha(prototype / 'prototype-freeze.json'),
        'prediction_changed': False,
        'source_support_is_processed_evidence_not_confirmed_source_ownership': True,
        'full_future_score_collision_safety': 'UNKNOWN: other groups have not been transposed/rendered',
        'edit_authorization': 'NONE',
    }
    dump(out, report)
    return report
