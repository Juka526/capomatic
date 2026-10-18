"""Synthetic fixtures only: these labels are not real annotation evidence."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from PIL import Image
import pytest

from scripts.omr_v4 import collect_independent_ink as ink


def now():
    return datetime.now(timezone.utc).isoformat()


def put(path, data):
    path.write_text(json.dumps(data))
    return path


def signer(tmp, who):
    return put(tmp/f'{who}-signature.json', {'person_id':who, 'signature':'SYNTHETIC TEST ONLY', 'signed_at':now()})


@pytest.fixture
def study(tmp_path, monkeypatch):
    # Small colorful image checks byte/pixel preservation and clipped corners.
    source = tmp_path/'synthetic-source.png'
    im = Image.new('RGB',(12,13))
    im.putdata([(x*17,y*19,(x+y)*9) for y in range(13) for x in range(12)])
    im.save(source)
    p = deepcopy(ink.protocol())
    p['source_dimensions'] = [12,13]
    p['source_sha256'] = ink.sha(source)
    monkeypatch.setattr(ink,'protocol',lambda:p)
    monkeypatch.setattr(ink,'verify_inputs',lambda:(p,source))
    binding = {'protocol_sha256':ink.PROTOCOL_SHA,'source_sha256':p['source_sha256']}
    roster = dict(binding, people=[{'role':r,'person_id':r,'human':True,
        'expertise':'synthetic test fixture','conflicts':'synthetic none',
        'prior_exposure':'synthetic none','excluded_roles':[],'eligible_attestation':True}
        for r in ('A','B','adjudicator','screener','custodian')])
    training = dict(binding,excluded_from_all_evaluation_and_holdout=True,
        instructions_sha256=hashlib.sha256(ink.INSTRUCTIONS.encode()).hexdigest(),
        excluded_pages=[{'source_sha256':'a'*64,'reason':'synthetic fixture training exclusion','consented':True}])
    screening = dict(binding,source_only=True,screener_id='screener',
                     tiles=[{'tile_id':t['tile_id'],'status':'examined','reason':'',
                             'nominations':[]} for t in ink.tiles(*im.size)])
    paths = []
    for kind, content in (('roster',roster),('training',training),('screening',screening)):
        raw = put(tmp_path/f'{kind}-raw.json',content)
        path = tmp_path/f'{kind}-frozen.json'
        ink.freeze(kind,raw,signer(tmp_path,'screener' if kind=='screening' else 'custodian'),path)
        paths.append(path)
    return tmp_path,p,source,paths


def build(study):
    tmp,p,source,paths = study
    out,audit = tmp/'packet',tmp/'private-audit.json'
    ink.packet(out,audit,*paths)
    return out,audit


def submission(study,out,role):
    tmp,p,source,paths = study
    result = ink.load(out/'submission-template.json')
    result.update(role=role,source_only_independent=True,
                  signature={'person_id':role,'signature':'SYNTHETIC TEST ONLY','signed_at':now()})
    for i,row in enumerate(result['labels']):
        row.update(physical_content=['UNKNOWN'] if i%2 else ['MUSICAL_NOTATION','WATERMARK_OR_GRAPHIC','UNKNOWN'],
                   boundary_contribution=['UNKNOWN','OVERLAP_OR_CROSSING'],certainty='ABSTAIN',
                   rationale='Synthetic uncertainty retained, not real evidence')
    return result


def test_protocol_unchanged_and_real_binding():
    assert ink.sha(ink.PROTOCOL)==ink.PROTOCOL_SHA
    p,source = ink.verify_inputs()
    assert p['source_dimensions']==[2481,3508]
    assert ink.sha(source)==p['source_sha256']


def test_prepare_no_official_sample(study,monkeypatch):
    tmp,p,source,paths = study
    monkeypatch.setattr(ink,'select',lambda *args:pytest.fail('preparation must not sample'))
    result = ink.prepare(tmp/'kit')
    assert result['status']=='NOT_READY' and result['official_selected_anchors']==0
    assert result['source_only_screening_tile_pngs']==1
    assert result['screening_tiles_are_official_anchors'] is False
    assert not (tmp/'kit'/'packet.json').exists()
    assert ink.sha(tmp/'kit'/'source.png')==ink.sha(source)
    assert (tmp/'kit'/'source.png').stat().st_mode & 0o222 == 0
    assert all(t['status'] is None for t in ink.load(tmp/'kit'/'screening-template.json')['tiles'])
    with pytest.raises(ValueError,match='new output'):
        ink.prepare(tmp/'kit')


def test_rank_is_exact_all_pixel_grid(study):
    tmp,p,source,paths = study
    screening = ink.frozen(paths[2],'screening')['content']
    anchors, counts = ink.select(p,screening)
    expected=[]
    w,h=p['source_dimensions']
    for r in range(4):
        for c in range(4):
            ranked=[]
            for y in range(r*h//4,(r+1)*h//4):
                for x in range(c*w//4,(c+1)*w//4):
                    msg=f"{p['seed']}|{p['source_sha256']}|prevalence|{c}|{r}|{x}|{y}"
                    ranked.append((hashlib.sha256(msg.encode()).digest(),y,x))
            expected.extend((x,y) for _,y,x in sorted(ranked)[:6])
    assert [(a['x'],a['y']) for a in anchors]==expected
    assert len(anchors)==96 and sum(x['population'] for x in counts['cells'])==w*h
    # Changing appearance cannot affect this function: it receives no raster.
    assert ink.rank(p,'presentation',0,1)==hashlib.sha256(
        f"{p['seed']}|{p['source_sha256']}|presentation|0|1".encode()).digest()


def test_small_page_shortfall_and_diagnostic_dedup(study):
    tmp,p,source,paths = study
    p=deepcopy(p); p['source_dimensions']=[1,1]
    screening={'tiles':[{'status':'examined','nominations':[
        {'motif':m,'x':0,'y':0} for m in p['diagnostic']['motif_order']]}]}
    anchors,stats=ink.select(p,screening)
    assert len(anchors)==1
    assert sum(c['selected'] for c in stats['cells'])==1
    assert all(m['duplicate_exclusions']==1 and m['selected_unique_anchors']==0 for m in stats['motifs'])


def test_diagnostic_rank_and_earlier_motif_exclusions(study):
    tmp,p,source,paths=study
    base,_=ink.select(p,{'tiles':[]})
    selected={(a['x'],a['y']) for a in base}
    available=[(x,y) for y in range(13) for x in range(12) if (x,y) not in selected]
    # select is tested directly with synthetic nomination lists; production validation
    # enforces one nominee per motif/tile before selection can run.
    motifs=p['diagnostic']['motif_order']
    screening={'tiles':[{'status':'examined','nominations':[
        {'motif':m,'x':x,'y':y} for m in motifs for x,y in available[:20]]}]}
    anchors,stats=ink.select(p,screening)
    assert len({(a['x'],a['y']) for a in anchors})==len(anchors)
    assert [s['selected_unique_anchors'] for s in stats['motifs']]==[8,8,4,0]
    first=sorted(available[:20],key=lambda xy:(ink.rank(p,'diagnostic',motifs[0],*xy),xy[1],xy[0]))[:8]
    assert [(a['x'],a['y']) for a in anchors if a.get('motif')==motifs[0]]==first


@pytest.mark.parametrize('change', ['blank_roster','duplicate_person','excluded_role','blank_training','same_training_page',
                                   'incomplete_screening','unsourced_screening','bad_nomination','screening_signer','order'])
def test_prerequisites_fail_closed(study,change):
    tmp,p,source,paths=study
    r,t,s=[ink.load(x) for x in paths]
    if change=='blank_roster': r['content']['people'][0]['human']=None
    if change=='duplicate_person': r['content']['people'][0]['person_id']='B'
    if change=='excluded_role': r['content']['people'][0]['excluded_roles']=['assistant']
    if change=='blank_training': t['content']['excluded_pages']=[]
    if change=='same_training_page': t['content']['excluded_pages'][0]['source_sha256']=p['source_sha256']
    if change=='incomplete_screening': s['content']['tiles'][0]['status']=None
    if change=='unsourced_screening': s['content']['source_only']=False
    if change=='bad_nomination': s['content']['tiles'][0]['nominations']=[{'motif':p['diagnostic']['motif_order'][0],'x':999,'y':0}]
    if change=='screening_signer': s['signature']['person_id']='A'
    if change=='order': s['frozen_at']='2000-01-01T00:00:00+00:00'; s['signature']['signed_at']=s['frozen_at']
    for path,e in zip(paths,(r,t,s)):
        path.chmod(0o644); e['content_sha256']=ink.digest(e['content']); path.write_text(json.dumps(e))
        receipt=ink.receipt_path(path); receipt.chmod(0o644)
        receipt.write_text(json.dumps({'file_sha256':ink.sha(path)}))
    with pytest.raises(ValueError):
        build(study)
    assert not (tmp/'packet').exists()


def test_missing_prerequisite_never_samples(study,monkeypatch):
    tmp,p,source,paths=study
    monkeypatch.setattr(ink,'select',lambda *a:pytest.fail('must not sample'))
    paths[0].unlink()
    with pytest.raises(FileNotFoundError): build(study)
    assert not (tmp/'packet').exists()


def test_packet_blinded_order_native_crops(study):
    tmp,p,source,paths=study
    out,audit=build(study)
    pp,m,a=ink.verify_packet(out,audit)
    assert [c['case_id'] for c in m['cases']]==sorted(c['case_id'] for c in m['cases'])
    assert all(set(c)=={'case_id','focus','context'} for c in m['cases'])
    assert not any(f.name=='private-audit.json' for f in out.iterdir())
    assert ink.sha(source)==ink.sha(out/'source.png')
    with Image.open(source) as image:
        for c,anchor in zip(m['cases'],a['anchors']):
            for s,name in ((65,'focus'),(513,'context')):
                box=ink.bounds(anchor['x'],anchor['y'],s,*image.size)
                with Image.open(out/c[name]['file']) as actual:
                    assert actual.size==image.crop(box).size
                    assert actual.tobytes()==image.crop(box).tobytes()
                assert c[name]['target']==[anchor['x']-box[0],anchor['y']-box[1]]
    assert ink.bounds(0,0,65,100,100)==[0,0,33,33]
    assert ink.bounds(99,99,513,100,100)==[0,0,100,100]
    with pytest.raises(ValueError,match='new packet'): build(study)


def test_colliding_public_ids_halt_before_output(study,monkeypatch):
    tmp,p,source,paths=study
    real=ink.rank
    monkeypatch.setattr(ink,'rank',lambda p,*parts:b'0'*32 if parts[0]=='presentation' else real(p,*parts))
    with pytest.raises(ValueError,match='collision'): build(study)
    assert not (tmp/'packet').exists()


def test_overlap_exact_union():
    assert ink.overlap([[0,0,2,2],[1,1,3,3],[0,0,2,2]])=={
        'unique_crop_rectangles':2,'overlapping_pair_count':3,'union_area':7}
    assert ink.overlap([])['union_area']==0


@pytest.mark.parametrize('change', ['blank','missing','duplicate','mixed_enum','empty_boundary','rationale','signer','ownership','attestation','binding','backdated'])
def test_invalid_submissions_do_not_freeze(study,change):
    tmp,p,source,paths=study
    out,audit=build(study)
    data=submission(study,out,'A')
    if change=='blank': data=ink.load(out/'submission-template.json')
    if change=='missing': data['labels'].pop()
    if change=='duplicate': data['labels'][1]['case_id']=data['labels'][0]['case_id']
    if change=='mixed_enum': data['labels'][0]['physical_content']=['MIXED']
    if change=='empty_boundary': data['labels'][0]['boundary_contribution']=[]
    if change=='rationale': data['labels'][0]['rationale']=' '
    if change=='signer': data['signature']['person_id']='B'
    if change=='ownership': data['labels'][0]['ownership']={'contributors':['predicted-group'],'unresolved':False}
    if change=='attestation': data['source_only_independent']=False
    if change=='binding': data['packet_sha256']='a'*64
    if change=='backdated': data['signature']['signed_at']='2000-01-01T00:00:00+00:00'
    path=put(tmp/'input.json',data)
    with pytest.raises(ValueError): ink.submit(out,audit,'A',path,tmp/'archive')
    assert not (tmp/'archive'/'A.json').exists()


def test_separate_freezes_comparison_adjudication_unknown_preserved(study):
    tmp,p,source,paths=study
    out,audit=build(study); archive=tmp/'archive'
    data=submission(study,out,'A')
    a_path=put(tmp/'A-input.json',data)
    receipt=ink.submit(out,audit,'A',a_path,archive)
    assert 'labels' not in receipt
    a_bytes=(archive/'A.json').read_bytes()
    with pytest.raises(ValueError,match='never overwrite'): ink.submit(out,audit,'A',a_path,archive)
    with pytest.raises(ValueError,match='both independent'): ink.disagree(out,audit,archive,tmp/'premature')
    assert not (tmp/'premature').exists()
    b=submission(study,out,'B'); b['labels'][0]['physical_content']=['TEXT','UNKNOWN']
    ink.submit(out,audit,'B',put(tmp/'B-input.json',b),archive)
    result=ink.disagree(out,audit,archive,tmp/'report')
    assert result['both_primaries_frozen']
    report=ink.load(tmp/'report'/'source-only-comparison.json')
    assert report['rows'][0]['A']['certainty']=='ABSTAIN'
    assert 'UNKNOWN' in report['rows'][0]['B']['physical_content']
    assert all('arm' not in row and 'x' not in row for row in report['rows'])
    stats=ink.load(tmp/'report'/'custodian-statistics.json')
    assert stats['arms']['prevalence']['disagreement_count']==1
    assert stats['arms']['prevalence']['unknown_abstain']['A']['abstain']==96
    adjud=submission(study,out,'adjudicator')
    adjud['primary_sha256']=report['primary_sha256']
    for row in adjud['labels']: row['alternatives_and_disposition']='Synthetic alternatives retained UNKNOWN'
    target=tmp/'adjudication.json'
    ink.adjudicate(out,audit,archive,put(tmp/'adjud-input.json',adjud),target)
    assert ink.frozen(target,'adjudication')['content']['labels'][0]['ownership']['unresolved']
    assert (archive/'A.json').read_bytes()==a_bytes
    with pytest.raises(ValueError,match='already exists'): ink.adjudicate(out,audit,archive,tmp/'adjud-input.json',target)


@pytest.mark.parametrize('which',['source','focus','context','protocol','prerequisite','audit','primary'])
def test_tampered_frozen_content_halts(study,which,monkeypatch):
    tmp,p,source,paths=study
    out,audit=build(study); archive=tmp/'archive'
    for role in ('A','B'):
        ink.submit(out,audit,role,put(tmp/f'{role}-input.json',submission(study,out,role)),archive)
    if which=='protocol':
        monkeypatch.setattr(ink,'PROTOCOL_SHA','0'*64)
    else:
        target={'source':out/'source.png','focus':out/ink.load(out/'packet.json')['cases'][0]['focus']['file'],
                'context':out/ink.load(out/'packet.json')['cases'][0]['context']['file'],
                'prerequisite':paths[0],'audit':audit,'primary':archive/'A.json'}[which]
        target.chmod(0o644)
        if which in ('audit','primary'):
            e=ink.load(target)
            if which=='primary': e['content']['labels'][0]['rationale']='tampered'
            else: e['content']['anchors'][0]['x']=999
            target.write_text(json.dumps(e))
        else: target.write_bytes(target.read_bytes()+b'tampered')
    with pytest.raises(ValueError): ink.disagree(out,audit,archive,tmp/'report')
    assert not (tmp/'report').exists()


def test_crop_native_sizes_and_edge_local_target():
    source = Image.new('L', (601,701), 127)
    for size in (65,513):
        box=ink.bounds(300,350,size,*source.size)
        assert source.crop(box).size==(size,size)
        assert (300-box[0],350-box[1])==(size//2,size//2)
        edge=ink.bounds(0,700,size,*source.size)
        assert source.crop(edge).size==(size//2+1,size//2+1)
        assert (0-edge[0],700-edge[1])==(0,size//2)


def test_recomputed_internal_digest_still_fails_external_receipt(study):
    tmp,p,source,paths=study
    out,audit=build(study); archive=tmp/'archive'
    for role in ('A','B'):
        ink.submit(out,audit,role,put(tmp/f'{role}-input.json',submission(study,out,role)),archive)
    path=archive/'A.json'
    data=ink.load(path); data['content']['labels'][0]['rationale']='tampered'
    data['content_sha256']=ink.digest(data['content'])
    path.chmod(0o644);path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='receipt mismatch'):
        ink.disagree(out,audit,archive,tmp/'report')


@pytest.mark.parametrize('kind',['extra_file','extra_directory','symlink_crop','symlink_packet','symlink_receipt'])
def test_packet_rejects_unexpected_entries_and_symlinks(study,kind):
    tmp,p,source,paths=study
    out,audit=build(study)
    if kind=='extra_file':
        (out/'hidden-solution-key.json').write_text('{"expected_pitch":"C4"}')
    elif kind=='extra_directory':
        (out/'private-evidence').mkdir()
    elif kind=='symlink_crop':
        crop=out/ink.load(out/'packet.json')['cases'][0]['focus']['file']
        target=tmp/'original-crop.png'; crop.rename(target); crop.symlink_to(target)
    elif kind=='symlink_packet':
        alias=tmp/'linked-packet';alias.symlink_to(out,target_is_directory=True);out=alias
    else:
        receipt=ink.receipt_path(audit)
        target=tmp/'original-receipt.json'; receipt.rename(target);receipt.symlink_to(target)
    with pytest.raises(ValueError,match='unexpected|symlink'):
        ink.verify_packet(out,audit)


@pytest.mark.parametrize('level',['top','row','signature'])
@pytest.mark.parametrize('role',['A','adjudicator'])
def test_prediction_fields_rejected_at_each_submission_boundary(study,level,role):
    tmp,p,source,paths=study
    out,audit=build(study)
    pp,m,a=ink.verify_packet(out,audit)
    content=submission(study,out,role)
    if role=='adjudicator':
        content['primary_sha256']={'A':'a'*64,'B':'b'*64}
        for row in content['labels']:
            row['alternatives_and_disposition']='Synthetic alternatives retained'
    target={'top':content,'row':content['labels'][0],'signature':content['signature']}[level]
    target['expected_pitch']='predicted ownership must never reach comparison'
    with pytest.raises(ValueError,match='fields'):
        ink.validate_labels(content,pp,m,a,role)


@pytest.mark.parametrize('operation',['prepare','packet','audit','archive','report','adjudication','freeze','tile_export'])
def test_outputs_cannot_enter_immutable_source_evidence(study,monkeypatch,operation):
    tmp,p,source,paths=study
    protected=tmp/'immutable-source-evidence';protected.mkdir()
    sentinel=protected/'source.png';sentinel.write_bytes(source.read_bytes())
    monkeypatch.setattr(ink,'evidence_root',lambda:protected.resolve())
    target=protected/'new-output'
    before=sentinel.read_bytes()
    with pytest.raises(ValueError,match='immutable source evidence'):
        if operation=='prepare': ink.prepare(target)
        elif operation=='packet': ink.packet(target,tmp/'audit.json',*paths)
        elif operation=='audit': ink.packet(tmp/'packet',target,*paths)
        elif operation=='archive': ink.submit(tmp/'packet',tmp/'audit.json','A',tmp/'input.json',target)
        elif operation=='report': ink.disagree(tmp/'packet',tmp/'audit.json',tmp/'archive',target)
        elif operation=='adjudication': ink.adjudicate(tmp/'packet',tmp/'audit.json',tmp/'archive',tmp/'input.json',target)
        elif operation=='freeze': ink.freeze('roster',tmp/'input.json',tmp/'signature.json',target)
        else: ink.export_screening_tiles(source,target)
    assert sentinel.read_bytes()==before and not target.exists()


def test_output_symlink_to_evidence_rejected_and_no_receipt_alias(study,monkeypatch):
    tmp,p,source,paths=study
    protected=tmp/'immutable';protected.mkdir()
    monkeypatch.setattr(ink,'evidence_root',lambda:protected.resolve())
    alias=tmp/'evidence-alias';alias.symlink_to(protected,target_is_directory=True)
    with pytest.raises(ValueError,match='symlink'):
        ink.prepare(alias/'new-kit')
    out=tmp/'audit.json.receipt.json'
    with pytest.raises(ValueError,match='alias'):
        ink.packet(out,tmp/'audit.json',*paths)
    assert not out.exists()


def test_archive_cannot_leak_primary_labels_inside_packet(study):
    tmp,p,source,paths=study
    out,audit=build(study)
    content=put(tmp/'A-input.json',submission(study,out,'A'))
    with pytest.raises(ValueError,match='outside packet'):
        ink.submit(out,audit,'A',content,out/'private-archive')
    assert not (out/'private-archive').exists()


def test_native_screening_tiles_cover_entire_page_and_clipped_edges(tmp_path):
    source=tmp_path/'synthetic-tiles-source.png'
    image=Image.new('RGB',(130,129))
    image.putdata([(x%256,y%256,(x+3*y)%256) for y in range(129) for x in range(130)])
    image.save(source)
    records=ink.export_screening_tiles(source,tmp_path/'tiles')
    assert len(records)==9
    assert [r['bounds'] for r in records]==[r['bounds'] for r in ink.tiles(130,129)]
    reconstructed=Image.new('RGB',image.size)
    for tile in records:
        path=tmp_path/'tiles'/tile['file']
        assert ink.sha(path)==tile['sha256'] and path.stat().st_mode & 0o222==0
        with Image.open(path) as crop:
            assert crop.tobytes()==image.crop(tile['bounds']).tobytes()
            reconstructed.paste(crop,tuple(tile['bounds'][:2]))
    assert reconstructed.tobytes()==image.tobytes()
    with Image.open(tmp_path/'tiles'/records[-1]['file']) as corner:
        assert corner.size==(2,1)
    assert ink.sha(source)==hashlib.sha256(source.read_bytes()).hexdigest()
