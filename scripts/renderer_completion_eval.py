"""Real HTTP evaluation. Native controls are development tests, never OMR accuracy."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import time
import unicodedata
import zipfile

import httpx
import numpy as np
from PIL import Image, ImageDraw
from pypdf import PdfReader
from music21 import converter

from scripts.controlled_native_score import make_fixture


def sha(data):
    return hashlib.sha256(data).hexdigest()


def raster(pdf, destination):
    subprocess.run(['pdftocairo','-r','300','-singlefile','-png',str(pdf),str(destination)],check=True)
    return Image.open(destination.with_suffix('.png')).convert('RGB')


def boxes(data):
    reader=PdfReader(io.BytesIO(data))
    return [{'rotation':p.rotation,'boxes':{name:list(map(float,getattr(p,name)))
             for name in ('mediabox','cropbox','trimbox','bleedbox','artbox')}} for p in reader.pages]


def source_alpha(data, name):
    image=PdfReader(io.BytesIO(data)).pages[0]['/Resources']['/XObject']['/'+name].get_object()
    return Image.frombytes('L',(image['/Width'],image['/Height']),image['/SMask'].get_object().get_data())


def check_control(source, reference, source_png, reference_png, target_png, pdf, xml, profile, expected):
    assert target_png.tobytes()==reference_png.tobytes(), 'Independent paired source raster differs'
    assert boxes(source)==boxes(pdf)
    page=PdfReader(io.BytesIO(pdf)).pages[0]
    image=page['/Resources']['/XObject']['/PageRaster'].get_object()
    assert image.get_data()==target_png.tobytes(), 'PDF embedded pixels differ'
    actual=converter.parseData(xml.decode(),format='musicxml')
    assert [n.pitch.nameWithOctave for n in actual.recurse().notes]==expected
    assert all(n.quarterLength==4 for n in actual.recurse().notes)
    lyric=np.asarray(source_alpha(source,'Lyrics'))>0
    assert np.array_equal(np.asarray(source_png)[lyric],np.asarray(target_png)[lyric])
    staff=np.asarray(source_alpha(source,'Staff'))>0
    source_music=np.asarray(source_alpha(source,'Music'))>0
    target_music=np.asarray(source_alpha(reference,'Music'))>0
    edits=source_music|target_music
    assert np.array_equal(np.asarray(source_png)[~edits],np.asarray(target_png)[~edits])
    assert not np.count_nonzero(target_music&lyric)
    removed=source_music&~target_music&~staff
    assert np.all(np.asarray(target_png)[removed]==255)
    # Observe output pixels without consuming the renderer's anchor metrics.
    residual=[]
    source_entry=json.loads(PdfReader(io.BytesIO(source)).trailer['/Root']['/CapomaticSource'].get_object().get_data())['pages'][0]
    source_pitches=[n.pitch.nameWithOctave for n in converter.parseData(source_entry['musicxml'],format='musicxml').recurse().notes]
    source_grey=np.asarray(source_png.convert('L'))
    step={'C':1,'D':2,'E':3,'F':4,'G':5,'A':6,'B':7}
    grey=np.asarray(target_png.convert('L'))
    for x,name,source_name in zip(profile['note_x'],expected,source_pitches):
        number=int(name[-1])*7+step[name[0]]
        y=profile['staff_top']+4*profile['interline']-(number-31)*profile['interline']/2
        x0,x1=int(x-40),int(x+40);y0,y1=int(y-24),int(y+25)
        mask=(grey[y0:y1,x0:x1]<255)&~staff[y0:y1,x0:x1]
        yy,xx=np.where(mask)
        assert len(xx)>0
        observed=[x0+(int(xx.min())+int(xx.max()))/2,y0+(int(yy.min())+int(yy.max()))/2]
        error=[observed[0]-x,observed[1]-y]
        assert max(map(abs,error))<=.5
        source_number=int(source_name[-1])*7+step[source_name[0]]
        source_y=profile['staff_top']+4*profile['interline']-(source_number-31)*profile['interline']/2
        sy0,sy1=int(source_y-24),int(source_y+25)
        source_mask=(source_grey[sy0:sy1,x0:x1]<255)&~staff[sy0:sy1,x0:x1]
        _,source_xs=np.where(source_mask)
        source_x=x0+(int(source_xs.min())+int(source_xs.max()))/2
        assert observed[0]==source_x, 'Fixed source notehead x changed'
        residual.append({'pitch':name,'target':[x,y],'observed':observed,'error':error,
                         'source_observed_x':source_x,'fixed_x_displacement_px':observed[0]-source_x})
    return {'paired_reference_pixel_difference':0,'lyric_pixel_difference':0,
            'preserved_lyric_ink_pixels':int(np.count_nonzero(lyric)),
            'protected_pixel_difference':0,'old_music_residual_pixels':0,
            'source_staff_reconstructed_pixels':int(np.count_nonzero(source_music&staff)),
            'original_preserved_pixels':int(np.count_nonzero(~edits)),
            'notehead_observations':residual,'page_boxes_equal':True,
            'pdf_embedded_pixels_equal_png':True,'unexplained_alpha_collisions':0,
            'recognition_accuracy':'UNVERIFIED; native source-provided semantics'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api',required=True)
    parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    baseline=json.loads(Path('docs/evidence/SCORE_GEOMETRY_EVALUATION.json').read_text())
    expected_hash={unicodedata.normalize('NFC',r['name']):r['source_sha256'] for r in baseline['rows']}
    paths=[Path(p) for p in json.loads(args.inputs.read_text())]
    result={'status':'FUNCTIONALLY_INCOMPLETE_FOR_ORDINARY_SCANNED_SCORES',
            'dataset':'development inputs; no hidden/independent validation set',
            'real':[],'controlled':[]}
    def persist():
        (args.out/'evaluation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    with httpx.Client(base_url=args.api,timeout=900) as client:
        client.get('/health').raise_for_status()
        for index,path in enumerate(paths,1):
            data=path.read_bytes();name=unicodedata.normalize('NFC',path.name)
            assert sha(data)==expected_hash[name], 'Historical input mismatch'
            folder=args.out/f'real-{index}';folder.mkdir()
            detected=client.post('/detect',files={'image':(path.name,data,'application/pdf')})
            (folder/'detect.json').write_bytes(detected.content)
            details=detected.json(); details=details if detected.status_code==200 else details['detail']
            print('REAL DETECT',index,detected.status_code,flush=True)
            for shift in (0,1,-1):
                response=client.post('/render',data={'detection_id':details['detection_id'],
                                    'semitones':shift,'output_format':'pdf','mode':'key'})
                record={'input':name,'index':index,'source_sha256':sha(data),'shift':shift,
                        'detect_http':detected.status_code,'render_http':response.status_code,
                        'response_sha256':sha(response.content),'recognition_accuracy':'UNVERIFIED',
                        'source_unchanged':sha(path.read_bytes())==sha(data)}
                (folder/f'{shift:+d}-response.bin').write_bytes(response.content)
                if response.status_code==200:
                    assert shift==0 and response.headers['x-capomatic-identity']=='true'
                    assert response.content==data and boxes(response.content)==boxes(data)
                    target=folder/'identity.pdf';target.write_bytes(response.content)
                    png=raster(target,folder/'identity-preview')
                    record.update(render_path='lossless_original_pdf_identity',output_pdf_sha256=sha(response.content),
                                  page_boxes_equal=True,all_original_bytes_preserved=True,
                                  preservation_contract_pass=True,nonzero_demonstrated=False)
                else:
                    assert response.status_code==422
                    report=response.json()['detail']['report'];record['report']=report
                    record['first_blocker']=report.get('first_blocker')
                    record['secondary_blockers']=report.get('secondary_blockers',[])
                    record['preservation_contract_pass']=False
                result['real'].append(record);persist()
                print('REAL RENDER',index,shift,response.status_code,flush=True)
        controls={}
        for fifths,label in ((0,'C'),(5,'B')):
            data,profile,xml=make_fixture(fifths);folder=args.out/f'controlled-{label}';folder.mkdir()
            (folder/'source.pdf').write_bytes(data);(folder/'source.musicxml').write_bytes(xml)
            png=raster(folder/'source.pdf',folder/'source')
            controls[label]={'data':data,'profile':profile,'png':png,'folder':folder}
        pitches={'C':['C5','E5','A4','F4'],'B':['B4','D#5','G#4','E4']}
        for label,c in controls.items():
            detected=client.post('/detect',files={'image':(f'controlled-{label}.pdf',c['data'],'application/pdf')})
            assert detected.status_code==200,detected.text
            (c['folder']/'detect.json').write_bytes(detected.content)
            ident=detected.json()['detection_id']
            for shift in (0,1,-1):
                response=client.post('/render',data={'detection_id':ident,'semitones':shift,'mode':'key','output_format':'zip'})
                row={'control':label,'shift':shift,'http':response.status_code,'response_sha256':sha(response.content)}
                if response.status_code==200:
                    reference_label=label if shift==0 else ('B' if label=='C' else 'C')
                    reference=controls[reference_label]
                    assert (label,shift) in [('C',0),('C',-1),('B',0),('B',1)]
                    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                        pdf=z.read('transposed.pdf');png=z.read('page-001.png');xml=z.read('page-001.musicxml')
                        report=json.loads(z.read('conversion-report.json'))
                    stem=c['folder']/f'{shift:+d}'
                    stem.with_suffix('.pdf').write_bytes(pdf);stem.with_suffix('.png').write_bytes(png)
                    stem.with_suffix('.musicxml').write_bytes(xml)
                    stem.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
                    target_png=Image.open(io.BytesIO(png)).convert('RGB')
                    checks=check_control(c['data'],reference['data'],c['png'],reference['png'],target_png,
                                         pdf,xml,c['profile'],pitches[reference_label])
                    rasterized=raster(stem.with_suffix('.pdf'),c['folder']/f'{shift:+d}-pdf-preview')
                    assert rasterized.tobytes()==target_png.tobytes()
                    checks['pdf_raster_pixel_difference']=0
                    row.update(render_path=report['render_path'],checks=checks,
                               pdf_sha256=sha(pdf),png_sha256=sha(png),musicxml_sha256=sha(xml),
                               native_semantic_accuracy='source provided, not independently measured OMR')
                    # Comparison labels are outside the untouched page images.
                    compare=Image.new('RGB',(target_png.width,target_png.height*2+64),'white')
                    compare.paste(c['png'],(0,32));compare.paste(target_png,(0,target_png.height+64))
                    draw=ImageDraw.Draw(compare);draw.text((10,8),f'SOURCE {label}',fill='black')
                    draw.text((10,target_png.height+40),f'TARGET shift {shift:+d}',fill='black')
                    compare.save(c['folder']/f'{shift:+d}-comparison.png')
                    # Exercise actual standalone PNG and PDF response paths too.
                    for fmt in ('png','pdf'):
                        extra=client.post('/render',data={'detection_id':ident,'semitones':shift,'output_format':fmt})
                        assert extra.status_code==200
                        assert extra.content==(png if fmt=='png' else pdf)
                    row['standalone_png_pdf_http_verified']=True
                else:
                    assert response.status_code==422
                    row['failure']=response.json();(c['folder']/f'{shift:+d}-failure.json').write_bytes(response.content)
                result['controlled'].append(row);persist()
                print('CONTROL RENDER',label,shift,response.status_code,flush=True)
    result['counts']={
        'real_identity_success':sum(r['render_http']==200 and r['shift']==0 for r in result['real']),
        'real_nonzero_success':sum(r['render_http']==200 and r['shift']!=0 for r in result['real']),
        'real_safe_evidence_rejections':sum(r['render_http']==422 for r in result['real']),
        'controlled_identity_success':sum(r['http']==200 and r['shift']==0 for r in result['controlled']),
        'controlled_nonzero_success':sum(r['http']==200 and r['shift']!=0 for r in result['controlled']),
        'controlled_unsupported_rejections':sum(r['http']==422 for r in result['controlled'])}
    persist()


if __name__=='__main__':main()
