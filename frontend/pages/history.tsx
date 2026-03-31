/**
 * User job history page.
 * Shows all processed chord sheets with download/delete actions.
 */
import { useEffect, useState } from 'react';
import { useAuth } from '@/components/AuthProvider';
import { useLang, LangToggle } from '@/components/LangProvider';
import ProtectedRoute from '@/components/ProtectedRoute';
import { getMyJobs, downloadJobResult, deleteJob, Job } from '@/lib/api';
import Link from 'next/link';
import Head from 'next/head';

function HistoryContent() {
  const { user } = useAuth();
  const { t } = useLang();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { loadJobs(); }, []);

  async function loadJobs() {
    try {
      setLoading(true);
      setError(null);
      setJobs(await getMyJobs());
    } catch (err: any) {
      setError(err.message || t.failedLoad);
    } finally {
      setLoading(false);
    }
  }

  async function handleDownload(job: Job) {
    try {
      const blob = await downloadJobResult(job.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${job.song_name || 'capomatic'}_${job.semitones}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(t.downloadFailed(err.message));
    }
  }

  async function handleDelete(job: Job) {
    if (!confirm(t.deleteConfirm(job.song_name || t.untitled))) return;
    try {
      await deleteJob(job.id);
      setJobs(jobs.filter(j => j.id !== job.id));
    } catch (err: any) {
      alert(t.deleteFailed(err.message));
    }
  }

  const totalJobs = jobs.length;
  const completedJobs = jobs.filter(j => j.status === 'completed').length;
  const failedJobs = jobs.filter(j => j.status === 'failed').length;

  return (
    <>
      <Head><title>{t.historyTitle} - Capomatic</title><link rel="icon" href="/favicon.svg" type="image/svg+xml" /></Head>

      <div style={{ minHeight: '100vh', backgroundColor: '#F5EDD8', fontFamily: "'Inter', 'Segoe UI', Arial, sans-serif", overflowX: 'hidden' }}>

        <nav className="history-nav">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0, flex: 1 }}>
            <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 6, textDecoration: 'none', flexShrink: 0 }}>
              <svg viewBox="0 0 36 36" width="24" height="24">
                <circle cx="18" cy="18" r="17" fill="#1a1a2e" />
                <rect x="11" y="12" width="14" height="2.5" rx="1.2" fill="#e05d00" />
                <rect x="11" y="16" width="14" height="2.5" rx="1.2" fill="#e05d00" opacity="0.7" />
                <rect x="11" y="20" width="14" height="2.5" rx="1.2" fill="#e05d00" opacity="0.4" />
                <rect x="21" y="10" width="3" height="16" rx="1.5" fill="white" opacity="0.9" />
              </svg>
              <span style={{ fontWeight: 800, fontSize: '0.9rem', color: '#1a1a2e', fontFamily: 'Georgia, serif', fontStyle: 'italic', whiteSpace: 'nowrap' }}>
                Capo<span style={{ color: '#e05d00' }}>matic</span>
              </span>
            </Link>
            <span style={{ color: 'rgba(0,0,0,0.15)', flexShrink: 0 }}>|</span>
            <h1 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#1a1a2e', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.historyTitle}</h1>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
            <LangToggle />
            <span className="history-username" style={{ fontSize: '0.8rem', color: '#888', fontWeight: 500 }}>{user?.name || user?.email}</span>
          </div>
        </nav>

        <main className="history-main">

          {loading && (
            <div style={{ textAlign: 'center', padding: '64px 0' }}>
              <div style={{ width: 40, height: 40, border: '3px solid rgba(0,0,0,0.08)', borderTop: '3px solid #e05d00', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto' }} />
              <p style={{ marginTop: 16, color: '#aaa', fontSize: '0.85rem' }}>{t.loading}</p>
            </div>
          )}

          {error && !loading && (
            <div style={{ textAlign: 'center', padding: '64px 0' }}>
              <p style={{ color: '#d4183d', marginBottom: 16, fontSize: '0.9rem' }}>{error}</p>
              <button onClick={loadJobs} style={{ background: 'linear-gradient(135deg, #e05d00, #c84b00)', color: 'white', border: 'none', borderRadius: 10, padding: '10px 24px', fontWeight: 700, cursor: 'pointer', fontSize: '0.85rem' }}>
                {t.retry}
              </button>
            </div>
          )}

          {!loading && !error && (
            <>
              {/* Stats */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, marginBottom: 28 }}>
                {[
                  { label: t.totalJobs, value: totalJobs, color: '#1a1a2e' },
                  { label: t.completed, value: completedJobs, color: '#28c45e' },
                  { label: t.failed, value: failedJobs, color: '#d4183d' },
                ].map(({ label, value, color }) => (
                  <div key={label} style={{ background: 'rgba(255,255,255,0.6)', borderRadius: 14, padding: '20px 20px', border: '1px solid rgba(255,255,255,0.85)', backdropFilter: 'blur(8px)', boxShadow: '0 2px 12px rgba(0,0,0,0.05)' }}>
                    <p style={{ margin: 0, fontSize: '0.72rem', color: '#aaa', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</p>
                    <p style={{ margin: '6px 0 0', fontSize: '2rem', fontWeight: 800, color }}>{value}</p>
                  </div>
                ))}
              </div>

              {jobs.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '64px 20px', background: 'rgba(255,255,255,0.55)', borderRadius: 16, border: '2px dashed rgba(0,0,0,0.08)' }}>
                  <div style={{ fontSize: '2.5rem', marginBottom: 12 }}>🎵</div>
                  <p style={{ color: '#aaa', marginBottom: 20, fontSize: '0.9rem' }}>{t.noJobs}</p>
                  <Link href="/" style={{ display: 'inline-block', background: 'linear-gradient(135deg, #e05d00, #c84b00)', color: 'white', textDecoration: 'none', borderRadius: 50, padding: '11px 26px', fontWeight: 700, fontSize: '0.85rem', boxShadow: '0 4px 14px rgba(224,93,0,0.28)' }}>
                    {t.processFirst}
                  </Link>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {jobs.map(job => (
                    <div key={job.id} className="history-job-card">
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#1a1a2e' }}>
                          {job.song_name || t.untitled}
                        </h3>
                        <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, fontSize: '0.78rem', color: '#888' }}>
                          {job.original_key && job.target_key && (
                            <span style={{ fontWeight: 700, color: '#1a1a2e' }}>{job.original_key} → {job.target_key}</span>
                          )}
                          <span>({t.semitones(job.semitones)})</span>
                          <span style={{ color: 'rgba(0,0,0,0.15)' }}>·</span>
                          <span>{job.mode}</span>
                          <span style={{ color: 'rgba(0,0,0,0.15)' }}>·</span>
                          <span style={{ fontWeight: 700, color: job.status === 'completed' ? '#28c45e' : job.status === 'failed' ? '#d4183d' : '#e05d00' }}>
                            {job.status === 'completed' ? t.completed : job.status === 'failed' ? t.failed : job.status}
                          </span>
                        </div>
                        <div style={{ marginTop: 4, fontSize: '0.7rem', color: '#ccc' }}>
                          {new Date(job.created_at).toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </div>
                      <div className="history-job-actions">
                        {job.status === 'completed' && (
                          <button onClick={() => handleDownload(job)} style={{ background: 'linear-gradient(135deg, #e05d00, #c84b00)', color: 'white', border: 'none', borderRadius: 9, padding: '8px 16px', fontSize: '0.78rem', fontWeight: 700, cursor: 'pointer', boxShadow: '0 2px 8px rgba(224,93,0,0.22)' }}>
                            {t.download}
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(job)}
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
            </>
          )}
        </main>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }

        .history-nav {
          position: sticky; top: 0; z-index: 100;
          display: flex; align-items: center; justify-content: space-between;
          padding: 0 16px; height: 52px;
          background: rgba(245, 237, 216, 0.95);
          backdrop-filter: blur(12px);
          border-bottom: 1px solid rgba(0,0,0,0.07);
          overflow: hidden;
        }
        @media (min-width: 640px) {
          .history-nav { padding: 0 24px; }
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
  return (
    <ProtectedRoute>
      <HistoryContent />
    </ProtectedRoute>
  );
}
