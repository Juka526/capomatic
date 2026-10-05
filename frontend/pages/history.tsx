/**
 * User history page — reads from localStorage (tc-history key).
 */
import { useEffect, useState } from 'react';
import { useAuth } from '@/components/AuthProvider';
import { useLang, LangToggle } from '@/components/LangProvider';
import { Wordmark } from '@/components/Wordmark';
import Link from 'next/link';
import Head from 'next/head';
import { parseJobHistory, type JobHistoryEntry } from '@/lib/job-history.mjs';

function HistoryContent() {
  const { user } = useAuth();
  const { t } = useLang();
  const [entries, setEntries] = useState<JobHistoryEntry[]>([]);

  useEffect(() => {
    try {
      setEntries(parseJobHistory(localStorage.getItem('tc-history')));
    } catch {
      setEntries([]);
    }
  }, []);

  function handleDelete(id: string) {
    const updated = entries.filter(e => e.id !== id);
    setEntries(updated);
    localStorage.setItem('tc-history', JSON.stringify(updated));
  }

  return (
    <>
      <Head><title>{t.historyTitle} - Capomatic</title><link rel="icon" href="/favicon.svg" type="image/svg+xml" /></Head>

      <div className="with-bars" style={{ minHeight: '100vh', backgroundColor: '#F5EDD8', fontFamily: "'Inter', 'Segoe UI', Arial, sans-serif", overflowX: 'hidden' }}>

        <nav className="history-nav fixed-top">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0, flex: 1 }}>
            <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 6, textDecoration: 'none', flexShrink: 0 }}>
              <Wordmark height={22} />
            </Link>
            <span style={{ color: 'rgba(0,0,0,0.15)', flexShrink: 0 }}>|</span>
            <h1 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#1a1a2e', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.historyTitle}</h1>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
            <LangToggle />
            <span className="history-username" style={{ fontSize: '0.8rem', color: '#595959', fontWeight: 500 }}>{user?.name || user?.email}</span>
          </div>
        </nav>

        <main className="history-main">
          {entries.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '64px 20px', background: 'rgba(255,255,255,0.55)', borderRadius: 16, border: '2px dashed rgba(0,0,0,0.08)' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: 12 }}>🎵</div>
              <p style={{ color: '#686868', marginBottom: 20, fontSize: '0.9rem' }}>{t.noJobs}</p>
              <Link href="/" style={{ display: 'inline-block', background: 'linear-gradient(135deg, #a34200, #7f3000)', color: 'white', textDecoration: 'none', borderRadius: 50, padding: '11px 26px', fontWeight: 700, fontSize: '0.85rem', boxShadow: '0 4px 14px rgba(163,66,0,0.28)' }}>
                {t.processFirst}
              </Link>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {entries.map(entry => (
                <div key={entry.id} className="history-job-card">
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#1a1a2e' }}>
                      {entry.song_name || t.untitled}
                    </h3>
                    <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, fontSize: '0.78rem', color: '#595959' }}>
                      {entry.original_key && entry.target_key && (
                        <span style={{ fontWeight: 700, color: '#1a1a2e' }}>{entry.original_key} → {entry.target_key}</span>
                      )}
                      <span>({t.semitones(entry.semitones)})</span>
                    </div>
                    <div style={{ marginTop: 4, fontSize: '0.7rem', color: '#ccc' }}>
                      {new Date(entry.timestamp).toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                  <div className="history-job-actions">
                    <button
                      onClick={() => handleDelete(entry.id)}
                      style={{ background: 'none', border: 'none', color: '#d4183d', padding: '8px 10px', borderRadius: 9, cursor: 'pointer', fontSize: '0.78rem', fontWeight: 600 }}
                      onMouseEnter={e => (e.currentTarget.style.background = 'rgba(212,24,61,0.06)')}
                      onMouseLeave={e => (e.currentTarget.style.background = 'none')}
                    >
                      {t.delete}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>

      <style>{`
        .history-nav {
          z-index: 100;
          display: flex; align-items: center; justify-content: space-between;
          padding: env(safe-area-inset-top, 0px) 16px 0; height: calc(52px + env(safe-area-inset-top, 0px));
          background: rgba(245, 237, 216, 0.95);
          backdrop-filter: blur(12px);
          border-bottom: 1px solid rgba(0,0,0,0.07);
          overflow: hidden;
        }
        @media (min-width: 640px) {
          .history-nav { padding-left: 24px; padding-right: 24px; }
        }

        .history-username {
          display: none;
        }
        @media (min-width: 640px) {
          .history-username {
            display: inline;
            max-width: 180px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
        }

        .history-main {
          max-width: 960px; margin: 0 auto; padding: 20px 14px;
        }
        @media (min-width: 640px) {
          .history-main { padding: 32px 20px; }
        }

        .history-job-card {
          background: white; border-radius: 14px; padding: 14px 16px;
          box-shadow: 0 2px 12px rgba(0,0,0,0.06);
          border: 1px solid rgba(0,0,0,0.04);
          display: flex; flex-direction: column; gap: 10px;
        }
        @media (min-width: 540px) {
          .history-job-card {
            flex-direction: row; align-items: flex-start;
            justify-content: space-between; gap: 16px;
            padding: 16px 20px;
          }
        }

        .history-job-actions {
          display: flex; align-items: center; gap: 8px;
        }
      `}</style>
    </>
  );
}

export default function HistoryPage() {
  return <HistoryContent />;
}
