/**
 * Admin dashboard — user management.
 */
import { useEffect, useState } from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import { useLang, LangToggle } from '@/components/LangProvider';
import { getAllUsers, AdminUser } from '@/lib/admin-api';
import Link from 'next/link';
import Head from 'next/head';

function DashboardContent() {
  const { t } = useLang();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      setUsers(await getAllUsers());
    } catch (err: any) {
      setError(err.message || t.failedLoad);
    } finally {
      setLoading(false);
    }
  }

  const thBase: React.CSSProperties = { padding: '10px 16px', textAlign: 'left', fontSize: '0.7rem', color: '#aaa', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', borderBottom: '1px solid rgba(0,0,0,0.06)', background: 'rgba(0,0,0,0.02)' };
  const tdBase: React.CSSProperties = { padding: '12px 16px', fontSize: '0.82rem', borderBottom: '1px solid rgba(0,0,0,0.04)', color: '#444' };

  return (
    <>
      <Head><title>{t.adminDashboard} - Capomatic</title><link rel="icon" href="/favicon.svg" type="image/svg+xml" /></Head>

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
                Capo<span style={{ color: '#e05d00' }}>matic</span>
              </span>
            </Link>
            <span className="admin-title-sep" style={{ color: 'rgba(0,0,0,0.15)' }}>|</span>
            <h1 className="admin-title" style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#1a1a2e' }}>{t.adminDashboard}</h1>
            <style>{`@media (max-width: 540px) { .admin-title, .admin-title-sep { display: none; } }`}</style>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <LangToggle />
            <span style={{ padding: '3px 12px', background: 'rgba(212,24,61,0.1)', color: '#d4183d', fontSize: '0.7rem', fontWeight: 800, borderRadius: 20, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              ADMIN
            </span>
          </div>
        </nav>

        <main style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 20px' }}>

          {loading && (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '64px 0' }}>
              <div style={{ width: 40, height: 40, border: '3px solid rgba(0,0,0,0.08)', borderTop: '3px solid #e05d00', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
            </div>
          )}

          {error && !loading && (
            <div style={{ background: 'white', borderRadius: 16, padding: 32, maxWidth: 360, margin: '64px auto', textAlign: 'center', boxShadow: '0 4px 24px rgba(0,0,0,0.10)' }}>
              <p style={{ color: '#d4183d', marginBottom: 20, fontSize: '0.88rem' }}>{error}</p>
              <button onClick={loadData} style={{ background: 'linear-gradient(135deg, #e05d00, #c84b00)', color: 'white', border: 'none', borderRadius: 10, padding: '10px 24px', fontWeight: 700, cursor: 'pointer', fontSize: '0.85rem' }}>
                {t.retry}
              </button>
            </div>
          )}

          {!loading && !error && (
            <div style={{ background: 'white', borderRadius: 16, overflow: 'hidden', boxShadow: '0 2px 12px rgba(0,0,0,0.06)', border: '1px solid rgba(0,0,0,0.04)' }}>
              <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(0,0,0,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#1a1a2e' }}>{t.allUsers}</h2>
                <span style={{ fontSize: '0.8rem', color: '#aaa', fontWeight: 600 }}>{users.length}</span>
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
