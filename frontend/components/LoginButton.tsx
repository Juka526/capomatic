/**
 * User icon button — circular avatar/icon in nav.
 * Unauthenticated: dark circle with user silhouette, clicks to login.
 * Authenticated: avatar or initials, dropdown with logout.
 */
'use client';

import { useState, useRef, useEffect } from 'react';
import { UserRound } from 'lucide-react';
import { useAuth } from './AuthProvider';
import { useLang } from './LangProvider';

export default function LoginButton() {
  const { user, isAuthenticated, isLoading, login, logout } = useAuth();
  const { t } = useLang();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  if (isLoading) {
    return <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#e0dcd0' }} />;
  }

  if (!isAuthenticated) {
    return (
      <button
        onClick={() => void login()}
        style={{
          width: 32, height: 32, borderRadius: '50%',
          background: '#1a1a2e', border: 'none', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: 0,
        }}
        title={t.login}
        aria-label={t.login}
      >
        <UserRound size={16} color="white" strokeWidth={2} />
      </button>
    );
  }

  const initial = (user?.name || user?.email || '?')[0].toUpperCase();

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(!open)}
        aria-label={user?.name || user?.email || t.login}
        aria-expanded={open}
        aria-haspopup="menu"
        style={{
          width: 32, height: 32, borderRadius: '50%',
          border: 'none', cursor: 'pointer', padding: 0,
          overflow: 'hidden',
          background: user?.picture ? 'transparent' : '#e05d00',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}
      >
        {user?.picture ? (
          <img src={user.picture} alt="" style={{ width: 32, height: 32, borderRadius: '50%', objectFit: 'cover' }} />
        ) : (
          <span style={{ color: 'white', fontSize: '0.82rem', fontWeight: 800 }}>{initial}</span>
        )}
      </button>

      {open && (
        <div className="user-dropdown" role="menu">
          <div style={{ padding: '10px 16px 8px', borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
            <p style={{ margin: 0, fontSize: '0.82rem', fontWeight: 700, color: '#1a1a2e' }}>{user?.name || t.login}</p>
            {user?.email && (
              <p style={{ margin: '2px 0 0', fontSize: '0.72rem', color: '#999' }}>{user.email}</p>
            )}
          </div>
          <button
            onClick={() => { setOpen(false); logout(); }}
            role="menuitem"
            style={{
              display: 'block', width: '100%', textAlign: 'left',
              background: 'none', border: 'none', cursor: 'pointer',
              padding: '10px 16px', fontSize: '0.82rem', fontWeight: 600,
              color: '#d4183d',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(212,24,61,0.04)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'none')}
          >
            {t.logout}
          </button>
        </div>
      )}
    </div>
  );
}
