import { useState, type FormEvent } from 'react';
import Head from 'next/head';
import Link from 'next/link';

const API = process.env.NEXT_PUBLIC_OMR_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const MAX_SIZE = 10 * 1024 * 1024;
const ALLOWED = ['.pdf', '.png', '.jpg', '.jpeg', '.xml', '.musicxml', '.mxl'];

function safeFilename(name: string): string {
  return name.replace(/[^a-zA-Z0-9._-]/g, '_').slice(0, 80);
}

export default function ScoreV3() {
  const [file, setFile] = useState<File | null>(null);
  const [semitones, setSemitones] = useState(0);
  const [format, setFormat] = useState<'zip' | 'pdf'>('zip');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [elapsed, setElapsed] = useState<number | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || busy) return;
    setError('');
    setElapsed(null);
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
    if (!ALLOWED.includes(ext)) { setError('지원하지 않는 파일 형식입니다.'); return; }
    if (file.size > MAX_SIZE) { setError('파일 크기는 10MB 이하여야 합니다.'); return; }
    setBusy(true);
    const start = performance.now();
    try {
      const form = new FormData();
      form.append('file', file, file.name);
      form.append('semitones', String(semitones));
      // Do not abort at 30 seconds: this is a performance goal, not a deadline.
      const response = await fetch(`${API}/api/v3/score/transpose.${format}`, { method: 'POST', body: form });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(typeof body?.detail === 'string' ? body.detail : `서버 오류 (${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `${safeFilename(file.name.replace(/\.[^.]+$/, ''))}-transposed.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
      setElapsed((performance.now() - start) / 1000);
    } catch (e) {
      setError(e instanceof Error ? e.message : '악보 변환에 실패했습니다.');
    } finally {
      setBusy(false);
    }
  }

  return <>
    <Head><title>악보 전체 조옮김 실험실 | Capomatic</title></Head>
    <main style={{ maxWidth: 680, margin: '3rem auto', padding: '0 1.5rem', fontFamily: 'system-ui, sans-serif', lineHeight: 1.7 }}>
      <Link href="/">← Capomatic 돌아가기</Link>
      <h1>악보 전체 조옮김 (V3 실험실)</h1>
      <p>멜로디와 코드가 포함된 악보를 인식하고 조옮김된 PDF와 MusicXML을 생성합니다. 현재 실험 기능으로 결과를 반드시 확인해 주세요.</p>
      <form onSubmit={submit} style={{ display: 'grid', gap: 18 }}>
        <label>악보 파일 (PDF는 현재 1페이지만 지원)
          <input style={{ display: 'block', width: '100%' }} type="file" accept=".pdf,.png,.jpg,.jpeg,.xml,.musicxml,.mxl" required
            onChange={e => setFile(e.target.files?.[0] || null)} disabled={busy} />
        </label>
        <label>조옮김 (반음 단위): {semitones > 0 ? '+' : ''}{semitones}
          <input style={{ display: 'block', width: '100%' }} type="range" min={-11} max={11} step={1} value={semitones}
            onChange={e => setSemitones(Number(e.target.value))} disabled={busy} />
        </label>
        <label>결과물
          <select style={{ display: 'block', padding: 8 }} value={format} onChange={e => setFormat(e.target.value as 'zip' | 'pdf')} disabled={busy}>
            <option value="zip">ZIP (PDF + MusicXML + 처리 보고서)</option>
            <option value="pdf">PDF만 다운로드</option>
          </select>
        </label>
        <button type="submit" disabled={busy || !file} style={{ padding: 14, cursor: busy ? 'wait' : 'pointer' }}>
          {busy ? '변환 중입니다. 복잡한 악보는 30초 이상 걸릴 수 있습니다…' : '악보 변환 및 다운로드'}
        </button>
      </form>
      {elapsed !== null && <p role="status">완료: {elapsed.toFixed(1)}초. 출력된 악보의 음표와 코드를 확인하세요.</p>}
      {error && <p role="alert" style={{ color: 'crimson' }}>{error}</p>}
      <p style={{ fontSize: 13, opacity: .75 }}>현재 정확도 99% 및 처리시간 30초는 검증된 성능이 아니라 개발 목표입니다.</p>
    </main>
  </>;
}
