import { useEffect, useRef, useState } from "react";
import { useLang } from "@/components/LangProvider";

interface GuideModalProps {
  onClose: () => void;
  onDismissForever: () => void;
}

const STEP_ICONS = ["𝄞", "⊫", "♪"];

export function GuideModal({ onClose, onDismissForever }: GuideModalProps) {
  const { t } = useLang();
  const dialogRef = useRef<HTMLDivElement>(null);
  const [step, setStep] = useState(0);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const info = t.guideSteps[step];
  const isLast = step === t.guideSteps.length - 1;

  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null;
    dialogRef.current?.querySelector<HTMLButtonElement>(".guide-next")?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCloseRef.current();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previousFocus?.focus();
    };
  }, []);

  const trapFocus = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Tab") return;
    const items = dialogRef.current?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)");
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
    <div className="guide-backdrop" onClick={onClose}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="guide-title"
        aria-describedby="guide-description"
        className="guide-dialog"
        onKeyDown={trapFocus}
        onClick={e => e.stopPropagation()}
      >
        <div className="guide-icon" aria-hidden="true">{STEP_ICONS[step]}</div>
        <div className="guide-text" aria-live="polite" aria-atomic="true">
          <p className="guide-count">{t.guideStepOf(step + 1, t.guideSteps.length)}</p>
          <h2 id="guide-title" className="guide-title">{info.title}</h2>
          <p id="guide-description" className="guide-desc">{info.desc}</p>
        </div>
        <div className="guide-dots">
          {t.guideSteps.map((_, index) => (
            <button
              key={index}
              type="button"
              className={index === step ? "on" : undefined}
              aria-label={t.guideGoToStep(index + 1)}
              aria-current={index === step ? "step" : undefined}
              onClick={() => setStep(index)}
            >
              <span aria-hidden="true" />
            </button>
          ))}
        </div>
        <div className="guide-actions">
          <button type="button" className="guide-prev" onClick={() => setStep(step - 1)} disabled={step === 0}>{t.previous}</button>
          <button type="button" className="guide-next" onClick={() => { if (isLast) onClose(); else setStep(step + 1); }}>{isLast ? t.done : t.next}</button>
        </div>
        <div className="guide-secondary">
          <button type="button" className="guide-dismiss" onClick={onDismissForever}>{t.dontShowAgain}</button>
          <button type="button" className="guide-skip" onClick={onClose}>{t.skip}</button>
        </div>
      </div>
    </div>
  );
}
