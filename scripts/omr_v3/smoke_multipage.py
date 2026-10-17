"""Exercise real page-local OMR/fallback and ZIP packaging against a running API."""
import argparse
import io
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path

import requests
from PIL import Image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[2]
    scores = root / 'tests/omr_v3_eval/scores'
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # Preserve the degraded raster's native density through PDF inspection.
        with Image.open(scores / 'naui.jpg') as image:
            image.convert('RGB').save(tmp / 'degraded.pdf', resolution=90)
        source = tmp / 'three-pages.pdf'
        subprocess.run(['pdfunite', str(scores / 'jusim.pdf'), str(tmp / 'degraded.pdf'),
                        str(scores / 'chingu.pdf'), str(source)], check=True)
        response = requests.post(args.url.rstrip('/') + '/api/v3/score/transpose.zip',
                                 files={'file': ('three-pages.pdf', source.read_bytes(), 'application/pdf')},
                                 data={'mode': 'key', 'semitones': '2'}, timeout=1200)
        response.raise_for_status()
        (args.out / 'multipage.zip').write_bytes(response.content)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            report = json.loads(archive.read('conversion-report.json'))
            assert report['document']['page_count'] == 3, report
            assert [page['page'] for page in report['pages']] == [1, 2, 3], report
            assert report['pages'][1]['mode'] in ('chord_only', 'failure'), report
            assert all(page['mode'] == 'failure' or page.get('integrity', {}).get('ok', True)
                       for page in report['pages']), report
        (args.out / 'multipage-report.json').write_text(json.dumps(report, indent=2))
        print(json.dumps({'document': report['document'],
                          'page_modes': [page['mode'] for page in report['pages']]}))


if __name__ == '__main__':
    main()
