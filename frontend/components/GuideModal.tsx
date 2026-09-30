import { useEffect, useRef, useState } from "react";
import { useLang } from "@/components/LangProvider";
import { GUIDE_STEP_COUNT, guideMedia } from "@/lib/guide-visibility.mjs";

type Device = "mobile" | "desktop";
const MOBILE_QUERY = "(max-width: 640px)";

interface GuideModalProps {
  step: number;
  onStepChange: (step: number) => void;
  /** Skip, backdrop, Esc and Done: nothing is stored. */
  onClose: () => void;
  /** "Don't show again": the caller stores the flag, then closes. */
  onDismissForever: () => void;
}

/**
 * How-to guide: one short looping demo video per step, recorded by
 * scripts/record-guide.mjs. Only the current step's video is mounted, so
 * nothing is downloaded until the guide is open.
 */
export function GuideModal({ step, onStepChange, onClose, onDismissForever }: GuideModalProps) {
  const { t, lang } = useLang();
  const dialogRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  // Decided once, when the guide opens (this component mounts on open).
  const [device] = useState<Device>(() => (window.matchMedia(MOBILE_QUERY).matches ? "mobile" : "desktop"));
  const [reduceMotion] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [playing, setPlaying] = useState(!reduceMotion);

  const info = t.guideSteps[step];
  const media = guideMedia(device, lang, step);
  const isLast = step === GUIDE_STEP_COUNT - 1;

  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null;
    // Start on "Next", never on "Don't show again", so Enter can't dismiss by accident.
    dialogRef.current?.querySelector<HTMLButtonElement>(".guide-next")?.focus();
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") onCloseRef.current(); };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previousFocus?.focus();
    };
  }, []);

  // A new step starts paused again under reduced motion.
  useEffect(() => { setPlaying(!reduceMotion); }, [step, reduceMotion]);

  const trapFocus = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Tab") return;
    const buttons = dialogRef.current?.querySelectorAll<HTMLButtonElement>("button");
    if (!buttons?.length) return;
    const first = buttons[0];
    const last = buttons[buttons.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  };

  const playVideo = () => {
    setPlaying(true);
    void videoRef.current?.play().catch(() => setPlaying(false));
  };

  return (
    <div className="guide-backdrop" onClick={onClose}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="guide-title"
        className={`guide-dialog guide-${device}`}
        onKeyDown={trapFocus}
        onClick={e => e.stopPropagation()}
      >
        <div className="guide-media">
          <video
            key={media.webm}
            ref={videoRef}
            muted
            playsInline
            loop
            autoPlay={!reduceMotion}
            preload="none"
            poster={media.poster}
            aria-label={device === "mobile" ? info.videoMobile : info.videoDesktop}
          >
            <source src={media.webm} type="video/webm" />
            <source src={media.mp4} type="video/mp4" />
          </video>
          {!playing && (
            <button type="button" className="guide-play" onClick={playVideo} aria-label={t.playGuideVideo}>
              <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true"><path d="M7 4.5v13l11-6.5z" fill="currentColor" /></svg>
            </button>
          )}
        </div>
        <div className="guide-body">
          <p className="guide-count">{t.guideStepOf(step + 1, GUIDE_STEP_COUNT)}</p>
          <h2 id="guide-title" className="guide-title">{info.title}</h2>
          <p className="guide-desc">{info.desc}</p>
          <div className="guide-dots" aria-hidden="true">
            {Array.from({ length: GUIDE_STEP_COUNT }, (_, i) => (
              <span key={i} className={i === step ? "on" : undefined} />
            ))}
          </div>
          <button type="button" className="guide-dismiss" onClick={onDismissForever}>{t.dontShowAgain}</button>
          <div className="guide-actions">
            <button type="button" className="guide-skip" onClick={onClose}>{t.skip}</button>
            <button type="button" className="guide-next" onClick={() => (isLast ? onClose() : onStepChange(step + 1))}>
              {isLast ? t.done : t.next}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
