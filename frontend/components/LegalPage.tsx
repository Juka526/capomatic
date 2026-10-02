import Head from 'next/head';
import Link from 'next/link';
import { useLang, LangToggle } from '@/components/LangProvider';
import { Wordmark } from '@/components/Wordmark';

type Section = { heading: string; paragraphs: string[] };

interface LegalPageProps {
  title: { ko: string; en: string };
  sections: { ko: Section[]; en: Section[] };
}

export default function LegalPage({ title, sections }: LegalPageProps) {
  const { lang } = useLang();
  const activeTitle = title[lang];
  return (
    <>
      <Head>
        <title>{activeTitle} - Capomatic</title>
        <meta name="robots" content="index,follow" />
      </Head>
      <div style={{ minHeight: '100vh', background: '#F5EDD8', color: '#252525' }}>
        <nav style={{ height: 52, padding: '0 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(0,0,0,0.07)' }}>
          <Link href="/" style={{ display: 'flex', textDecoration: 'none' }}><Wordmark height={22} /></Link>
          <LangToggle />
        </nav>
        <main style={{ maxWidth: 760, margin: '0 auto', padding: '40px 20px 64px', lineHeight: 1.7 }}>
          <h1 style={{ margin: '0 0 8px', fontSize: 'clamp(1.8rem, 6vw, 2.6rem)' }}>{activeTitle}</h1>
          <p style={{ margin: '0 0 36px', color: '#665e54', fontSize: '0.85rem' }}>2026-09-16</p>
          {sections[lang].map((section) => (
            <section key={section.heading} style={{ marginBottom: 28 }}>
              <h2 style={{ fontSize: '1.08rem', marginBottom: 8 }}>{section.heading}</h2>
              {section.paragraphs.map((paragraph) => (
                <p key={paragraph} style={{ margin: '8px 0', fontSize: '0.94rem' }}>{paragraph}</p>
              ))}
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
          <p style={{ marginTop: 40 }}>
            <Link href="/" style={{ color: '#b44a00', fontWeight: 700 }}>← Capomatic</Link>
          </p>
        </main>
      </div>
    </>
  );
}
