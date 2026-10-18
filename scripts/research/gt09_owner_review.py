"""Loopback-only owner annotation tool. Never independent ground truth or edit authority."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from scripts.research.gt08_review import COORDINATES, read_json, verify_packet

VERSION = 'gt09-owner-review/1'
LABELS = ('TEXT', 'NON_TEXT', 'MIXED', 'UNKNOWN')
UNREVIEWED = 'UNREVIEWED'
DEFAULT_PACKET = Path(
    '/private/tmp/capomatic-v4-gt08-text/gt08-output/reviewer-handoff/source-only-packet'
)
EXPECTED_PACKET = '0fa69a361b41a713979b5736c2b30dae5037e3af30e10dfdef3d4771bb10a217'
UI = Path(__file__).with_name('gt09_ui')


def encoded(data):
    return (
        json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
        + '\n'
    ).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def integer(value):
    return type(value) is int


def validate_case(value, case, complete=False):
    require(
        isinstance(value, dict)
        and set(value)
        == {
            'case_id',
            'image_sha256',
            'width',
            'height',
            'runs',
            'finalized',
            'uncertainty_acknowledged',
        },
        '잘못된 사례 필드',
    )
    require(
        all(value[k] == case[k] for k in ('case_id', 'width', 'height'))
        and value['image_sha256'] == case['sha256'],
        '사례/이미지/크기 불일치',
    )
    require(integer(value['width']) and integer(value['height']), '정수 크기 필요')
    require(
        type(value['finalized']) is bool and type(value['uncertainty_acknowledged']) is bool,
        '확정 상태 오류',
    )
    require(isinstance(value['runs'], list), 'RLE 배열 필요')
    counts = dict.fromkeys((*LABELS, UNREVIEWED), 0)
    expected = (0, 0)
    previous_label = None
    for run in value['runs']:
        require(isinstance(run, list) and len(run) == 4, 'RLE는 [y,left,right_exclusive,label]')
        y, left, right, label = run
        require(all(integer(n) for n in (y, left, right)), '정수 좌표 필요')
        require(
            label in counts and 0 <= y < case['height'] and 0 <= left < right <= case['width'],
            'RLE 범위/범주 오류',
        )
        require((y, left) == expected, '누락/중복/정렬 오류')
        require(
            not (left > 0 and label == previous_label),
            '인접 동일 범주는 하나의 정규 RLE로 저장해야 합니다',
        )
        counts[label] += right - left
        previous_label = label
        expected = (y + 1, 0) if right == case['width'] else (y, right)
    require(expected == (case['height'], 0), '픽셀 누락')
    if complete or value['finalized']:
        require(value['finalized'] and counts[UNREVIEWED] == 0, '미검토 픽셀이 남았습니다')
        require(value['uncertainty_acknowledged'], 'UNKNOWN/MIXED 커버리지 확인 필요')
    return counts


class ReviewStore:
    def __init__(self, packet, output, expected_packet=EXPECTED_PACKET):
        self.packet = Path(packet).resolve()
        self.output = Path(output).resolve()
        require(
            not (
                self.output == self.packet
                or self.packet in self.output.parents
                or self.output in self.packet.parents
            ),
            '원본 패킷과 저장 경로를 분리하세요',
        )
        # GT08 custody directories must never become owner-review storage.
        require(
            'gt08-output' not in self.output.parts, 'GT08 독립 리뷰 경로에는 저장할 수 없습니다'
        )
        self.packet_sha = expected_packet
        self.lock = threading.Lock()
        self.verify()
        self.output.mkdir(parents=True, exist_ok=True)
        require(
            not any(p.is_symlink() for p in [Path(output), *Path(output).parents]),
            '심볼릭 링크 저장 경로 거부',
        )
        self.state_path = self.output / 'owner-state.json'
        if self.state_path.exists():
            self.validate_state(read_json(self.state_path))

    def verify(self):
        require(
            sha((self.packet / 'packet.json').read_bytes()) == self.packet_sha,
            '원본 패킷 해시 불일치',
        )
        self.cases = verify_packet(self.packet)
        self.manifest = read_json(self.packet / 'packet.json')

    def empty(self):
        return {
            'version': VERSION,
            'review_type': 'OWNER_REVIEW',
            'evidence_status': 'NOT_INDEPENDENT_GROUND_TRUTH',
            'packet_sha256': self.packet_sha,
            'coordinate_system': COORDINATES,
            'revision': 0,
            'cases': {},
        }

    def validate_state(self, state):
        require(isinstance(state, dict) and set(state) == set(self.empty()), '저장 형식 오류')
        for k, v in self.empty().items():
            if k not in ('revision', 'cases'):
                require(state[k] == v, 'OWNER_REVIEW 패킷/좌표/출처 불일치')
        require(
            integer(state['revision'])
            and state['revision'] >= 0
            and isinstance(state['cases'], dict),
            '저장 버전 오류',
        )
        require(set(state['cases']) <= set(self.cases), '알 수 없는 사례')
        for key, value in state['cases'].items():
            require(value['case_id'] == key, '사례 키 불일치')
            validate_case(value, self.cases[key])

    def load(self):
        self.verify()
        state = read_json(self.state_path) if self.state_path.exists() else self.empty()
        self.validate_state(state)
        return state

    def save(self, state):
        with self.lock:
            old = self.load()
            self.validate_state(state)
            require(
                state['revision'] == old['revision'],
                '다른 탭에서 저장했습니다. 새로고침 후 다시 작업하세요',
            )
            state = dict(state, revision=old['revision'] + 1)
            temp = self.output / ('state-' + secrets.token_hex(8) + '.tmp')
            try:
                with temp.open('xb') as f:
                    f.write(encoded(state))
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp, self.state_path)
            finally:
                temp.unlink(missing_ok=True)
            return state

    def export(self):
        with self.lock:
            state = self.load()
            require(set(state['cases']) == set(self.cases), '다섯 사례를 모두 검토·확정하세요')
            coverage = {}
            for key, case in self.cases.items():
                coverage[key] = validate_case(state['cases'][key], case, complete=True)
            result = {k: v for k, v in state.items() if k != 'revision'}
            result.update(
                {
                    'cases': [state['cases'][c] for c in self.cases],
                    'coverage': coverage,
                    'composition_authorized': False,
                    'protection_masks_modified': False,
                }
            )
            data = encoded(result)
            folder = self.output / 'owner-review-exports'
            require(not folder.is_symlink(), '심볼릭 링크 내보내기 경로 거부')
            folder.mkdir(exist_ok=True)
            path = folder / (sha(data) + '.json')
            require(not path.is_symlink(), '심볼릭 링크 내보내기 파일 거부')
            if path.exists():
                require(path.read_bytes() == data, '내보내기 충돌')
            else:
                temp = folder / ('export-' + secrets.token_hex(8) + '.tmp')
                try:
                    with temp.open('xb') as f:
                        f.write(data)
                        f.flush()
                        os.fsync(f.fileno())
                    temp.chmod(0o444)
                    # Publish the complete bytes atomically without replacing any export.
                    os.link(temp, path)
                finally:
                    temp.unlink(missing_ok=True)
            return data


def handler(store, token):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, content, kind='application/json; charset=utf-8'):
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header(
                'Content-Security-Policy',
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(content)

        def trusted_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def do_GET(self):
            if not self.trusted_host():
                self.reply(403, encoded({'error': '로컬 주소만 허용합니다'}))
                return
            path = urlsplit(self.path).path
            try:
                if path == '/':
                    self.reply(
                        200,
                        (UI / 'index.html').read_bytes().replace(b'__TOKEN__', token.encode()),
                        'text/html; charset=utf-8',
                    )
                elif path in ('/app.js', '/model.js', '/style.css'):
                    self.reply(
                        200,
                        (UI / path[1:]).read_bytes(),
                        'text/css' if path.endswith('css') else 'text/javascript',
                    )
                elif path == '/api/packet':
                    store.verify()
                    self.reply(200, encoded(dict(store.manifest, packet_sha256=store.packet_sha)))
                elif path == '/api/state':
                    self.reply(200, encoded(store.load()))
                elif path.startswith('/case/') and path[6:] in store.cases:
                    store.verify()
                    self.reply(
                        200,
                        (store.packet / store.cases[path[6:]]['image']).read_bytes(),
                        'image/png',
                    )
                else:
                    self.reply(404, encoded({'error': '없는 경로'}))
            except (ValueError, OSError) as exc:
                self.reply(400, encoded({'error': str(exc)}))

        def do_POST(self):
            origin = self.headers.get('Origin')
            if (
                not self.trusted_host()
                or self.headers.get('X-Review-Token') != token
                or origin not in (None, f'http://127.0.0.1:{self.server.server_port}')
            ):
                self.reply(403, encoded({'error': '로컬 검토 세션이 아닙니다'}))
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                require(0 <= size <= 16 * 1024 * 1024, '요청 크기 초과')
                raw = self.rfile.read(size)
                path = urlsplit(self.path).path
                if path == '/api/state':
                    # Strict loader rejects duplicate fields and nonfinite numbers.
                    def pairs(items):
                        d = {}
                        for k, v in items:
                            require(k not in d, '중복 JSON 필드')
                            d[k] = v
                        return d

                    state = json.loads(
                        raw,
                        object_pairs_hook=pairs,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('비유한 수')),
                    )
                    self.reply(200, encoded(store.save(state)))
                elif path == '/api/export':
                    self.reply(200, store.export())
                else:
                    self.reply(404, encoded({'error': '없는 경로'}))
            except (ValueError, TypeError, KeyError, OSError) as exc:
                self.reply(400, encoded({'error': str(exc)}))

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path, default=DEFAULT_PACKET)
    parser.add_argument('--out', type=Path, default=Path('gt09-output'))
    parser.add_argument('--port', type=int, default=8769)
    args = parser.parse_args()
    store = ReviewStore(args.packet, args.out)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler(store, secrets.token_hex(32)))
    print(
        f'OWNER_REVIEW / NOT_INDEPENDENT_GROUND_TRUTH\nhttp://127.0.0.1:{server.server_port}\n저장: {store.output}',
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
