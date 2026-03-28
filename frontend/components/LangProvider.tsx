import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Lang, translations, T } from '@/lib/i18n';

interface LangContextValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: T;
}

const LangContext = createContext<LangContextValue | null>(null);

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>('ko'); // Korean default

  // Hydrate from localStorage after mount
  useEffect(() => {
    const stored = localStorage.getItem('tc-lang') as Lang | null;
    if (stored === 'ko' || stored === 'en') setLangState(stored);
  }, []);

  const setLang = (l: Lang) => {
    setLangState(l);
    localStorage.setItem('tc-lang', l);
  };

  return (
    <LangContext.Provider value={{ lang, setLang, t: translations[lang] }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLang(): LangContextValue {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error('useLang must be used inside LangProvider');
  return ctx;
}

/** Small KO/EN toggle button for use in navbars */
export function LangToggle() {
  const { lang, setLang } = useLang();
  return (
    <div style={{ display: 'flex', alignItems: 'center', background: 'rgba(0,0,0,0.07)', borderRadius: 20, padding: '2px 3px', gap: 2 }}>
      {(['ko', 'en'] as Lang[]).map(l => (
        <button
          key={l}
          onClick={() => setLang(l)}
          style={{
            padding: '3px 10px', borderRadius: 16, border: 'none', cursor: 'pointer',
            fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.04em',
            background: lang === l ? '#1a1a2e' : 'transparent',
            color: lang === l ? 'white' : '#888',
            transition: 'all 0.18s',
          }}
        >
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
