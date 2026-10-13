import { useEffect, useMemo, useRef, type RefObject } from 'react';
import { useLang } from '@/components/LangProvider';
import { createSupportQr } from '@/lib/support-qr.mjs';

interface SupportModalProps {
  url: string;
  onClose: () => void;
  triggerRef: RefObject<HTMLButtonElement>;
}

export default function SupportModal({ url, onClose, triggerRef }: SupportModalProps) {
  const { t } = useLang();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const qr = useMemo(() => createSupportQr(url), [url]);

  useEffect(() => {
    const trigger = triggerRef.current;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCloseRef.current();
    };
    const phone = window.matchMedia('(max-width: 640px)');
    const onResize = () => { if (phone.matches) onCloseRef.current(); };
    document.addEventListener('keydown', onKeyDown);
    phone.addEventListener('change', onResize);
    // The lazy chunk can land after the window already crossed to phone width.
    onResize();
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      phone.removeEventListener('change', onResize);
      trigger?.focus();
    };
  }, [triggerRef]);

  const trapFocus = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'Tab') return;
    const items = dialogRef.current?.querySelectorAll<HTMLElement>('button, a[href]');
    if (!items?.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return (
    <div className="support-backdrop" onClick={onClose}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="support-title"
        aria-describedby="support-help"
        className="support-dialog"
        onClick={event => event.stopPropagation()}
        onKeyDown={trapFocus}
      >
        <h2 id="support-title">{t.support}</h2>
        <svg className="support-qr" viewBox={`0 0 ${qr.size} ${qr.size}`} width="200" height="200" role="img" aria-label={t.supportQrLabel} shapeRendering="crispEdges">
          <rect width={qr.size} height={qr.size} fill="#fff" />
          <path d={qr.path} fill="#000" />
        </svg>
        <p id="support-help">{t.supportQrHelp}</p>
        <a href={url} target="_blank" rel="noopener noreferrer" aria-label={t.supportOpenHereAria} className="support-device-link">
          {t.supportOpenHere}
        </a>
        <button ref={closeRef} type="button" onClick={onClose} className="support-close">{t.supportClose}</button>
      </div>
    </div>
  );
}
