/**
 * Experimental V3 page: whole-score recognition and transposition.
 * Hidden unless NEXT_PUBLIC_ENABLE_SCORE_V3=1; the API also needs login.
 */
import { useState, type CSSProperties, type FormEvent } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useAuth } from '@/components/AuthProvider';
import { useLang, LangToggle } from '@/components/LangProvider';
import { Wordmark } from '@/components/Wordmark';
import { getAccessToken } from '@/lib/auth0';
import {
  CAPO_MAX, KEY_SHIFT_LIMIT, SCORE_EXTENSIONS,
  scoreDownloadName, scoreFileProblem, shiftFields,
} from '@/lib/score-v3.mjs';

const ENABLED = process.env.NEXT_PUBLIC_ENABLE_SCORE_V3 === '1';
const API = process.env.NEXT_PUBLIC_OMR_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const TEXT = {
  ko: {
    title: '악보 전체 조옮김 (실험)',
    intro: '멜로디·코드 악보를 인식해 음표와 코드를 함께 옮긴 PDF와 MusicXML을 만듭니다. 실험 기능이므로 결과를 꼭 확인해 주세요.',
    disabled: '이 기능은 아직 공개되지 않았습니다.',
    loginNeeded: '악보 전체 변환은 로그인 후 사용할 수 있습니다.',
    login: '로그인',
    file: '악보 파일 (PDF는 1페이지, 이미지, MusicXML)',
    modeKey: '조옮김 (음표+코드)',
    modeCapo: '카포 (코드만, 음표 그대로)',
    keyValue: (n: number) => `반음 ${n > 0 ? '+' : ''}${n}`,
    capoValue: (n: number) => `카포 ${n}`,
    format: '받을 파일',
    zip: 'ZIP (PDF + MusicXML + 보고서)',
    pdf: 'PDF만',
    submit: '변환하기',
    busy: '변환 중… 한 페이지에 1분 정도 걸릴 수 있습니다.',
    done: (s: number, w: string | null) => `완료 (${s.toFixed(1)}초). ${w && w !== '0' ? `검토가 필요한 마디 경고 ${w}건 — ` : ''}음표와 코드를 꼭 확인하세요.`,
    badType: '지원하지 않는 파일 형식입니다.',
    badSize: '파일은 10MB 이하여야 합니다.',
    failed: (status: number) => `변환에 실패했습니다 (${status}).`,
    tooMany: '요청이 많습니다. 잠시 후 다시 시도해 주세요.',
    note: '정확도 99%와 페이지당 30초는 개발 목표이며 아직 검증된 성능이 아닙니다.',
    back: '← 돌아가기',
  },
  en: {
    title: 'Whole-score transposition (experimental)',
    intro: 'Recognises a lead sheet and moves notes and chords together, returning a PDF and MusicXML. Experimental: always check the result.',
    disabled: 'This feature is not available yet.',
    loginNeeded: 'Please log in to convert whole scores.',
    login: 'Log in',
    file: 'Score file (1-page PDF, image or MusicXML)',
    modeKey: 'Key change (notes + chords)',
    modeCapo: 'Capo (chords only, notes unchanged)',
    keyValue: (n: number) => `${n > 0 ? '+' : ''}${n} semitones`,
    capoValue: (n: number) => `Capo ${n}`,
    format: 'Download',
    zip: 'ZIP (PDF + MusicXML + report)',
    pdf: 'PDF only',
    submit: 'Convert',
    busy: 'Converting… about a minute per page.',
    done: (s: number, w: string | null) => `Done in ${s.toFixed(1)} s. ${w && w !== '0' ? `${w} bar warning(s) to review — ` : ''}check notes and chords before use.`,
    badType: 'Unsupported file type.',
    badSize: 'Files must be 10 MB or smaller.',
    failed: (status: number) => `Conversion failed (${status}).`,
    tooMany: 'Too many requests. Please try again later.',
    note: '99% accuracy and 30 s per page are development targets, not verified performance.',
    back: '← Back',
  },
};

export default function ScoreV3() {
  const { lang } = useLang();
  const t = TEXT[lang];
  const { isAuthenticated, isLoading, login } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<'key' | 'capo'>('key');
  const [value, setValue] = useState(0);
  const [format, setFormat] = useState<'zip' | 'pdf'>('zip');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || busy) return;
    setError('');
    setStatus('');
    const problem = scoreFileProblem(file.name, file.size);
    if (problem) { setError(problem === 'type' ? t.badType : t.badSize); return; }
    const fields = shiftFields(mode, value);
    setBusy(true);
    const start = performance.now();
    try {
      const token = await getAccessToken();
      const form = new FormData();
      form.append('file', file, file.name);
      form.append('semitones', String(fields.semitones));
      form.append('mode', fields.mode);
      // No client-side deadline: 30 s is a goal, not a cutoff.
      const response = await fetch(`${API}/api/v3/score/transpose.${format}`, {
        method: 'POST',
        body: form,
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        const detail = typeof body?.detail === 'string' ? body.detail : '';
        throw new Error(response.status === 429 ? t.tooMany : `${t.failed(response.status)} ${detail}`.trim());
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = scoreDownloadName(file.name, fields, format);
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
      setStatus(t.done((performance.now() - start) / 1000, response.headers.get('X-OMR-Review-Warnings')));
    } catch (e) {
      setError(e instanceof Error ? e.message : t.failed(0));
    } finally {
      setBusy(false);
    }
  }

  const card: CSSProperties = { background: 'rgba(255,255,255,0.7)', borderRadius: 16, padding: 20, border: '1px solid rgba(0,0,0,0.06)' };

  return (
    <>
      <Head><title>{t.title} - Capomatic</title><meta name="robots" content="noindex" /></Head>
      <div style={{ minHeight: '100vh', backgroundColor: '#F5EDD8', fontFamily: "'Inter', 'Segoe UI', Arial, sans-serif" }}>
        <nav style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderBottom: '1px solid rgba(0,0,0,0.07)' }}>
          <Link href="/" aria-label="Capomatic"><Wordmark height={22} /></Link>
          <LangToggle />
        </nav>
        <main style={{ maxWidth: 640, margin: '0 auto', padding: '24px 16px 48px', display: 'grid', gap: 16, color: '#1a1a2e' }}>
          <Link href="/" style={{ color: '#7f3000', fontSize: '0.85rem' }}>{t.back}</Link>
          <h1 style={{ margin: 0, fontSize: '1.3rem' }}>{t.title}</h1>
          {!ENABLED ? (
            <p style={card}>{t.disabled}</p>
          ) : isLoading ? null : !isAuthenticated ? (
            <div style={card}>
              <p style={{ marginTop: 0 }}>{t.loginNeeded}</p>
              <button type="button" onClick={() => login('/score-v3')} style={{ background: '#a34200', color: 'white', border: 0, borderRadius: 50, padding: '10px 22px', fontWeight: 700, cursor: 'pointer' }}>{t.login}</button>
            </div>
          ) : (
            <form onSubmit={submit} style={{ ...card, display: 'grid', gap: 16 }}>
              <p style={{ margin: 0, fontSize: '0.9rem', color: '#444' }}>{t.intro}</p>
              <label style={{ display: 'grid', gap: 6, fontWeight: 600 }}>{t.file}
                <input type="file" accept={SCORE_EXTENSIONS.join(',')} required disabled={busy}
                  onChange={e => setFile(e.target.files?.[0] || null)} />
              </label>
              <fieldset style={{ border: 0, padding: 0, margin: 0, display: 'grid', gap: 6 }} disabled={busy}>
                <label><input type="radio" name="mode" checked={mode === 'key'} onChange={() => { setMode('key'); setValue(0); }} /> {t.modeKey}</label>
                <label><input type="radio" name="mode" checked={mode === 'capo'} onChange={() => { setMode('capo'); setValue(0); }} /> {t.modeCapo}</label>
              </fieldset>
              <label style={{ display: 'grid', gap: 6, fontWeight: 600 }}>
                {mode === 'capo' ? t.capoValue(value) : t.keyValue(value)}
                <input type="range" disabled={busy} value={value} step={1}
                  min={mode === 'capo' ? 0 : -KEY_SHIFT_LIMIT} max={mode === 'capo' ? CAPO_MAX : KEY_SHIFT_LIMIT}
                  onChange={e => setValue(Number(e.target.value))} />
              </label>
              <label style={{ display: 'grid', gap: 6, fontWeight: 600 }}>{t.format}
                <select value={format} disabled={busy} onChange={e => setFormat(e.target.value as 'zip' | 'pdf')} style={{ padding: 8 }}>
                  <option value="zip">{t.zip}</option>
                  <option value="pdf">{t.pdf}</option>
                </select>
              </label>
              <button type="submit" disabled={busy || !file} style={{ background: busy ? '#999' : '#a34200', color: 'white', border: 0, borderRadius: 50, padding: '12px 22px', fontWeight: 700, cursor: busy ? 'wait' : 'pointer' }}>
                {busy ? t.busy : t.submit}
              </button>
              {status && <p role="status" style={{ margin: 0 }}>{status}</p>}
              {error && <p role="alert" style={{ margin: 0, color: '#b00020' }}>{error}</p>}
            </form>
          )}
          <p style={{ fontSize: '0.75rem', color: '#666', margin: 0 }}>{t.note}</p>
        </main>
      </div>
    </>
  );
}
