import { useCallback, useEffect, useRef, useState } from "react";
import { useLang } from "@/components/LangProvider";
import { GUIDE_STEP_COUNT, guideMedia } from "@/lib/guide-visibility.mjs";
import { type Chapter, chapterAt, nextChapterStart, parseChapters, previousChapterStart } from "@/lib/guide-chapters.mjs";

type Device = "mobile" | "desktop";
const MOBILE_QUERY = "(max-width: 640px)";

interface GuideModalProps {
  /** Skip, backdrop, Esc and Done: nothing is stored. */
  onClose: () => void;
  /** "Don't show again": the caller stores the flag, then closes. */
  onDismissForever: () => void;
}

/**
 * How-to guide: one continuous demo video (recorded by scripts/record-guide.mjs)
 * whose step text follows the scene being played. Back/Next and the dots jump
 * the video to a scene. The video only exists while the guide is open, so
 * nothing is downloaded before that.
 */
export function GuideModal({ onClose, onDismissForever }: GuideModalProps) {
  const { t, lang } = useLang();
  const dialogRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const seekRef = useRef<HTMLInputElement>(null);
  // Decided once, when the guide opens (this component mounts on open).
  const [device] = useState<Device>(() => (window.matchMedia(MOBILE_QUERY).matches ? "mobile" : "desktop"));
  const [reduceMotion] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [playing, setPlaying] = useState(false);
  const [step, setStep] = useState(0);
  const chaptersRef = useRef<Chapter[]>([]);
  const pendingSeekRef = useRef<number | null>(null);

  const media = guideMedia(device, lang);
  const info = t.guideSteps[step];
  const isLast = step === GUIDE_STEP_COUNT - 1;

  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  // Text and seek bar follow the video. Without chapter data the buttons still page through the text.
  const sync = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    const time = pendingSeekRef.current ?? video.currentTime;
    if (chaptersRef.current.length) setStep(chapterAt(time, chaptersRef.current));
    const seek = seekRef.current;
    if (seek && Number.isFinite(video.duration)) {
      seek.max = String(video.duration);
      seek.value = String(time);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    chaptersRef.current = [];
    fetch(media.chapters)
      .then(res => (res.ok ? res.json() : null))
      .then(data => {
        if (cancelled) return;
        chaptersRef.current = parseChapters(data);
        sync();
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [media.chapters, sync]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    // A frame callback switches the text on the frame the scene starts; timeupdate (~4 Hz) is the fallback.
    const frameSync = typeof video.requestVideoFrameCallback === "function";
    let handle = 0;
    const onFrame = () => { sync(); handle = video.requestVideoFrameCallback(onFrame); };
    if (frameSync) handle = video.requestVideoFrameCallback(onFrame);
    const onMetadata = () => {
      if (pendingSeekRef.current != null) {
        video.currentTime = pendingSeekRef.current;
        pendingSeekRef.current = null;
      }
      sync();
    };
    const onPlay = () => setPlaying(true);
    const onPause = () => setPlaying(false);
    video.addEventListener("loadedmetadata", onMetadata);
    video.addEventListener("seeked", sync);
    video.addEventListener("play", onPlay);
    video.addEventListener("pause", onPause);
    if (!frameSync) video.addEventListener("timeupdate", sync);
    return () => {
      if (frameSync) video.cancelVideoFrameCallback(handle);
      video.removeEventListener("loadedmetadata", onMetadata);
      video.removeEventListener("seeked", sync);
      video.removeEventListener("play", onPlay);
      video.removeEventListener("pause", onPause);
      video.removeEventListener("timeupdate", sync);
    };
  }, [media.mp4, sync]);

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

  /** Jump the video (keeping play/pause as it is); before metadata, apply once it arrives. */
  const seekTo = (time: number) => {
    const video = videoRef.current;
    if (!video) return;
    setStep(chapterAt(time, chaptersRef.current));
    if (video.readyState >= HTMLMediaElement.HAVE_METADATA) {
      video.currentTime = time;
    } else {
      pendingSeekRef.current = time;
      video.preload = "metadata"; // preload="none" would otherwise never fetch it
    }
  };

  const currentTime = () => pendingSeekRef.current ?? videoRef.current?.currentTime ?? 0;

  const goToStep = (index: number) => {
    const chapter = chaptersRef.current[index];
    if (chapter) seekTo(chapter.start);
    else setStep(index);
  };

  const goNext = () => {
    if (isLast) { onClose(); return; }
    const start = chaptersRef.current.length ? nextChapterStart(currentTime(), chaptersRef.current) : null;
    if (start != null) seekTo(start); else setStep(step + 1);
  };

  const goPrevious = () => {
    const start = chaptersRef.current.length ? previousChapterStart(currentTime(), chaptersRef.current) : null;
    if (start != null) seekTo(start); else setStep(Math.max(0, step - 1));
  };

  const togglePlay = () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) void video.play().catch(() => setPlaying(false));
    else video.pause();
  };

  const trapFocus = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Tab") return;
    const items = dialogRef.current?.querySelectorAll<HTMLElement>("button:not(:disabled), input");
    if (!items?.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
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
            key={media.mp4}
            ref={videoRef}
            muted
            playsInline
            loop
            autoPlay={!reduceMotion}
            preload="none"
            poster={media.poster}
            aria-label={device === "mobile" ? t.guideVideoMobile : t.guideVideoDesktop}
          >
            <source src={media.mp4} type="video/mp4" />
          </video>
          {!playing && (
            <button type="button" className="guide-play" onClick={togglePlay} aria-label={t.playGuideVideo}>
              <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true"><path d="M7 4.5v13l11-6.5z" fill="currentColor" /></svg>
            </button>
          )}
        </div>
        <div className="guide-controls">
          <button type="button" className="guide-toggle" onClick={togglePlay} aria-label={playing ? t.pauseGuideVideo : t.playGuideVideo}>
            {playing ? (
              <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5h2.6v11H4zM9.4 2.5H12v11H9.4z" fill="currentColor" /></svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M4.5 2.5v11l9-5.5z" fill="currentColor" /></svg>
            )}
          </button>
          <input
            ref={seekRef}
            className="guide-seek"
            type="range"
            min={0}
            max={1}
            step="any"
            defaultValue={0}
            aria-label={t.guideSeek}
            onInput={e => seekTo(Number(e.currentTarget.value))}
          />
        </div>
        <div className="guide-body">
          {/* Re-read only when the scene changes: React re-renders this text only then. */}
          <div className="guide-text" aria-live="polite" aria-atomic="true">
            <p className="guide-count">{t.guideStepOf(step + 1, GUIDE_STEP_COUNT)}</p>
            <h2 id="guide-title" className="guide-title">{info.title}</h2>
            <p className="guide-desc">{info.desc}</p>
          </div>
          <div className="guide-dots">
            {Array.from({ length: GUIDE_STEP_COUNT }, (_, i) => (
              <button
                key={i}
                type="button"
                className={i === step ? "on" : undefined}
                aria-label={t.guideGoToStep(i + 1)}
                aria-current={i === step ? "step" : undefined}
                onClick={() => goToStep(i)}
              >
                <span aria-hidden="true" />
              </button>
            ))}
          </div>
          <button type="button" className="guide-dismiss" onClick={onDismissForever}>{t.dontShowAgain}</button>
          <div className="guide-actions">
            <button type="button" className="guide-skip" onClick={onClose}>{t.skip}</button>
            <button type="button" className="guide-prev" onClick={goPrevious} disabled={step === 0}>{t.previous}</button>
            <button type="button" className="guide-next" onClick={goNext}>{isLast ? t.done : t.next}</button>
          </div>
        </div>
      </div>
    </div>
  );
}
