/**
 * Admin dashboard page.
 * Shows statistics, popular songs, and user management.
 */
import { useEffect, useState } from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import { useLang, LangToggle } from '@/components/LangProvider';
import {
  getAdminStats,
  getPopularSongs,
  getAllUsers,
  AdminStats,
  PopularSong,
  AdminUser,
} from '@/lib/admin-api';
import Link from 'next/link';
import Head from 'next/head';

const COLOR_MAP: Record<string, string> = {
  blue: '#1a1a2e',
  green: '#28c45e',
  purple: '#7c3aed',
  orange: '#e05d00',
  pink: '#d4183d',
};

function StatCard({ title, value, color = 'blue' }: { title: string; value: string | number; color?: string }) {
  return (
    <div style={{ background: 'rgba(255,255,255,0.6)', borderRadius: 14, padding: '20px 20px', border: '1px solid rgba(255,255,255,0.85)', backdropFilter: 'blur(8px)', boxShadow: '0 2px 12px rgba(0,0,0,0.05)' }}>
      <p style={{ margin: 0, fontSize: '0.72rem', color: '#aaa', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{title}</p>
      <p style={{ margin: '6px 0 0', fontSize: '1.9rem', fontWeight: 800, color: COLOR_MAP[color] ?? color }}>{value}</p>
    </div>
  );
}

function DashboardContent() {
  const { t } = useLang();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [popular, setPopular] = useState<PopularSong[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'popular' | 'users'>('overview');

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      const [statsData, popularData, usersData] = await Promise.all([
        getAdminStats(), getPopularSongs(20), getAllUsers(),
      ]);
      setStats(statsData);
      setPopular(popularData);
      setUsers(usersData);
    } catch (err: any) {
      setError(err.message || t.failedLoad);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: '#F5EDD8', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'Inter', 'Segoe UI', Arial, sans-serif" }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ width: 40, height: 40, border: '3px solid rgba(0,0,0,0.08)', borderTop: '3px solid #e05d00', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto' }} />
          <p style={{ marginTop: 16, color: '#aaa', fontSize: '0.85rem' }}>{t.loadingDashboard}</p>
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: '#F5EDD8', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'Inter', 'Segoe UI', Arial, sans-serif" }}>
        <div style={{ background: 'white', borderRadius: 16, padding: 32, maxWidth: 360, textAlign: 'center', boxShadow: '0 4px 24px rgba(0,0,0,0.10)' }}>
          <h2 style={{ margin: '0 0 8px', color: '#1a1a2e' }}>Error</h2>
          <p style={{ color: '#d4183d', marginBottom: 20, fontSize: '0.88rem' }}>{error}</p>
          <button onClick={loadData} style={{ background: 'linear-gradient(135deg, #e05d00, #c84b00)', color: 'white', border: 'none', borderRadius: 10, padding: '10px 24px', fontWeight: 700, cursor: 'pointer', fontSize: '0.85rem' }}>
            {t.retry}
          </button>
        </div>
      </div>
    );
  }

  const tabs = [
    { key: 'overview' as const, label: t.overview },
    { key: 'popular' as const, label: t.popularSongs },
    { key: 'users' as const, label: t.users },
  ];

  const thBase: React.CSSProperties = { padding: '10px 16px', textAlign: 'left', fontSize: '0.7rem', color: '#aaa', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', borderBottom: '1px solid rgba(0,0,0,0.06)', background: 'rgba(0,0,0,0.02)' };
  const tdBase: React.CSSProperties = { padding: '12px 16px', fontSize: '0.82rem', borderBottom: '1px solid rgba(0,0,0,0.04)', color: '#444' };

  return (
    <>
      <Head><title>{t.adminDashboard} - TransChord</title></Head>

      <div style={{ minHeight: '100vh', backgroundColor: '#F5EDD8', fontFamily: "'Inter', 'Segoe UI', Arial, sans-serif" }}>

        <nav style={{
          position: 'sticky', top: 0, zIndex: 100,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 24px', height: 52,
          background: 'rgba(245, 237, 216, 0.95)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid rgba(0,0,0,0.07)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}>
              <svg viewBox="0 0 36 36" width="24" height="24">
                <circle cx="18" cy="18" r="17" fill="#1a1a2e" />
                <rect x="11" y="12" width="14" height="2.5" rx="1.2" fill="#e05d00" />
                <rect x="11" y="16" width="14" height="2.5" rx="1.2" fill="#e05d00" opacity="0.7" />
                <rect x="11" y="20" width="14" height="2.5" rx="1.2" fill="#e05d00" opacity="0.4" />
                <rect x="21" y="10" width="3" height="16" rx="1.5" fill="white" opacity="0.9" />
              </svg>
              <span style={{ fontWeight: 800, fontSize: '0.9rem', color: '#1a1a2e', fontFamily: 'Georgia, serif', fontStyle: 'italic' }}>
                Trans<span style={{ color: '#e05d00' }}>Chord</span>
              </span>
            </Link>
            <span style={{ color: 'rgba(0,0,0,0.15)' }}>|</span>
            <h1 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#1a1a2e' }}>{t.adminDashboard}</h1>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <LangToggle />
            <span style={{ padding: '3px 12px', background: 'rgba(212,24,61,0.1)', color: '#d4183d', fontSize: '0.7rem', fontWeight: 800, borderRadius: 20, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              ADMIN
            </span>
          </div>
        </nav>

        <main style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 20px' }}>

          {/* Tabs */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 28 }}>
            {tabs.map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                style={{
                  padding: '8px 20px', borderRadius: 10, border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: '0.82rem',
                  background: activeTab === tab.key ? '#1a1a2e' : 'rgba(255,255,255,0.6)',
                  color: activeTab === tab.key ? 'white' : '#666',
                  boxShadow: activeTab === tab.key ? '0 2px 10px rgba(26,26,46,0.2)' : 'none',
                  transition: 'all 0.18s',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Overview */}
          {activeTab === 'overview' && stats && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12 }}>
                <StatCard title={t.totalUsers} value={stats.total_users} color="blue" />
                <StatCard title={t.totalJobsStat} value={stats.total_jobs} color="green" />
                <StatCard title={t.cachedItems} value={stats.total_cached} color="purple" />
                <StatCard title={t.cacheHitRate} value={`${stats.cache_hit_rate.toFixed(1)}%`} color="orange" />
                <StatCard title={t.avgTime} value={`${Math.round(stats.avg_processing_time)}ms`} color="pink" />
              </div>
              <div style={{ background: 'white', borderRadius: 16, overflow: 'hidden', boxShadow: '0 2px 12px rgba(0,0,0,0.06)', border: '1px solid rgba(0,0,0,0.04)' }}>
                <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(0,0,0,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h2 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#1a1a2e' }}>{t.top5Songs}</h2>
                  <button onClick={() => setActiveTab('popular')} style={{ background: 'none', border: 'none', color: '#e05d00', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 700 }}>{t.viewAll}</button>
                </div>
                <div style={{ overflowX: 'auto' }}>
                  {popular.length === 0 ? (
                    <p style={{ padding: '32px', textAlign: 'center', color: '#ccc', fontSize: '0.85rem' }}>{t.noSongs}</p>
                  ) : (
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr>{[t.rank, t.song, t.semitonesCol, t.requests].map(h => <th key={h} style={thBase}>{h}</th>)}</tr>
                      </thead>
                      <tbody>
                        {popular.slice(0, 5).map((song, idx) => (
                          <tr key={idx} onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,0,0,0.02)')} onMouseLeave={e => (e.currentTarget.style.background = '')}>
                            <td style={{ ...tdBase, fontWeight: 800, color: '#1a1a2e', width: 40 }}>{idx + 1}</td>
                            <td style={{ ...tdBase, fontWeight: 600 }}>{song.song_name}</td>
                            <td style={tdBase}>{song.original_key} → {song.target_key}</td>
                            <td style={{ ...tdBase, fontWeight: 800, color: '#e05d00' }}>{song.request_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Popular Songs */}
          {activeTab === 'popular' && (
            <div style={{ background: 'white', borderRadius: 16, overflow: 'hidden', boxShadow: '0 2px 12px rgba(0,0,0,0.06)', border: '1px solid rgba(0,0,0,0.04)' }}>
              <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
                <h2 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#1a1a2e' }}>{t.popularRanking}</h2>
              </div>
              {popular.length === 0 ? (
                <p style={{ padding: '48px', textAlign: 'center', color: '#ccc', fontSize: '0.85rem' }}>{t.noSongs}</p>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        {[t.rank, t.song, t.original, t.target, t.semitonesCol, t.requests, t.uniqueUsers, t.lastRequested].map((h, i) => (
                          <th key={i} style={{ ...thBase, textAlign: (i === 5 || i === 6) ? 'right' : 'left' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {popular.map((song, idx) => (
                        <tr key={idx} onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,0,0,0.02)')} onMouseLeave={e => (e.currentTarget.style.background = '')}>
                          <td style={{ ...tdBase, fontWeight: 800, color: '#1a1a2e', width: 40 }}>{idx + 1}</td>
                          <td style={{ ...tdBase, fontWeight: 600 }}>{song.song_name}</td>
                          <td style={tdBase}>{song.original_key || '—'}</td>
                          <td style={tdBase}>{song.target_key || '—'}</td>
                          <td style={{ ...tdBase, textAlign: 'center' }}>
                            <span style={{ padding: '2px 8px', borderRadius: 6, fontSize: '0.75rem', fontWeight: 700, background: song.semitones < 0 ? 'rgba(212,24,61,0.08)' : song.semitones > 0 ? 'rgba(40,196,94,0.1)' : 'rgba(0,0,0,0.05)', color: song.semitones < 0 ? '#d4183d' : song.semitones > 0 ? '#1a9e50' : '#888' }}>
                              {song.semitones > 0 ? '+' : ''}{song.semitones}
                            </span>
                          </td>
                          <td style={{ ...tdBase, textAlign: 'right', fontWeight: 800, color: '#e05d00' }}>{song.request_count}</td>
                          <td style={{ ...tdBase, textAlign: 'right' }}>{song.unique_users}</td>
                          <td style={{ ...tdBase, color: '#bbb', fontSize: '0.75rem' }}>
                            {new Date(song.last_requested).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Users */}
          {activeTab === 'users' && (
            <div style={{ background: 'white', borderRadius: 16, overflow: 'hidden', boxShadow: '0 2px 12px rgba(0,0,0,0.06)', border: '1px solid rgba(0,0,0,0.04)' }}>
              <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
                <h2 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#1a1a2e' }}>{t.allUsers}</h2>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>{[t.email, t.name, t.role, t.created, t.lastLogin].map(h => <th key={h} style={thBase}>{h}</th>)}</tr>
                  </thead>
                  <tbody>
                    {users.map(u => (
                      <tr key={u.id} onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,0,0,0.02)')} onMouseLeave={e => (e.currentTarget.style.background = '')}>
                        <td style={{ ...tdBase, fontWeight: 600, color: '#1a1a2e' }}>{u.email}</td>
                        <td style={tdBase}>{u.name || '—'}</td>
                        <td style={tdBase}>
                          <span style={{ padding: '3px 10px', borderRadius: 20, fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', background: u.role === 'admin' ? 'rgba(212,24,61,0.1)' : 'rgba(0,0,0,0.06)', color: u.role === 'admin' ? '#d4183d' : '#888' }}>
                            {u.role}
                          </span>
                        </td>
                        <td style={{ ...tdBase, color: '#bbb', fontSize: '0.75rem' }}>
                          {new Date(u.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                        </td>
                        <td style={{ ...tdBase, color: '#bbb', fontSize: '0.75rem' }}>
                          {u.last_login ? new Date(u.last_login).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : t.never}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </main>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </>
  );
}

export default function AdminDashboard() {
  return (
    <ProtectedRoute requireAdmin>
      <DashboardContent />
    </ProtectedRoute>
  );
}
