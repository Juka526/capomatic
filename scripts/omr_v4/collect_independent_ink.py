"""Offline source-only collection. Human independence remains an external responsibility."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import heapq
import json
from pathlib import Path
import shutil

from PIL import Image

PROTOCOL = Path(__file__).resolve().parents[2] / 'docs/V4_INDEPENDENT_INK_PROTOCOL.json'
PROTOCOL_SHA = '2a04b99dd6b9fc2fae38d43efebfb56355e76376872f7a7ad581c2c7c3c597b6'
INSTRUCTIONS = '''Label only the anchor pixel, using the original source, focus and context.
Local target coordinates are zero-based. Crops are clipped, never padded or enhanced.
Optional zoom must use integer nearest-neighbor. Do not inspect guard, BINARY,
semantic evidence, screening motifs, audit mapping, or another primary's labels.
Use nonempty physical_content and boundary_contribution sets from schema.json.
MIXED is presentation shorthand for multiple valid content/contribution choices;
it is not a physical enum value. UNKNOWN may coexist with other possibilities.
Retain all rows including UNKNOWN, UNCERTAIN and ABSTAIN; give a rationale.
Ownership starts as contributors: [], unresolved: true; do not infer group IDs.
No per-case feedback or primary discussion before both files freeze.
Train only on frozen excluded pages. Sign your own complete submission.
Local files cannot enforce privacy or human independence: the custodian must
separate access, record exposure/conflicts, and deliver A/B independently.
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')


def receipt_path(path):
    return Path(str(path) + '.receipt.json')


def require_new_frozen(path):
    check_destination(path)
    check_destination(receipt_path(path))
    require(not Path(path).exists() and not receipt_path(path).exists(), 'frozen output/receipt already exists')


def seal(path):
    # Read-only files and separate receipts detect accidents, not a malicious custodian.
    write(receipt_path(path), {'file_sha256': sha(path)})
    Path(path).chmod(0o444)
    receipt_path(path).chmod(0o444)


def check_seal(path):
    no_symlinks(path)
    no_symlinks(receipt_path(path))
    require(sha(path) == load(receipt_path(path))['file_sha256'], 'frozen file/receipt mismatch')


def load(path):
    return json.loads(Path(path).read_text())


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def exact_keys(value, keys, name):
    require(isinstance(value, dict) and set(value) == set(keys), f'unexpected/missing {name} fields')


def no_symlinks(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'symlink paths are not permitted')


def evidence_root():
    p = protocol()
    require(sha(p['binding_manifest']) == p['binding_manifest_sha256'], 'binding manifest mismatch')
    return Path(load(p['binding_manifest'])['input_root']).resolve()


def check_destination(path):
    no_symlinks(path)
    resolved = Path(path).resolve()
    root = evidence_root()
    require(resolved != root and root not in resolved.parents, 'output inside immutable source evidence')


def separate_paths(left, right):
    a, b = Path(left).resolve(), Path(right).resolve()
    require(a != b and a not in b.parents and b not in a.parents, 'private output must be outside packet; paths must not alias')


def private_destination(path, packet_path):
    check_destination(path)
    separate_paths(path, packet_path)


def stamp(value):
    require(isinstance(value, str), 'timestamp required')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(dt.tzinfo is not None and dt <= datetime.now(timezone.utc), 'invalid/future timestamp')
    return dt


def signature(meta):
    exact_keys(meta, ('person_id', 'signature', 'signed_at'), 'signature')
    for key in ('person_id', 'signature', 'signed_at'):
        require(isinstance(meta.get(key), str) and meta[key].strip(), f'{key} required')
    stamp(meta['signed_at'])


def protocol():
    require(sha(PROTOCOL) == PROTOCOL_SHA, 'frozen protocol mutation')
    return load(PROTOCOL)


def verify_inputs():
    p = protocol()
    manifest = Path(p['binding_manifest'])
    require(sha(manifest) == p['binding_manifest_sha256'], 'binding manifest mismatch')
    m = load(manifest)
    require(len(m['files']) == p['binding_count'], 'binding count mismatch')
    root = Path(m['input_root'])
    for name, expected in m['files'].items():
        require(sha(root / name) == expected, f'input mismatch: {name}')
    require(sha(root / 'source.png') == p['source_sha256'], 'source mismatch')
    with Image.open(root / 'source.png') as im:
        require(list(im.size) == p['source_dimensions'], 'source dimensions mismatch')
    return p, root / 'source.png'


def tiles(w, h):
    return [{'tile_id': f't{r:04d}_{c:04d}', 'bounds': [x, y, min(x+64,w), min(y+64,h)]}
            for r, y in enumerate(range(0, h, 64))
            for c, x in enumerate(range(0, w, 64))]


def export_screening_tiles(source, out):
    """Entire page partition for screening; no anchor ranking or selection."""
    check_destination(out)
    out = Path(out)
    require(not out.exists(), 'new screening tile directory required')
    out.mkdir(parents=True)
    with Image.open(source) as im:
        records = tiles(*im.size)
        for tile in records:
            tile['file'] = tile['tile_id'] + '.png'
            target = out / tile['file']
            im.crop(tuple(tile['bounds'])).save(target)
            tile['sha256'] = sha(target)
            target.chmod(0o444)
    return records


def schema(p):
    return {k: p['annotation'][k] for k in
            ('physical_content', 'boundary_contribution', 'certainty')} | {
        'MIXED': 'Choose multiple valid physical_content/boundary_contribution values; no MIXED enum.',
        'ownership': {'contributors': [], 'unresolved': True},
        'rationale': 'required nonblank string', 'all_case_ids_required': True}


def prepare(out):
    check_destination(out)
    p, source = verify_inputs()
    out = Path(out)
    require(not out.exists(), 'new output directory required')
    out.mkdir(parents=True)
    shutil.copyfile(source, out / 'source.png')
    ts = export_screening_tiles(source, out / 'screening-tiles')
    write(out / 'tiles.json', {'source_sha256': p['source_sha256'],
                              'tile_directory': 'screening-tiles', 'tiles': ts})
    write(out / 'screening-schema.json', {
        'tile_status': ['examined', 'unavailable', 'unclassifiable'],
        'motifs': p['diagnostic']['motif_order'],
        'nomination': {'motif': 'one motif from motifs', 'x': 'global integer x', 'y': 'global integer y'},
        'rule': 'At most one nomination per motif per tile; complete every tile in order.',
        'non_examined': 'Required reason and empty nominations; no silent omissions.',
        'absence': 'An examined tile with no nominations must explicitly contain nominations: [].'})
    (out / 'screening-instructions.txt').write_text(
        'Independent human screener: inspect only source.png, in tiles.json row-major order.\n'
        'Do not inspect guard, BINARY, semantic evidence, or primary labels.\n'
        'Tile bounds are half-open original-source coordinates, clipped at edges.\n'
        'All native tile PNGs are in screening-tiles/; hashes and bounds are in tiles.json.\n'
        'These exhaustive screening tiles are not selected evaluation anchors.\n'
        'Complete every screening-template.json row using screening-schema.json.\n'
        'Motifs are apparent visual hypotheses, never final physical labels.\n'
        'Unavailable/unclassifiable tiles require reasons and no nominations.\n'
        'Explicit empty nominations on examined tiles are retained.\n'
        'Freeze the entire independent screening list before any diagnostic ranking.\n')
    write(out / 'screening-template.json', {
        'source_sha256': p['source_sha256'], 'protocol_sha256': PROTOCOL_SHA,
        'source_only': None, 'screener_id': '',
        'tiles': [{'tile_id': t['tile_id'], 'status': None, 'reason': '', 'nominations': []}
                  for t in ts]})
    write(out / 'roster-template.json', {'source_sha256': p['source_sha256'],
        'protocol_sha256': PROTOCOL_SHA,
        'people': [{'role': role, 'person_id': '', 'human': None, 'expertise': '',
                    'conflicts': '', 'prior_exposure': '', 'excluded_roles': [],
                    'eligible_attestation': None}
                   for role in ('A', 'B', 'adjudicator', 'screener', 'custodian')]})
    (out / 'instructions.txt').write_text(INSTRUCTIONS)
    write(out / 'training-template.json', {'source_sha256': p['source_sha256'],
        'protocol_sha256': PROTOCOL_SHA, 'excluded_pages': [],
        'excluded_from_all_evaluation_and_holdout': None,
        'instructions_sha256': sha(out / 'instructions.txt')})
    write(out / 'schema.json', schema(p))
    write(out / 'signer-template.json', {'person_id': '', 'signature': '', 'signed_at': ''})
    result = {'status': 'NOT_READY', 'official_selected_anchors': 0,
              'planned_prevalence_maximum': 96, 'planned_diagnostic_maximum': 32,
              'protocol_sha256': PROTOCOL_SHA, 'source_sha256': p['source_sha256'],
              'missing': ['frozen_eligible_human_roster', 'frozen_training_exclusions',
                          'complete_frozen_independent_source_only_screening'],
              'packet_created': False, 'source_only_screening_tiles': len(ts),
              'source_only_screening_tile_pngs': len(ts), 'screening_tiles_are_official_anchors': False,
              'independence': 'External human attestation/access controls required; not proven by this tool.'}
    write(out / 'readiness.json', result)
    verify_inputs()
    for f in out.rglob('*'):
        if f.is_file():
            f.chmod(0o444)
    return result


def freeze(kind, input_path, signer_path, output):
    """Freeze bytes semantically; independent receipt must be held by custodian."""
    require_new_frozen(output)
    p = protocol()
    content = load(input_path)
    meta = load(signer_path)
    signature(meta)
    require(content['protocol_sha256'] == PROTOCOL_SHA and
            content['source_sha256'] == p['source_sha256'], 'freeze binding mismatch')
    # Prerequisites are checked before archiving, not merely when sampling later.
    if kind == 'roster':
        validate_roster(content, p)
        require(meta['person_id'] == person(content, 'custodian')['person_id'], 'custodian must freeze roster')
    elif kind == 'training':
        validate_training(content, p)
    elif kind == 'screening':
        validate_screening(content, p)
        require(meta['person_id'] == content['screener_id'], 'screener must sign screening')
    else:
        raise ValueError('unknown prerequisite kind')
    envelope = {'kind': kind, 'content': content, 'signature': meta,
                'frozen_at': datetime.now(timezone.utc).isoformat(),
                'protocol_sha256': PROTOCOL_SHA, 'content_sha256': digest(content)}
    write(output, envelope)
    seal(output)
    return {'file_sha256': sha(output), 'content_sha256': envelope['content_sha256']}


def frozen(path, kind):
    check_seal(path)
    e = load(path)
    require(e['kind'] == kind and e['protocol_sha256'] == PROTOCOL_SHA, 'freeze kind/protocol mismatch')
    require(e['content_sha256'] == digest(e['content']), 'frozen content tampered')
    signature(e['signature'])
    require(stamp(e['signature']['signed_at']) <= stamp(e['frozen_at']), 'signature after freeze')
    return e


def person(roster, role):
    matches = [x for x in roster['people'] if x['role'] == role]
    require(len(matches) == 1, f'exactly one {role} required')
    return matches[0]


def validate_roster(roster, p):
    required = ('A', 'B', 'adjudicator', 'screener', 'custodian')
    require(len(roster['people']) == len(required), 'exact role roster required')
    people = [person(roster, role) for role in required]
    require(len({x['person_id'] for x in people}) == len(people), 'roles must be separate people')
    for x in people:
        require(isinstance(x['person_id'], str) and x['person_id'].strip(), 'person identity required')
        require(x['human'] is True and x['eligible_attestation'] is True, 'eligible human attestation required')
        for k in ('expertise', 'conflicts', 'prior_exposure'):
            require(isinstance(x[k], str) and x[k].strip(), f'{k} disclosure required')
        require(isinstance(x['excluded_roles'], list), 'excluded role disclosure required')
    for x in people[:3]:
        require(not set(x['excluded_roles']) & set(p['independence']['excluded_roles']), 'ineligible primary/adjudicator')


def validate_training(training, p):
    require(training['excluded_from_all_evaluation_and_holdout'] is True, 'training exclusions not attested')
    require(training['instructions_sha256'] == hashlib.sha256(INSTRUCTIONS.encode()).hexdigest(), 'instructions mismatch')
    require(bool(training['excluded_pages']), 'separate training pages required')
    for page in training['excluded_pages']:
        h = page['source_sha256']
        require(isinstance(h, str) and len(h) == 64 and all(c in '0123456789abcdef' for c in h), 'training hash invalid')
        require(h != p['source_sha256'], 'evaluation source used for training')
        require(isinstance(page['reason'], str) and page['reason'].strip(), 'training exclusion reason required')
        require(page['consented'] is True, 'training consent attestation required')


def validate_screening(screening, p):
    require(screening['source_only'] is True and bool(screening['screener_id']), 'source-only screening attestation required')
    ts = tiles(*p['source_dimensions'])
    rows = screening['tiles']
    require([r['tile_id'] for r in rows] == [t['tile_id'] for t in ts], 'complete row-major screening required')
    motifs = p['diagnostic']['motif_order']
    for row, tile in zip(rows, ts):
        require(row['status'] in ('examined', 'unavailable', 'unclassifiable'), 'incomplete screening tile')
        if row['status'] != 'examined':
            require(bool(row['reason'].strip()) and not row['nominations'], 'unavailable tile needs reason, no nominations')
        seen = set()
        for n in row['nominations']:
            require(n['motif'] in motifs and n['motif'] not in seen, 'invalid/duplicate tile motif')
            seen.add(n['motif'])
            x, y = n['x'], n['y']
            require(type(x) is int and type(y) is int, 'integer anchor required')
            a,b,c,d = tile['bounds']
            require(a <= x < c and b <= y < d, 'nomination outside tile')


def prerequisites(roster_path, training_path, screening_path, p):
    r, t, s = (frozen(path, kind) for path, kind in
               ((roster_path, 'roster'), (training_path, 'training'), (screening_path, 'screening')))
    for e in (r,t,s):
        require(e['content']['source_sha256'] == p['source_sha256'] and
                e['content']['protocol_sha256'] == PROTOCOL_SHA, 'prerequisite binding mismatch')
    validate_roster(r['content'], p)
    validate_training(t['content'], p)
    validate_screening(s['content'], p)
    require(r['signature']['person_id'] == person(r['content'], 'custodian')['person_id'], 'roster signer mismatch')
    require(t['signature']['person_id'] == person(r['content'], 'custodian')['person_id'], 'training signer mismatch')
    require(s['signature']['person_id'] == person(r['content'], 'screener')['person_id'] ==
            s['content']['screener_id'], 'screening signer mismatch')
    require(stamp(r['frozen_at']) <= stamp(s['frozen_at']) and
            stamp(t['frozen_at']) <= stamp(s['frozen_at']), 'roster/training must freeze before screening')
    return r['content'], s['content']


def rank(p, *parts):
    return hashlib.sha256('|'.join(map(str, (p['seed'], p['source_sha256'], *parts))).encode('utf-8')).digest()


def select(p, screening):
    """Dimensions, identity and frozen source-only nominations are the only inputs."""
    w,h = p['source_dimensions']
    anchors, cells, selected = [], [], set()
    for r in range(4):
        for c in range(4):
            points = ((rank(p, 'prevalence', c,r,x,y), y,x)
                      for y in range(r*h//4,(r+1)*h//4)
                      for x in range(c*w//4,(c+1)*w//4))
            chosen = heapq.nsmallest(6, points)
            population = ((c+1)*w//4-c*w//4)*((r+1)*h//4-r*h//4)
            cells.append({'cell': [c,r], 'population': population, 'selected': len(chosen)})
            for _,y,x in chosen:
                selected.add((x,y))
                anchors.append({'x':x,'y':y,'arm':'prevalence','cell':[c,r]})
    counts = []
    for motif in p['diagnostic']['motif_order']:
        nominations = [n for t in screening['tiles'] for n in t['nominations'] if n['motif'] == motif]
        ordered = sorted((rank(p,'diagnostic',motif,n['x'],n['y']),n['y'],n['x']) for n in nominations)
        eligible = [(x,y) for _,y,x in ordered if (x,y) not in selected]
        duplicate_exclusions = len(ordered)-len(eligible)
        for x,y in eligible[:8]:
            selected.add((x,y))
            anchors.append({'x':x,'y':y,'arm':'diagnostic','motif':motif})
        counts.append({'motif':motif, 'all_nominations':len(nominations),
                       'duplicate_exclusions':duplicate_exclusions, 'eligible_after_exclusions':len(eligible),
                       'selected_unique_anchors':min(8,len(eligible))})
    return anchors, {'cells':cells,'motifs':counts,
                     'examined_tiles':sum(t['status']=='examined' for t in screening['tiles']),
                     'unavailable_tiles':sum(t['status']=='unavailable' for t in screening['tiles']),
                     'unclassifiable_tiles':sum(t['status']=='unclassifiable' for t in screening['tiles'])}


def bounds(x,y,s,w,h):
    return [max(0,x-s//2), max(0,y-s//2), min(w,x+s//2+1), min(h,y+s//2+1)]


def overlap(rectangles):
    pairs = sum(max(a[0],b[0]) < min(a[2],b[2]) and max(a[1],b[1]) < min(a[3],b[3])
                for i,a in enumerate(rectangles) for b in rectangles[i+1:])
    xs = sorted({v for r in rectangles for v in (r[0],r[2])})
    area = 0
    for x0,x1 in zip(xs,xs[1:]):
        intervals = sorted((r[1],r[3]) for r in rectangles if r[0] <= x0 and r[2] >= x1)
        top, length = -1, 0
        for y0,y1 in intervals:
            length += max(0,y1-max(y0,top))
            top = max(top,y1)
        area += (x1-x0)*length
    return {'unique_crop_rectangles':len({tuple(r) for r in rectangles}),
            'overlapping_pair_count':pairs, 'union_area':area}


def packet(out, audit, roster_path, training_path, screening_path):
    check_destination(out)
    check_destination(audit)
    p, source = verify_inputs()
    roster, screening = prerequisites(roster_path, training_path, screening_path, p)
    out, audit = Path(out), Path(audit)
    require(not out.exists(), 'new packet and audit paths required')
    require_new_frozen(audit)
    separate_paths(out, audit)
    separate_paths(out, receipt_path(audit))
    anchors, denominators = select(p, screening)
    for a in anchors:
        a['case_id'] = 'p'+rank(p,'presentation',a['x'],a['y']).hex()
    require(len({a['case_id'] for a in anchors}) == len(anchors), 'presentation digest collision')
    anchors.sort(key=lambda a:(a['case_id'],a['y'],a['x']))
    out.mkdir(parents=True)
    shutil.copyfile(source, out/'source.png')
    (out/'instructions.txt').write_text(INSTRUCTIONS)
    write(out/'schema.json', schema(p))
    cases, rectangles = [], {65:[],513:[]}
    with Image.open(source) as im:
        for a in anchors:
            case = {'case_id':a['case_id']}
            for size, name in ((65,'focus'),(513,'context')):
                rect = bounds(a['x'],a['y'],size,*im.size)
                rectangles[size].append(rect)
                filename = f"{a['case_id']}-{name}.png"
                im.crop(tuple(rect)).save(out/filename)
                case[name] = {'file':filename, 'sha256':sha(out/filename),
                              'target':[a['x']-rect[0],a['y']-rect[1]]}
            cases.append(case)
    manifest = {'protocol_sha256':PROTOCOL_SHA,'source_sha256':p['source_sha256'],
                'cases':cases, 'files':{f.name:sha(f) for f in out.iterdir() if f.is_file()}}
    write(out/'packet.json', manifest)
    template = {'protocol_sha256':PROTOCOL_SHA,'source_sha256':p['source_sha256'],
                'packet_sha256':sha(out/'packet.json'), 'role':'',
                'signature':{'person_id':'','signature':'','signed_at':''},
                'source_only_independent':None,
                'labels':[{'case_id':c['case_id'], 'physical_content':[],
                           'boundary_contribution':[], 'certainty':'','rationale':'',
                           'ownership':{'contributors':[],'unresolved':True}} for c in cases]}
    write(out/'submission-template.json',template)
    audit_content = {'protocol_sha256':PROTOCOL_SHA,'source_sha256':p['source_sha256'],
        'packet_sha256':sha(out/'packet.json'), 'template_sha256':sha(out/'submission-template.json'),
        'packet_frozen_at':datetime.now(timezone.utc).isoformat(),
        'roster':roster,'anchors':anchors,'denominators':denominators,
        'overlap':{'unique_anchors':len(anchors), **{str(s):overlap(rs) for s,rs in rectangles.items()}},
        'prerequisites':{str(Path(f).resolve()):sha(f) for f in (roster_path,training_path,screening_path)}}
    write(audit, {'content':audit_content,'content_sha256':digest(audit_content)})
    seal(audit)
    for f in out.iterdir():
        f.chmod(0o444)
    verify_inputs()
    return {'status':'READY_FOR_INDEPENDENT_COLLECTION', 'official_selected_anchors':len(anchors),
            'human_independence':'Externally attested, not automatically proven',
            'audit_sha256':sha(audit),'packet_sha256':sha(out/'packet.json')}


def verify_packet(out, audit):
    p = protocol()
    out = Path(out)
    no_symlinks(out)
    separate_paths(out, audit)
    separate_paths(out, receipt_path(audit))
    check_seal(audit)
    e = load(audit)
    require(e['content_sha256'] == digest(e['content']), 'audit content tampered')
    a = e['content']
    require(a['protocol_sha256'] == PROTOCOL_SHA and a['source_sha256'] == p['source_sha256'], 'audit binding mismatch')
    require(sha(out/'packet.json') == a['packet_sha256'], 'packet manifest tampered')
    no_symlinks(out/'packet.json')
    m = load(out/'packet.json')
    exact_keys(m, ('protocol_sha256','source_sha256','cases','files'), 'packet manifest')
    expected_files = {'source.png', 'instructions.txt', 'schema.json'}
    for case in m['cases']:
        exact_keys(case, ('case_id','focus','context'), 'packet case')
        case_id = case['case_id']
        require(isinstance(case_id,str) and len(case_id)==65 and case_id[0]=='p' and
                all(c in '0123456789abcdef' for c in case_id[1:]), 'invalid opaque case ID')
        for name in ('focus','context'):
            exact_keys(case[name], ('file','sha256','target'), 'crop descriptor')
            filename = f'{case_id}-{name}.png'
            require(case[name]['file']==filename, 'crop filename must match opaque case ID')
            require(m['files'].get(filename)==case[name]['sha256'], 'crop hash binding mismatch')
            expected_files.add(filename)
    require(set(m['files'])==expected_files, 'unexpected/missing manifest files')
    require({f.name for f in out.iterdir()}==expected_files|{'packet.json','submission-template.json'},
            'unexpected/missing packet files')
    for f in out.iterdir():
        require(not f.is_symlink() and f.is_file(), 'packet entries must be regular files, no symlinks')
    require(m['protocol_sha256'] == PROTOCOL_SHA and m['source_sha256'] == p['source_sha256'], 'packet binding mismatch')
    for name,h in m['files'].items():
        require(Path(name).name == name and sha(out/name) == h, f'packet file tampered: {name}')
    require(sha(out/'source.png') == p['source_sha256'], 'packet source mismatch')
    require(sha(out/'submission-template.json') == a['template_sha256'], 'packet template tampered')
    for path,h in a['prerequisites'].items():
        require(sha(path) == h, 'frozen prerequisite tampered')
    require([c['case_id'] for c in m['cases']] == [x['case_id'] for x in a['anchors']], 'case mapping mismatch')
    return p,m,a


def validate_labels(content, p, manifest, audit, role):
    allowed = {'protocol_sha256','source_sha256','packet_sha256','role','signature','source_only_independent','labels'}
    if role == 'adjudicator':
        allowed.add('primary_sha256')
    exact_keys(content, allowed, 'submission')
    require(content['protocol_sha256'] == PROTOCOL_SHA and content['source_sha256'] == p['source_sha256'] and
            content['packet_sha256'] == audit['packet_sha256'], 'submission binding mismatch')
    require(content['role'] == role and content['source_only_independent'] is True, 'independent role attestation required')
    signature(content['signature'])
    require(stamp(content['signature']['signed_at']) >= stamp(audit['packet_frozen_at']), 'submission signed before packet freeze')
    require(content['signature']['person_id'] == person(audit['roster'],role)['person_id'], 'signer not frozen role')
    labels = content['labels']
    require([x['case_id'] for x in labels] == [x['case_id'] for x in manifest['cases']], 'all case IDs in packet order required')
    for row in labels:
        allowed_row = {'case_id','physical_content','boundary_contribution','certainty','rationale','ownership'}
        if role == 'adjudicator':
            allowed_row.add('alternatives_and_disposition')
        exact_keys(row, allowed_row, 'label row')
        for k in ('physical_content','boundary_contribution'):
            values = row[k]
            require(isinstance(values,list) and values and len(set(values)) == len(values) and
                    set(values) <= set(p['annotation'][k]), f'invalid {k}; MIXED requires multiple valid choices')
        require(row['certainty'] in p['annotation']['certainty'], 'invalid certainty')
        require(isinstance(row['rationale'],str) and row['rationale'].strip(), 'rationale required')
        require(row['ownership'] == {'contributors':[],'unresolved':True}, 'source-only ownership must remain unknown')


def submit(out, audit_path, role, input_path, archive):
    private_destination(archive, out)
    require(role in ('A','B'), 'primary role must be A or B')
    p,m,a = verify_packet(out,audit_path)
    content = load(input_path)
    validate_labels(content,p,m,a,role)
    archive = Path(archive)
    archive.mkdir(parents=True,exist_ok=True)
    target = archive/f'{role}.json'
    check_destination(target)
    check_destination(receipt_path(target))
    require(not target.exists() and not receipt_path(target).exists(), 'primary already frozen; never overwrite')
    e = {'kind':role,'content':content,'content_sha256':digest(content),
         'protocol_sha256':PROTOCOL_SHA,'signature':content['signature'],
         'frozen_at':datetime.now(timezone.utc).isoformat(), 'audit_sha256':sha(audit_path)}
    write(target,e)
    seal(target)
    # Custodian must retain this receipt separately. No A labels are returned to B.
    return {'role':role,'file_sha256':sha(target),'content_sha256':e['content_sha256']}


def both(out,audit_path,archive):
    private_destination(archive, out)
    p,m,a = verify_packet(out,audit_path)
    archive = Path(archive)
    frozen_files = [archive/f'{role}.json' for role in ('A','B')]
    require(all(f.exists() for f in frozen_files), 'both independent primary freezes required')
    entries = [frozen(f,role) for f,role in zip(frozen_files,('A','B'))]
    for e,role in zip(entries,('A','B')):
        require(e['audit_sha256'] == sha(audit_path), 'audit changed since primary freeze')
        require(e['signature'] == e['content']['signature'], 'signature metadata mismatch')
        validate_labels(e['content'],p,m,a,role)
    return p,m,a,entries


def disagree(out,audit_path,archive,report_dir):
    private_destination(report_dir, out)
    p,m,a,entries = both(out,audit_path,archive)
    dest = Path(report_dir)
    require(not dest.exists(), 'new source-only disagreement output required')
    dest.mkdir(parents=True)
    rows = []
    summaries = {}
    for arm in ('prevalence','diagnostic'):
        pairs = [(anchor,x,y) for anchor,x,y in zip(a['anchors'],entries[0]['content']['labels'],entries[1]['content']['labels'])
                 if anchor['arm']==arm]
        axes = {}
        for axis in ('physical_content','boundary_contribution'):
            axes[axis] = {'exact_set_agreement':sum(set(x[axis])==set(y[axis]) for _,x,y in pairs),
                'per_label_2x2':{label:{f'{i}{j}':sum((label in x[axis])==bool(i) and (label in y[axis])==bool(j)
                    for _,x,y in pairs) for i,j in ((0,0),(0,1),(1,0),(1,1))}
                    for label in p['annotation'][axis]}}
        summaries[arm] = {'paired':len(pairs),'unpaired':0,'total':len(pairs), 'axes':axes,
            'disagreement_count':sum(any(set(x[k])!=set(y[k]) for k in ('physical_content','boundary_contribution')) or x['certainty']!=y['certainty'] for _,x,y in pairs),
            'unknown_abstain':{role:{'unknown':sum('UNKNOWN' in z[i+1]['physical_content'] or 'UNKNOWN' in z[i+1]['boundary_contribution'] for z in pairs),
                                     'abstain':sum(z[i+1]['certainty']=='ABSTAIN' for z in pairs)} for i,role in enumerate(('A','B'))}}
    for x,y in zip(entries[0]['content']['labels'],entries[1]['content']['labels']):
        rows.append({'case_id':x['case_id'],'A':x,'B':y})
    hashes = {role:sha(Path(archive)/f'{role}.json') for role in ('A','B')}
    write(dest/'source-only-comparison.json',{'primary_sha256':hashes,'rows':rows})
    # Arm/mapping and source-independent metrics stay with the custodian.
    write(dest/'custodian-statistics.json',{'arms':summaries,'overlap':a['overlap'],
        'denominators':a['denominators'],'primary_sha256':hashes})
    template = load(Path(out)/'submission-template.json')
    template.update(role='adjudicator',primary_sha256=hashes)
    for row in template['labels']:
        row['alternatives_and_disposition'] = ''
    write(dest/'adjudication-template.json',template)
    return {'both_primaries_frozen':True,'case_count':len(rows),'disagreement_report_created':True,
            'access':'Only source-only comparison/template to adjudicator; statistics stay custodian-only.'}


def adjudicate(out,audit_path,archive,input_path,output):
    private_destination(output, out)
    private_destination(receipt_path(output), out)
    require_new_frozen(output)
    p,m,a,entries = both(out,audit_path,archive)
    content = load(input_path)
    validate_labels(content,p,m,a,'adjudicator')
    expected = {role:sha(Path(archive)/f'{role}.json') for role in ('A','B')}
    require(content['primary_sha256']==expected,'primary freeze digest mismatch')
    for row in content['labels']:
        require(isinstance(row.get('alternatives_and_disposition'),str) and
                row['alternatives_and_disposition'].strip(), 'preserve alternatives and explain disposition')
    require(stamp(content['signature']['signed_at']) >= max(stamp(e['frozen_at']) for e in entries), 'adjudication signed before primary freezes')
    e = {'kind':'adjudication','protocol_sha256':PROTOCOL_SHA,'content':content,
         'content_sha256':digest(content),'signature':content['signature'],
         'frozen_at':datetime.now(timezone.utc).isoformat(),'audit_sha256':sha(audit_path)}
    write(output,e)
    seal(output)
    return {'adjudication_sha256':sha(output),'status':'PHYSICAL_LABELS_FROZEN_NO_EDIT_AUTHORIZATION'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    q = sub.add_parser('prepare'); q.add_argument('--out',type=Path,required=True)
    q = sub.add_parser('freeze-input')
    for name in ('kind','input','signer','output'): q.add_argument('--'+name,required=True)
    q = sub.add_parser('packet')
    for name in ('out','audit','roster','training','screening'): q.add_argument('--'+name,required=True)
    for command in ('submit','disagreements','adjudicate'):
        q = sub.add_parser(command)
        for name in ('out','audit','archive'): q.add_argument('--'+name,required=True)
        if command in ('submit','adjudicate'): q.add_argument('--input',required=True)
        if command == 'submit': q.add_argument('--role',choices=['A','B'],required=True)
        elif command == 'disagreements': q.add_argument('--report-dir',required=True)
        else: q.add_argument('--output',required=True)
    args = vars(parser.parse_args()); cmd = args.pop('command')
    if cmd == 'prepare': result = prepare(**args)
    elif cmd == 'freeze-input': result = freeze(args['kind'],args['input'],args['signer'],args['output'])
    elif cmd == 'packet': result = packet(args['out'],args['audit'],args['roster'],args['training'],args['screening'])
    elif cmd == 'submit': result = submit(args['out'],args['audit'],args['role'],args['input'],args['archive'])
    elif cmd == 'disagreements': result = disagree(args['out'],args['audit'],args['archive'],args['report_dir'])
    else: result = adjudicate(args['out'],args['audit'],args['archive'],args['input'],args['output'])
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__ == '__main__':
    main()
