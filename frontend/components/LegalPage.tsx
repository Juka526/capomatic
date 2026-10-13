import Head from 'next/head';
import Link from 'next/link';
import { useLang, LangToggle } from '@/components/LangProvider';
import { Wordmark } from '@/components/Wordmark';
import { LEGAL_CONTACT_EMAIL } from '@/lib/legal-contact';

// A table's first row is its header.
export type Block = string | { list: string[] } | { table: string[][] } | { href: string; text: string };
export type Section = { heading: string; paragraphs: Block[] };

interface LegalPageProps {
  title: { ko: string; en: string };
  sections: { ko: Section[]; en: Section[] };
  updated?: string;
  toc?: boolean;
}

const textStyle = { margin: '8px 0', fontSize: '0.94rem' };
const cellStyle = { padding: '6px 8px', border: '1px solid rgba(0,0,0,0.12)', textAlign: 'left' as const, verticalAlign: 'top' as const };

function renderBlock(block: Block, key: number) {
  if (typeof block === 'string') return <p key={key} style={textStyle}>{block}</p>;
  if ('list' in block) {
    return <ul key={key} style={{ ...textStyle, paddingLeft: 22 }}>{block.list.map((item, i) => <li key={i}>{item}</li>)}</ul>;
  }
  if ('table' in block) {
    const [head, ...rows] = block.table;
    return (
      <div key={key} style={{ overflowX: 'auto', margin: '12px 0' }}>
        <table style={{ borderCollapse: 'collapse', fontSize: '0.85rem', lineHeight: 1.5, minWidth: '100%' }}>
          <thead><tr>{head.map((cell, i) => <th key={i} style={{ ...cellStyle, background: 'rgba(0,0,0,0.04)' }}>{cell}</th>)}</tr></thead>
          <tbody>{rows.map((row, r) => <tr key={r}>{row.map((cell, i) => <td key={i} style={cellStyle}>{cell}</td>)}</tr>)}</tbody>
        </table>
      </div>
    );
  }
  return <p key={key} style={textStyle}><Link href={block.href} style={{ color: '#b44a00' }}>{block.text}</Link></p>;
}

export default function LegalPage({ title, sections, updated = '2026-09-16', toc = false }: LegalPageProps) {
  const { lang } = useLang();
  const activeTitle = title[lang];
  return (
    <>
      <Head>
        <title>{activeTitle} - Capomatic</title>
        <meta name="robots" content="index,follow" />
      </Head>
      <div className="with-bars" style={{ minHeight: '100vh', background: '#F5EDD8', color: '#252525' }}>
        <nav className="fixed-top" style={{ zIndex: 100, height: 'calc(52px + env(safe-area-inset-top, 0px))', padding: 'env(safe-area-inset-top, 0px) 20px 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#F5EDD8', borderBottom: '1px solid rgba(0,0,0,0.07)' }}>
          <Link href="/" style={{ display: 'flex', textDecoration: 'none' }}><Wordmark height={22} /></Link>
          <LangToggle />
        </nav>
        <main style={{ maxWidth: 760, margin: '0 auto', padding: '40px 20px 64px', lineHeight: 1.7 }}>
          <h1 style={{ margin: '0 0 8px', fontSize: 'clamp(1.8rem, 6vw, 2.6rem)' }}>{activeTitle}</h1>
          <p style={{ margin: '0 0 36px', color: '#665e54', fontSize: '0.85rem' }}>{updated}</p>
          {toc && (
            <nav aria-label={lang === 'ko' ? '목차' : 'Contents'} style={{ marginBottom: 36 }}>
              <h2 style={{ fontSize: '1.08rem', marginBottom: 8 }}>{lang === 'ko' ? '목차' : 'Contents'}</h2>
              <ol style={{ ...textStyle, paddingLeft: 22 }}>
                {sections[lang].map((section, i) => (
                  <li key={section.heading}><a href={`#s-${i + 1}`} style={{ color: '#252525' }}>{section.heading}</a></li>
                ))}
              </ol>
            </nav>
          )}
          {sections[lang].map((section, i) => (
            <section key={section.heading} id={`s-${i + 1}`} style={{ marginBottom: 28, scrollMarginTop: 72 }}>
              <h2 style={{ fontSize: '1.08rem', marginBottom: 8 }}>{section.heading}</h2>
              {section.paragraphs.map(renderBlock)}
            </section>
          ))}
          <p style={{ marginTop: 32, fontSize: '0.9rem' }}>
            <a
              href="https://github.com/Juka526/capomatic/issues"
              target="_blank"
              rel="noreferrer"
              style={{ color: '#665e54' }}
            >
              GitHub Issues
            </a>
          </p>
          {LEGAL_CONTACT_EMAIL && (
            <p style={{ fontSize: '0.9rem' }}>
              <a href={`mailto:${LEGAL_CONTACT_EMAIL}`} style={{ color: '#665e54' }}>{LEGAL_CONTACT_EMAIL}</a>
            </p>
          )}
          <p style={{ marginTop: 40 }}>
            <Link href="/" style={{ color: '#b44a00', fontWeight: 700 }}>← Capomatic</Link>
          </p>
        </main>
      </div>
    </>
  );
}
