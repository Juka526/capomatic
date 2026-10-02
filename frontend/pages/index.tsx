import { useState, useRef, useCallback, useEffect, useMemo } from "react";
import { Upload, Download, Loader2, AlertCircle, ArrowRight } from "lucide-react";
import Head from "next/head";
import Link from "next/link";
import LoginButton from "@/components/LoginButton";
import { useLang, LangToggle } from "@/components/LangProvider";
import { GuitarFretboard } from "@/components/GuitarFretboard";
import { MobileWordmark } from "@/components/MobileWordmark";
import { translations } from "@/lib/i18n";
import { computeTargetKey } from "@/lib/target-key.mjs";
import { pngDownloadName } from "@/lib/download-name.mjs";
import { chooseSaveStrategy, dataUrlToBlob } from "@/lib/download-image.mjs";
import { prependJobHistory } from "@/lib/job-history.mjs";
import { SHIFT_LIMIT, mobileStepper, shiftSummary } from "@/lib/transpose-control.mjs";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const MAX_FILE_SIZE = 20 * 1024 * 1024;
const RENDER_CACHE_LIMIT = 5;
// Same breakpoint as styles/globals.css; everything mobile-only keys off it.
const MOBILE_QUERY = "(max-width: 640px)";
const DESKTOP_SHIFT_LIMIT = 7;

const prettyKey = (key: string | null) => (key ?? "").replace(/^([A-G])b/, "$1\u266D").replace("#", "\u266F");

type ChordStyle = { parenthesis?: "open" | "close" | "both" };
type ChordItem = { text: string; bbox: number[] | null; style?: ChordStyle | null };
type RenderMode = "replace" | "above" | "both";
type RenderResult = {
  replace_image: string | null;
  above_image: string | null;
  original_key: string | null;
  target_key: string | null;
  semitones: number;
};
const ESTIMATED_DETECT_MS = 60000;
type Row = { y1: number; y2: number; yCenter: number };

function userFacingApiError(
  status: number,
  messages: typeof translations.ko | typeof translations.en,
): string {
  if (status === 404) return messages.detectionExpired;
  if (status === 413) return messages.uploadTooLarge;
  if (status === 422) return messages.invalidUpload;
  if (status === 429) return messages.ocrBusy;
  return messages.failedConnect;
}

function detectRows(chords: ChordItem[]): Row[] {
  const valid = chords.filter(c => c.bbox !== null) as { text: string; bbox: number[] }[];
  if (valid.length === 0) return [];
  const sorted = [...valid].sort((a, b) =>
    (a.bbox[1] + a.bbox[3]) / 2 - (b.bbox[1] + b.bbox[3]) / 2
  );
  const groups: { y1: number; y2: number; ycs: number[] }[] = [];
  for (const c of sorted) {
    const yc = (c.bbox[1] + c.bbox[3]) / 2;
    const last = groups[groups.length - 1];
    if (last && yc - last.ycs[last.ycs.length - 1] < 50) {
      last.y1 = Math.min(last.y1, c.bbox[1]);
      last.y2 = Math.max(last.y2, c.bbox[3]);
      last.ycs.push(yc);
    } else {
      groups.push({ y1: c.bbox[1], y2: c.bbox[3], ycs: [yc] });
    }
  }
  return groups.map(g => ({
    y1: g.y1, y2: g.y2,
    yCenter: g.ycs.reduce((a, b) => a + b, 0) / g.ycs.length,
  }));
}

function nearestRow(rows: Row[], y: number): Row | null {
  if (rows.length === 0) return null;
  return rows.reduce((best, r) =>
    Math.abs(r.yCenter - y) < Math.abs(best.yCenter - y) ? r : best
  );
}

export default function Home() {
  const { t, lang } = useLang();

  const [file, setFile] = useState<File | null>(null);
  const [semitoneShift, setSemitoneShift] = useState<number>(0); // -7 to +7

  const [detectionId, setDetectionId] = useState<string | null>(null);
  const [songTitle, setSongTitle] = useState("알수없음");
  const [originalKey, setOriginalKey] = useState<string | null>(null);
  const [detecting, setDetecting] = useState(false);
  const [detectProgress, setDetectProgress] = useState(0);
  const [detectElapsed, setDetectElapsed] = useState(0);

  const [replaceResult, setReplaceResult] = useState<string | null>(null);
  const [aboveResult, setAboveResult] = useState<string | null>(null);
  // data: URL shown full-screen for long-press saving where downloads are blocked.
  // Not a blob: URL: in-app browsers (KakaoTalk) save long-pressed images outside
  // the page, where blob: URLs do not resolve (#31, verified on a device).
  const [saveOverlayUrl, setSaveOverlayUrl] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"replace" | "above">("replace");
  const [showOriginal, setShowOriginal] = useState(false);
  const [rendering, setRendering] = useState(false);
  const [renderUpdating, setRenderUpdating] = useState(false);

  const [detectedChords, setDetectedChords] = useState<ChordItem[]>([]);
  const [editableChords, setEditableChords] = useState<ChordItem[]>([]);
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  const [addingChord, setAddingChord] = useState(false);
  const [addInput, setAddInput] = useState("");
  const [reRendering, setReRendering] = useState(false);
  const [addModeActive, setAddModeActive] = useState(false);
  const [pendingPosition, setPendingPosition] = useState<{x: number, y1: number, y2: number} | null>(null);
  const [pendingChordText, setPendingChordText] = useState("");
  const [hoverImgPos, setHoverImgPos] = useState<{x: number, y: number} | null>(null);
  const [imgNaturalSize, setImgNaturalSize] = useState<{w: number, h: number} | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [guideOpen, setGuideOpen] = useState(false);
  const [guideStep, setGuideStep] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const guideDialogRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const mobileImgRef = useRef<HTMLImageElement>(null);
  // Only the mobile result board mounts its own GuitarFretboard: two fretboards
  // in the DOM would share SVG gradient ids.
  const [isMobile, setIsMobile] = useState(false);
  const renderCacheRef = useRef<Map<string, RenderResult>>(new Map());
  const inFlightRenderRef = useRef<Map<string, Promise<RenderResult>>>(new Map());
  const selectedSemitoneRef = useRef(0);
  const editVersionRef = useRef(0);

  const originalImageUrl = useMemo(() => (
    file ? URL.createObjectURL(file) : null
  ), [file]);

  useEffect(() => () => {
    if (originalImageUrl) URL.revokeObjectURL(originalImageUrl);
  }, [originalImageUrl]);

  useEffect(() => {
    const query = window.matchMedia(MOBILE_QUERY);
    const update = () => setIsMobile(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  // Close hamburger menu on outside click
  useEffect(() => {
    if (!menuOpen) return;
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [menuOpen]);

  useEffect(() => {
    if (!guideOpen) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    const firstButton = guideDialogRef.current?.querySelector<HTMLButtonElement>('button');
    firstButton?.focus();
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setGuideOpen(false);
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previousFocus?.focus();
    };
  }, [guideOpen]);

  const trapGuideFocus = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'Tab') return;
    const buttons = guideDialogRef.current?.querySelectorAll<HTMLButtonElement>('button');
    if (!buttons?.length) return;
    const first = buttons[0];
    const last = buttons[buttons.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const capoFret = semitoneShift < 0 ? Math.abs(semitoneShift) : null;
  const semitones = semitoneShift;

  const targetKey = useMemo(() => {
    if (!originalKey || semitones === 0) return originalKey;
    return computeTargetKey(originalKey, semitones);
  }, [originalKey, semitones]);

  const detectedRows = useMemo(() => detectRows(detectedChords), [detectedChords]);
  const snapRow = useMemo(() =>
    (addModeActive && hoverImgPos) ? nearestRow(detectedRows, hoverImgPos.y) : null,
    [addModeActive, hoverImgPos, detectedRows]
  );

  // Passive touchmove listener to allow preventDefault (suppresses scroll in add mode)
  useEffect(() => {
    const els = [imgRef.current, mobileImgRef.current].filter((el): el is HTMLImageElement => el !== null);
    if (els.length === 0) return;
    const handler = (e: TouchEvent) => { if (addModeActive) e.preventDefault(); };
    els.forEach(el => el.addEventListener("touchmove", handler, { passive: false }));
    return () => els.forEach(el => el.removeEventListener("touchmove", handler));
  }, [addModeActive]);

  useEffect(() => {
    if (!detecting) return;
    const start = Date.now();
    const id = setInterval(() => {
      const dt = Date.now() - start;
      setDetectElapsed(dt);
      setDetectProgress(Math.min(100, (dt / ESTIMATED_DETECT_MS) * 100));
    }, 200);
    return () => clearInterval(id);
  }, [detecting]);

  const runDetection = useCallback(async (f: File) => {
    setDetecting(true);
    renderCacheRef.current.clear();
    inFlightRenderRef.current.clear();
    editVersionRef.current += 1;
    selectedSemitoneRef.current = 0;
    setDetectProgress(0);
    setDetectElapsed(0);
    setError(null);
    setDetectionId(null);
    setSongTitle("알수없음");
    setOriginalKey(null);
    setReplaceResult(null);
    setAboveResult(null);
    setShowOriginal(false);
    setDetectedChords([]);
    setEditableChords([]);
    setEditingIdx(null);
    setAddModeActive(false);
    setPendingPosition(null);
    setPendingChordText("");
    setHoverImgPos(null);
    setImgNaturalSize(null);
    try {
      const formData = new FormData();
      formData.append("image", f);
      formData.append("ocr_engine", "paddle");
      const res = await fetch(`${API_URL}/detect`, { method: "POST", body: formData });
      if (!res.ok) throw new Error(userFacingApiError(res.status, t));
      const data = await res.json();
      setDetectProgress(100);
      setDetectionId(data.detection_id);
      setSongTitle(data.song_title || "알수없음");
      setOriginalKey(data.original_key);
      const chords: ChordItem[] = (data.chords || []).map((c: any) => ({ text: c.text, bbox: c.bbox, style: c.style }));
      setDetectedChords(chords);
      setEditableChords(chords);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedConnect);
    } finally {
      setDetecting(false);
    }
  }, [t]);

  const handleFile = useCallback((f: File) => {
    if (f.size > MAX_FILE_SIZE) { setError(t.fileTooLarge); return; }
    setFile(f);
    setError(null);
    setSemitoneShift(0);
    setRenderUpdating(false);
    runDetection(f);
  }, [runDetection, t]);

  // The desktop result card sits below the fold; on mobile the result is already on screen.
  const scrollResultIntoView = () => {
    if (window.matchMedia(MOBILE_QUERY).matches) return;
    setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 150);
  };

  const clearRenderCache = () => {
    renderCacheRef.current.clear();
    inFlightRenderRef.current.clear();
  };

  const renderCacheKey = (semi: number, version = editVersionRef.current) => (
    detectionId ? `${detectionId}:${version}:${semi}` : null
  );

  const storeRenderCache = (key: string, data: RenderResult) => {
    const cache = renderCacheRef.current;
    const previous = cache.get(key);
    const merged: RenderResult = {
      replace_image: data.replace_image ?? previous?.replace_image ?? null,
      above_image: data.above_image ?? previous?.above_image ?? null,
      original_key: data.original_key ?? previous?.original_key ?? null,
      target_key: data.target_key ?? previous?.target_key ?? null,
      semitones: data.semitones,
    };
    cache.delete(key);
    cache.set(key, merged);
    while (cache.size > RENDER_CACHE_LIMIT) {
      const oldest = cache.keys().next().value;
      if (!oldest) break;
      cache.delete(oldest);
    }
    return merged;
  };

  const renderHasMode = (data: RenderResult, mode: RenderMode) => (
    mode === "both"
      ? Boolean(data.replace_image && data.above_image)
      : mode === "replace"
        ? Boolean(data.replace_image)
        : Boolean(data.above_image)
  );

  const applyRenderResult = (data: RenderResult) => {
    setReplaceResult(data.replace_image);
    setAboveResult(data.above_image);
  };

  const fetchRenderResult = async (
    semi: number,
    mode: RenderMode = "both",
    chordsOverride?: ChordItem[],
  ): Promise<RenderResult | null> => {
    const key = renderCacheKey(semi);
    if (!key || !detectionId) return null;

    const cached = renderCacheRef.current.get(key);
    if (cached && renderHasMode(cached, mode) && !chordsOverride) {
      renderCacheRef.current.delete(key);
      renderCacheRef.current.set(key, cached);
      return cached;
    }

    const requestKey = `${key}:${mode}`;
    const existing = inFlightRenderRef.current.get(requestKey);
    if (existing && !chordsOverride) return existing;

    const request = (async () => {
      const formData = new FormData();
      formData.append("detection_id", detectionId);
      formData.append("semitones", semi.toString());
      formData.append("mode", mode);
      if (chordsOverride) {
        formData.append("chords_override", JSON.stringify(chordsOverride));
      }
      const res = await fetch(`${API_URL}/render`, { method: "POST", body: formData });
      if (!res.ok) throw new Error(userFacingApiError(res.status, t));
      const data = await res.json() as RenderResult;
      return storeRenderCache(key, data);
    })();

    if (!chordsOverride) inFlightRenderRef.current.set(requestKey, request);
    try {
      return await request;
    } finally {
      if (inFlightRenderRef.current.get(requestKey) === request) {
        inFlightRenderRef.current.delete(requestKey);
      }
    }
  };

  const prefetchRender = (semi: number, mode: RenderMode = activeTab) => {
    if (!detectionId || semi === 0 || detecting || reRendering) return;
    const key = renderCacheKey(semi);
    const cached = key ? renderCacheRef.current.get(key) : null;
    if (
      !key
      || (cached && renderHasMode(cached, mode))
      || inFlightRenderRef.current.has(`${key}:${mode}`)
    ) return;
    void fetchRenderResult(semi, mode).catch(() => {});
  };

  const prefetchAdjacentRenders = (centerSemi: number) => {
    [centerSemi - 1, centerSemi + 1]
      .filter(semi => semi >= -7 && semi <= 7 && semi !== 0)
      .forEach(semi => prefetchRender(semi));
  };

  const fetchBackgroundMode = (semi: number, mode: "replace" | "above", version: number) => {
    void fetchRenderResult(semi, mode)
      .then(data => {
        if (
          !data
          || selectedSemitoneRef.current !== semi
          || editVersionRef.current !== version
        ) return;
        if (mode === "replace") setReplaceResult(data.replace_image);
        if (mode === "above") setAboveResult(data.above_image);
      })
      .catch(() => {});
  };

  const fetchOtherModeInBackground = (
    semi: number,
    visibleMode: "replace" | "above",
    version: number,
  ) => {
    fetchBackgroundMode(semi, visibleMode === "replace" ? "above" : "replace", version);
  };

  const performRender = async (
    chordsOverride?: ChordItem[],
    semitoneOverride: number = semitones,
    scrollToResult: boolean = true,
  ) => {
    if (!detectionId) return;
    const versionAtStart = editVersionRef.current;
    const visibleMode = activeTab;
    setRendering(true);
    setRenderUpdating(false);
    setError(null);
    try {
      const data = await fetchRenderResult(semitoneOverride, visibleMode, chordsOverride);
      if (!data || versionAtStart !== editVersionRef.current) return;
      applyRenderResult(data);
      setShowOriginal(false);
      saveToLocalHistory(songTitle, originalKey, data.target_key, semitoneOverride);
      if (scrollToResult) {
        scrollResultIntoView();
      }
      fetchOtherModeInBackground(semitoneOverride, visibleMode, versionAtStart);
      setTimeout(() => prefetchAdjacentRenders(semitoneOverride), 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedConnect);
    } finally {
      setRendering(false);
    }
  };

  const saveToLocalHistory = (title: string, origKey: string | null, tgtKey: string | null, semi: number) => {
    try {
      const entry = {
        id: crypto.randomUUID(),
        song_name: title || "알수없음",
        original_key: origKey,
        target_key: tgtKey,
        semitones: semi,
        timestamp: new Date().toISOString(),
      };
      const updated = prependJobHistory(localStorage.getItem("tc-history"), entry);
      localStorage.setItem("tc-history", JSON.stringify(updated));
    } catch {}
  };

  const handleReRender = async () => {
    if (!detectionId) return;
    editVersionRef.current += 1;
    clearRenderCache();
    setReRendering(true);
    setError(null);
    try {
      const visibleMode = activeTab;
      const versionAtStart = editVersionRef.current;
      const data = await fetchRenderResult(semitones, visibleMode, editableChords);
      if (!data) return;
      applyRenderResult(data);
      setShowOriginal(false);
      fetchOtherModeInBackground(semitones, visibleMode, versionAtStart);
      setTimeout(() => prefetchAdjacentRenders(semitones), 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedConnect);
    } finally {
      setReRendering(false);
    }
  };

  const handleImageClick = (e: React.MouseEvent<HTMLImageElement>) => {
    if (showOriginal || !addModeActive || !imgNaturalSize) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = Math.round((e.clientX - rect.left) * (imgNaturalSize.w / rect.width));
    const y = Math.round((e.clientY - rect.top) * (imgNaturalSize.h / rect.height));
    const row = nearestRow(detectedRows, y);
    setPendingPosition({ x, y1: row?.y1 ?? y, y2: row?.y2 ?? (y + 35) });
    setAddModeActive(false);
    setHoverImgPos(null);
  };

  const handleImageMouseMove = (e: React.MouseEvent<HTMLImageElement>) => {
    if (showOriginal || !addModeActive || !imgNaturalSize) return;
    const rect = e.currentTarget.getBoundingClientRect();
    setHoverImgPos({
      x: Math.round((e.clientX - rect.left) * (imgNaturalSize.w / rect.width)),
      y: Math.round((e.clientY - rect.top)  * (imgNaturalSize.h / rect.height)),
    });
  };

  const handleImageMouseLeave = () => setHoverImgPos(null);

  const handleImageTouchMove = (e: React.TouchEvent<HTMLImageElement>) => {
    if (showOriginal || !addModeActive || !imgNaturalSize) return;
    const touch = e.touches[0];
    const rect = e.currentTarget.getBoundingClientRect();
    setHoverImgPos({
      x: Math.round((touch.clientX - rect.left) * (imgNaturalSize.w / rect.width)),
      y: Math.round((touch.clientY - rect.top)  * (imgNaturalSize.h / rect.height)),
    });
  };

  const handleImageTouchEnd = (e: React.TouchEvent<HTMLImageElement>) => {
    if (showOriginal || !addModeActive || !imgNaturalSize || !hoverImgPos) return;
    e.preventDefault();
    const row = nearestRow(detectedRows, hoverImgPos.y);
    setPendingPosition({ x: hoverImgPos.x, y1: row?.y1 ?? hoverImgPos.y, y2: row?.y2 ?? (hoverImgPos.y + 35) });
    setAddModeActive(false);
    setHoverImgPos(null);
  };

  const confirmPositionedChord = () => {
    if (!pendingPosition || !pendingChordText.trim() || !imgNaturalSize) return;
    const { x, y1, y2 } = pendingPosition;
    const boundedX1 = Math.max(0, Math.min(imgNaturalSize.w - 1, Math.round(x)));
    const boundedY1 = Math.max(0, Math.min(imgNaturalSize.h - 1, Math.round(y1)));
    const boundedX2 = Math.min(imgNaturalSize.w, boundedX1 + 80);
    const boundedY2 = Math.max(
      boundedY1 + 1,
      Math.min(imgNaturalSize.h, Math.round(y2)),
    );
    setEditableChords(prev => [...prev, {
      text: pendingChordText.trim(),
      bbox: [boundedX1, boundedY1, boundedX2, boundedY2],
    }]);
    setPendingPosition(null);
    setPendingChordText("");
  };

  const closeSaveOverlay = () => setSaveOverlayUrl(null);

  // Results are base64 data URIs; mobile browsers do not reliably download
  // those via <a download>, so save through a Blob (see #31).
  const handleDownload = () => {
    const activeResult = activeTab === "replace" ? replaceResult : aboveResult;
    if (showOriginal) return;
    if (!activeResult) return;
    const filename = pngDownloadName(activeTab, file?.name);
    // Decoded synchronously so navigator.share still has the tap's user activation.
    const blob = dataUrlToBlob(activeResult);
    const pngFile = new File([blob], filename, { type: "image/png" });
    const strategy = chooseSaveStrategy({
      userAgent: navigator.userAgent,
      maxTouchPoints: navigator.maxTouchPoints,
      canShareFiles: typeof navigator.canShare === "function" && navigator.canShare({ files: [pngFile] }),
    });

    if (strategy === "overlay") {
      setSaveOverlayUrl(activeResult);
      return;
    }
    if (strategy === "share") {
      navigator.share({ files: [pngFile], title: filename }).catch((err: unknown) => {
        // Cancelling the share sheet is not an error; anything else falls back to long-press saving.
        if (!(err instanceof DOMException && err.name === "AbortError")) setSaveOverlayUrl(activeResult);
      });
      return;
    }
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = filename;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
    // Some mobile browsers read the blob after click() returns.
    window.setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
  };

  const clearFile = () => {
    clearRenderCache();
    editVersionRef.current += 1;
    selectedSemitoneRef.current = 0;
    setFile(null);
    setDetectionId(null);
    setSongTitle("알수없음");
    setOriginalKey(null);
    setReplaceResult(null);
    setAboveResult(null);
    setShowOriginal(false);
    setError(null);
    setSemitoneShift(0);
    setRenderUpdating(false);
    setDetectedChords([]);
    setEditableChords([]);
    setEditingIdx(null);
    setAddingChord(false);
    setAddModeActive(false);
    setPendingPosition(null);
    setPendingChordText("");
    setHoverImgPos(null);
    setImgNaturalSize(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const applySemitoneShift = async (value: number, limit: number = DESKTOP_SHIFT_LIMIT) => {
    const next = Math.max(-limit, Math.min(limit, value));
    if (next === semitoneShift || reRendering || detecting) return;
    const versionAtStart = editVersionRef.current;
    const shouldScrollToResult = !(replaceResult || aboveResult);
    selectedSemitoneRef.current = next;
    setSemitoneShift(next);
    if (next !== 0) {
      const key = renderCacheKey(next, versionAtStart);
      const cached = key ? renderCacheRef.current.get(key) : null;
      const visibleMode = activeTab;
      if (key && cached && renderHasMode(cached, visibleMode)) {
        renderCacheRef.current.delete(key);
        renderCacheRef.current.set(key, cached);
        applyRenderResult(cached);
        setShowOriginal(false);
        setRenderUpdating(false);
        saveToLocalHistory(songTitle, originalKey, cached.target_key, next);
        if (shouldScrollToResult) {
          scrollResultIntoView();
        }
        fetchOtherModeInBackground(next, visibleMode, versionAtStart);
        setTimeout(() => prefetchAdjacentRenders(next), 0);
        return;
      }

      setRenderUpdating(true);
      setError(null);
      try {
        const data = await fetchRenderResult(next, visibleMode);
        if (
          data
          && selectedSemitoneRef.current === next
          && versionAtStart === editVersionRef.current
        ) {
          applyRenderResult(data);
          setShowOriginal(false);
          saveToLocalHistory(songTitle, originalKey, data.target_key, next);
          if (shouldScrollToResult) {
            scrollResultIntoView();
          }
          fetchOtherModeInBackground(next, visibleMode, versionAtStart);
          setTimeout(() => prefetchAdjacentRenders(next), 0);
        }
      } catch (err) {
        if (selectedSemitoneRef.current === next) {
          setError(err instanceof Error ? err.message : t.failedConnect);
        }
      } finally {
        if (selectedSemitoneRef.current === next) {
          setRenderUpdating(false);
        }
      }
    } else {
      setRenderUpdating(false);
      setReplaceResult(null);
      setAboveResult(null);
    }
  };

  const handleFretSelect = (fret: number) => {
    void applySemitoneShift(-fret);
  };

  const handleResultTabSelect = (tab: "replace" | "above") => {
    setActiveTab(tab);
    setShowOriginal(false);
    if (!detectionId || semitones === 0) return;
    const versionAtStart = editVersionRef.current;
    const key = renderCacheKey(semitones, versionAtStart);
    const cached = key ? renderCacheRef.current.get(key) : null;
    if (cached && renderHasMode(cached, tab)) {
      applyRenderResult(cached);
      return;
    }
    setRenderUpdating(true);
    void fetchRenderResult(semitones, tab)
      .then(data => {
        if (
          !data
          || selectedSemitoneRef.current !== semitones
          || editVersionRef.current !== versionAtStart
        ) return;
        applyRenderResult(data);
      })
      .catch(err => {
        if (selectedSemitoneRef.current === semitones) {
          setError(err instanceof Error ? err.message : t.failedConnect);
        }
      })
      .finally(() => {
        if (selectedSemitoneRef.current === semitones) {
          setRenderUpdating(false);
        }
      });
  };

  const activeResult = activeTab === "replace" ? replaceResult : aboveResult;
  const previewSrc = showOriginal ? originalImageUrl : activeResult;

  // Shared by the desktop result card and the mobile sheet.
  const addModeOverlays = (
    <>
      {/* Ghost bbox preview — snaps to nearest detected chord row */}
      {!showOriginal && addModeActive && snapRow && hoverImgPos && imgNaturalSize && (
        <div style={{
          position: "absolute",
          left:   `${(hoverImgPos.x / imgNaturalSize.w) * 100}%`,
          top:    `${(snapRow.y1    / imgNaturalSize.h) * 100}%`,
          width:  `${(80            / imgNaturalSize.w) * 100}%`,
          height: `${((snapRow.y2 - snapRow.y1) / imgNaturalSize.h) * 100}%`,
          border: "2px dashed #e05d00",
          borderRadius: 3,
          background: "rgba(224,93,0,0.12)",
          pointerEvents: "none",
        }} />
      )}
      {!showOriginal && addModeActive && (
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0,
          padding: "10px 16px",
          background: "rgba(0,0,0,0.65)",
          color: "white", fontSize: "0.8rem", fontWeight: 600,
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <span>Click on the image to place the chord</span>
          <button
            onClick={() => setAddModeActive(false)}
            style={{ background: "none", border: "1px solid rgba(255,255,255,0.4)", borderRadius: 6, padding: "2px 10px", color: "white", cursor: "pointer", fontSize: "0.75rem" }}
          >Cancel</button>
        </div>
      )}
    </>
  );

  // Mobile result board (≤640px). One state: `semitones`.
  const chosen = Boolean(detectionId) && semitones !== 0;
  const mobileSheetSrc = chosen && activeResult && !showOriginal ? activeResult : originalImageUrl;
  const step = mobileStepper(semitones);
  const summary = shiftSummary(semitones);
  const stepBusy = !detectionId || detecting || reRendering;

  return (
    <>
      <Head>
        <title>Capomatic</title>
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <meta name="description" content="Transpose chord sheets easily" />
      </Head>

      <div role="main" className="app-root" style={{ minHeight: "100vh", backgroundColor: "#F5EDD8", fontFamily: "'Inter', 'Segoe UI', Arial, sans-serif", overflowX: "hidden" }}>

        {/* Nav */}
        <nav className="d-only" style={{
          position: "sticky", top: 0, zIndex: 100,
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "0 24px", height: 52,
          background: "rgba(255, 253, 247, 0.95)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid rgba(0,0,0,0.06)",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {/* Hamburger */}
            <button
              onClick={() => setMenuOpen(v => !v)}
              aria-label={t.guide}
              aria-expanded={menuOpen}
              style={{ background: "none", border: "none", cursor: "pointer", padding: 4, display: "flex", alignItems: "center", justifyContent: "center" }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3a4847" strokeWidth="2" strokeLinecap="round">
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
            <svg viewBox="0 0 36 36" width="28" height="28">
              <circle cx="18" cy="18" r="17" fill="#3a4847" />
              <rect x="11" y="12" width="14" height="2.5" rx="1.2" fill="#e05d00" />
              <rect x="11" y="16" width="14" height="2.5" rx="1.2" fill="#e05d00" opacity="0.7" />
              <rect x="11" y="20" width="14" height="2.5" rx="1.2" fill="#e05d00" opacity="0.4" />
              <rect x="21" y="10" width="3" height="16" rx="1.5" fill="white" opacity="0.9" />
            </svg>
            <span style={{ fontWeight: 800, fontSize: "0.96rem", color: "#3a4847", letterSpacing: "-0.01em", fontFamily: "Georgia, serif", fontStyle: "italic" }}>
              Capo<span style={{ color: "#9c3d00" }}>matic</span>
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <LangToggle />
            <LoginButton />
          </div>
        </nav>


        {/* Mobile top bar (≤640px) */}
        <nav className="m-only m-nav" data-screen={file ? "result" : "home"}>
          {file ? (
            <button type="button" className="m-icon-btn" onClick={clearFile} aria-label={t.mBack}>
              <svg width="17" height="14" viewBox="0 0 16 14" fill="none" aria-hidden="true"><path d="M15 7H1m0 0l5.5-5.5M1 7l5.5 5.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>
            </button>
          ) : (
            <button type="button" className="m-icon-btn m-menu" onClick={() => setMenuOpen(v => !v)} aria-label={t.mOpenMenu} aria-expanded={menuOpen}>
              <svg width="18" height="12" viewBox="0 0 18 12" fill="none" aria-hidden="true"><path d="M0 1h18M0 6h18M0 11h18" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>
            </button>
          )}
          <MobileWordmark />
          <span className="m-spacer" />
          {file ? (
            <button type="button" className="m-icon-btn" onClick={() => fileInputRef.current?.click()} aria-label={t.mUploadAnother}>
              <svg width="18" height="18" viewBox="0 0 17 17" fill="none" aria-hidden="true"><path d="M8.5 12V3m0 0L4.8 6.7M8.5 3l3.7 3.7M2 12.5v1A1.5 1.5 0 003.5 15h10a1.5 1.5 0 001.5-1.5v-1" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>
            </button>
          ) : (
            <div className="m-nav-right">
              <LangToggle />
              <LoginButton />
            </div>
          )}
        </nav>

        {/* Hamburger backdrop + side panel */}
        <div className={`hamburger-backdrop${menuOpen ? " open" : ""}`} onClick={() => setMenuOpen(false)} />
        <div className={`hamburger-menu${menuOpen ? " open" : ""}`} ref={menuRef}>
          {/* Panel header */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 20px", height: 52, borderBottom: "1px solid rgba(0,0,0,0.07)" }}>
            <span style={{ fontWeight: 800, fontSize: "0.96rem", color: "#1a1a2e", fontFamily: "Georgia, serif", fontStyle: "italic" }}>
              Capo<span style={{ color: "#9c3d00" }}>matic</span>
            </span>
            <button onClick={() => setMenuOpen(false)} aria-label={t.closeMenu} style={{ background: "none", border: "none", cursor: "pointer", padding: 4, display: "flex" }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1a1a2e" strokeWidth="2" strokeLinecap="round">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          {/* Links */}
          <nav style={{ padding: "8px 0" }}>
            <Link href="/history" onClick={() => setMenuOpen(false)}
              style={{ display: "block", padding: "14px 24px", fontSize: "0.9rem", fontWeight: 600, color: "#1a1a2e", textDecoration: "none" }}>
              {t.myJobs}
            </Link>
            <button
              onClick={() => { setMenuOpen(false); setGuideStep(0); setGuideOpen(true); }}
              style={{ display: "block", width: "100%", textAlign: "left", background: "none", border: "none", cursor: "pointer", padding: "14px 24px", fontSize: "0.9rem", fontWeight: 600, color: "#1a1a2e" }}>
              {t.guide}
            </button>
          </nav>
        </div>

        {/* Upload-first hero */}
        {!file && (
          <section className="upload-hero d-only" style={{
            maxWidth: 760,
            margin: "0 auto",
            padding: "46px 20px 22px",
            display: "grid",
            gridTemplateColumns: "minmax(0, 1fr)",
            justifyItems: "center",
            textAlign: "center",
          }}>
            <h1 className={lang === "ko" ? "upload-hero-title upload-hero-title-bilingual" : "upload-hero-title"} style={{ maxWidth: 680, margin: "0 0 20px", fontSize: "clamp(2.45rem, 7vw, 4.1rem)", lineHeight: 1, fontWeight: 900, color: "#171923", letterSpacing: 0 }}>
              {lang === "ko" ? (
                <>
                  <span className="upload-hero-title-en">전조, 이제 쉽게 끝</span>
                  <span className="upload-hero-title-ko">악보 사진을 올려보세요</span>
                </>
              ) : t.heroHeadline}
            </h1>
            <button
              className="primary-upload-cta"
              onClick={() => fileInputRef.current?.click()}
              style={{
                display: "inline-flex", alignItems: "center", gap: 10,
                background: "linear-gradient(135deg, #a34200, #7f3000)",
                border: "none", cursor: "pointer",
                borderRadius: 12, padding: "15px 24px",
                color: "white", fontSize: "0.98rem", fontWeight: 900,
                boxShadow: "0 10px 28px rgba(224,93,0,0.28)",
                transition: "transform 0.18s ease, box-shadow 0.18s ease",
              }}
              onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-1px)"; e.currentTarget.style.boxShadow = "0 14px 34px rgba(224,93,0,0.34)"; }}
              onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "0 10px 28px rgba(224,93,0,0.28)"; }}
            >
              <Upload size={20} color="white" strokeWidth={2.4} />
              {t.heroPrimaryCta}
              <ArrowRight size={18} color="white" strokeWidth={2.4} />
            </button>
            {error && (
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 14, color: "#d4183d", fontSize: "0.78rem", fontWeight: 600 }}>
                <AlertCircle size={13} />
                {error}
              </div>
            )}
          </section>
        )}


        {/* Mobile home (≤640px): one left edge for menu glyph, copy and upload card */}
        {!file && (
          <section className="m-only m-home">
            <h1 className="m-hero">
              {lang === "ko" && <span className="m-kicker">전조, 이제 쉽게 끝</span>}
              <span className="m-headline">{lang === "ko" ? "악보 사진을 올려보세요" : t.heroHeadline}</span>
            </h1>
            <div className="m-dropwrap">
              <button type="button" className="m-drop" onClick={() => fileInputRef.current?.click()}>
                <span className="m-ruled" aria-hidden="true" />
                <span className="m-drop-mid">
                  <span className="m-cta">
                    <svg width="21" height="21" viewBox="0 0 19 19" fill="none" aria-hidden="true"><path d="M9.5 13.5V3m0 0L5.4 7.1M9.5 3l4.1 4.1M2.5 13v2A1.5 1.5 0 004 16.5h11a1.5 1.5 0 001.5-1.5v-2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>
                    {t.heroPrimaryCta}
                  </span>
                  <span className="m-sub">{t.mUploadLimits}</span>
                </span>
              </button>
            </div>
            {error && (
              <p className="m-home-error" role="alert"><AlertCircle size={13} aria-hidden="true" /> {error}</p>
            )}
          </section>
        )}

        {file && (
          <div className="active-title-wrap d-only" style={{ textAlign: "center", padding: "30px 24px 0" }}>
            <h1 className="active-title" style={{ margin: "0 0 6px", fontSize: "clamp(1.8rem, 5vw, 2.5rem)", fontWeight: 900, color: "#1a1a2e", letterSpacing: 0 }}>
              {t.subtitle}
            </h1>
          </div>
        )}

        {/* Active info bar — shown once a file is loaded */}
        {file && (
          <div className="active-info-bar d-only" style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "24px 20px 16px", gap: 10 }}>
            {detecting && (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6, width: 260 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#9c3d00", fontSize: "0.8rem", fontWeight: 600 }}>
                  <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
                  {t.detectingChords}
                </div>
                <div style={{ width: "100%", height: 4, background: "rgba(0,0,0,0.1)", borderRadius: 2, overflow: "hidden" }}>
                  <div style={{ width: `${detectProgress}%`, height: "100%", background: "linear-gradient(90deg,#e05d00,#c84b00)", borderRadius: 2, transition: "width 0.3s ease-out" }} />
                </div>
                <span style={{ fontSize: "0.7rem", color: "#646464" }}>{(detectElapsed / 1000).toFixed(1)}s</span>
              </div>
            )}

            {!detecting && detectionId && originalKey && (
              <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 8, fontSize: "0.8rem", justifyContent: "center" }}>
                <span style={{ color: "#28c45e", fontWeight: 700 }}>✓</span>
                <span style={{ color: "#666" }}>{t.detectedKey}</span>
                <span style={{ fontWeight: 700, color: "#1a1a2e", background: "rgba(26,26,46,0.07)", padding: "2px 10px", borderRadius: 20 }}>
                  {originalKey}
                </span>
                {semitones !== 0 && targetKey && (
                  <>
                    <span style={{ color: "#ccc" }}>→</span>
                    <span style={{ fontWeight: 700, color: "#9c3d00", background: "rgba(163,66,0,0.08)", padding: "2px 10px", borderRadius: 20 }}>
                      {targetKey}
                    </span>
                    {semitones < 0 ? (
                      <span style={{ fontSize: "0.72rem", color: "#646464", fontWeight: 600 }}>
                        {t.capo} {Math.abs(semitones)}
                      </span>
                    ) : (
                      <span style={{ fontSize: "0.72rem", color: "#646464", fontWeight: 600 }}>
                        {t.transposeUpInfo(semitones)}
                      </span>
                    )}
                  </>
                )}
              </div>
            )}

            {!detecting && (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flexWrap: "wrap", gap: 8 }}>
                <button
                  onClick={clearFile}
                  style={{ background: "none", border: "1.5px solid rgba(0,0,0,0.15)", borderRadius: 20, padding: "5px 14px", fontSize: "0.75rem", fontWeight: 700, color: "#595959", cursor: "pointer", letterSpacing: "0.04em" }}
                >
                  {t.changeSheet}
                </button>
              </div>
            )}

            {error && (
              <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#d4183d", fontSize: "0.78rem", fontWeight: 600 }}>
                <AlertCircle size={13} />
                {error}
              </div>
            )}
          </div>
        )}


        {/* Mobile result (≤640px): the sheet on top, the board pinned to the bottom */}
        {file && (
          <div className="m-only m-result">
            <div className="m-sheet">
              <div className="m-page">
                {mobileSheetSrc && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    ref={mobileImgRef}
                    src={mobileSheetSrc}
                    alt={mobileSheetSrc === originalImageUrl ? t.originalSheetAlt : t.renderedSheetAlt(activeTab)}
                    style={{ cursor: addModeActive && !showOriginal ? "crosshair" : "default" }}
                    onLoad={e => setImgNaturalSize({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
                    onClick={handleImageClick}
                    onMouseMove={handleImageMouseMove}
                    onMouseLeave={handleImageMouseLeave}
                    onTouchMove={handleImageTouchMove}
                    onTouchEnd={handleImageTouchEnd}
                  />
                )}
                {chosen && addModeOverlays}
                {detecting && <div className="m-scan" aria-hidden="true" />}
              </div>
            </div>
            <div className="m-board">
              <div className="m-bhead" aria-live="polite">
                {detecting ? (
                  <>
                    <span className="m-spin" aria-hidden="true" />
                    <span className="m-muted">{t.mReadingSheet}</span>
                  </>
                ) : !detectionId ? (
                  error ? <span className="m-err"><AlertCircle size={13} aria-hidden="true" /> {error}</span> : null
                ) : semitones === 0 ? (
                  <>
                    <span className="m-ok" aria-hidden="true">✓</span>
                    <span className="m-muted">{t.mDetectedKey}</span>
                    {originalKey && <span className="m-pill">{prettyKey(originalKey)}</span>}
                    <span className="m-muted m-right m-small">{t.mPickCapo}</span>
                  </>
                ) : (
                  <>
                    <span className="m-ok" aria-hidden="true">✓</span>
                    <span className="m-pill">{prettyKey(originalKey)}</span>
                    <span className="m-arrow" aria-hidden="true">→</span>
                    <span className="m-pill m-to">{prettyKey(targetKey)}</span>
                    {(rendering || renderUpdating) && <span className="m-spin m-spin-sm" aria-hidden="true" />}
                    <span className="m-muted m-right">
                      {summary.kind === "capo" ? t.mCapoN(summary.capo) : t.mShiftSemitones(summary.semitones)}
                    </span>
                  </>
                )}
              </div>
              {error && detectionId && <p className="m-board-error" role="alert">{error}</p>}
              <div className="m-fretbox">
                {isMobile && (
                  <GuitarFretboard
                    capoFret={step.capo || null}
                    onFretSelect={detectionId && !detecting ? handleFretSelect : undefined}
                  />
                )}
              </div>
              <div className="m-stepper">
                <button
                  type="button"
                  className="m-sq"
                  onClick={() => void applySemitoneShift(step.minus.next, SHIFT_LIMIT)}
                  disabled={stepBusy || step.minus.disabled}
                  aria-label={step.minus.action === "capoDown" ? t.mCapoDown : t.mKeyUpStep}
                >−</button>
                <div className="m-val" aria-live="polite">
                  <small>
                    {step.label.kind === "capo" ? t.capoPosition : step.label.kind === "keyUp" ? t.mKeyUpNoCapo : t.mOutOfRangeDown}
                  </small>
                  <b>{step.label.kind === "capo" ? step.label.capo : t.mSemitoneValue(step.label.semitones)}</b>
                </div>
                <button
                  type="button"
                  className="m-sq"
                  onClick={() => void applySemitoneShift(step.plus.next, SHIFT_LIMIT)}
                  disabled={stepBusy || step.plus.disabled}
                  aria-label={step.plus.action === "capoUp" ? t.mCapoUp : t.mKeyDownStep}
                >+</button>
              </div>
              <div className="m-seg" role="group" aria-label={t.mDisplayMode}>
                {(["replace", "above"] as const).map(tab => (
                  <button key={tab} type="button" aria-pressed={activeTab === tab} disabled={!chosen} onClick={() => handleResultTabSelect(tab)}>
                    {tab === "replace" ? t.replace : t.above}
                  </button>
                ))}
              </div>
              <div className="m-acts">
                <button type="button" className="m-btn m-btn-ghost" disabled={!chosen} onClick={() => setShowOriginal(v => !v)}>
                  {showOriginal ? t.viewRendered : t.viewOriginal}
                </button>
                <button type="button" className="m-btn m-btn-primary" disabled={!chosen || showOriginal || !activeResult} onClick={handleDownload}>
                  <svg width="16" height="16" viewBox="0 0 15 15" fill="none" aria-hidden="true"><path d="M7.5 1v9m0 0L4 6.6M7.5 10L11 6.6M1.5 11v1.5A1.5 1.5 0 003 14h9a1.5 1.5 0 001.5-1.5V11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
                  {t.downloadPng}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Fretboard section — full width, no card, responsive padding via CSS */}
        <section className="fretboard-section d-only">
          <GuitarFretboard capoFret={capoFret} onFretSelect={detectionId && !detecting ? handleFretSelect : undefined} />
        </section>

        {/* Semitone selector */}
        <div className="transpose-selector d-only" style={{ maxWidth: 360, margin: "16px auto 0", padding: "0 20px" }}>
          <div className="transpose-panel" style={{ background: "rgba(255,255,255,0.55)", borderRadius: 16, padding: 12, border: "1px solid rgba(255,255,255,0.8)", backdropFilter: "blur(8px)", boxShadow: "0 2px 12px rgba(0,0,0,0.05)", display: "grid", gridTemplateColumns: "52px 1fr 52px", alignItems: "center", gap: 10 }}>
            <button
              onClick={() => applySemitoneShift(semitones - 1)}
              disabled={!detectionId || detecting || reRendering || semitones <= -7}
              aria-label={t.transposeDown}
              style={{
                height: 44, borderRadius: 12,
                border: "1.5px solid rgba(0,0,0,0.1)",
                background: semitones < 0 ? "linear-gradient(135deg, #a34200, #7f3000)" : "rgba(255,255,255,0.75)",
                color: semitones < 0 ? "white" : "#3a4847",
                fontSize: "1.35rem", fontWeight: 900,
                cursor: detectionId && !detecting && !reRendering && semitones > -7 ? "pointer" : "not-allowed",
                opacity: detectionId && !detecting && !reRendering && semitones > -7 ? 1 : 0.45,
              }}
            >-</button>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "0.68rem", fontWeight: 800, color: "#695c42", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                {t.capoPosition}
              </div>
              <div style={{ marginTop: 3, fontSize: "1.05rem", fontWeight: 900, color: "#1a1a2e" }}>
                {rendering ? t.rendering : renderUpdating ? t.updating : semitones > 0 ? `+${semitones}` : semitones}
              </div>
            </div>
            <button
              onClick={() => applySemitoneShift(semitones + 1)}
              disabled={!detectionId || detecting || reRendering || semitones >= 7}
              aria-label={t.transposeUp}
              style={{
                height: 44, borderRadius: 12,
                border: "1.5px solid rgba(0,0,0,0.1)",
                background: semitones > 0 ? "linear-gradient(135deg, #0b4ea2, #093b7a)" : "rgba(255,255,255,0.75)",
                color: semitones > 0 ? "white" : "#3a4847",
                fontSize: "1.35rem", fontWeight: 900,
                cursor: detectionId && !detecting && !reRendering && semitones < 7 ? "pointer" : "not-allowed",
                opacity: detectionId && !detecting && !reRendering && semitones < 7 ? 1 : 0.45,
              }}
            >+</button>
          </div>
        </div>

        {/* Result section */}
        {(replaceResult || aboveResult) && (
          <div ref={resultRef} className="result-wrap" style={{ maxWidth: 720, margin: "32px auto 48px", padding: "0 20px" }}>
            <div className="result-card" style={{ background: "rgba(230, 226, 219, 0.5)", borderRadius: 18, padding: "20px 20px 20px", border: "1px solid rgba(0,0,0,0.05)" }}>
              {/* Replace / Above toggle */}
              <div className="d-only" style={{ display: "flex", gap: 6, marginBottom: 16, background: "rgba(0,0,0,0.04)", borderRadius: 10, padding: 4 }}>
                {(["replace", "above"] as const).map(tab => (
                  <button
                    key={tab}
                    onClick={() => handleResultTabSelect(tab)}
                    style={{
                      flex: 1, padding: "10px 0", border: "none", cursor: "pointer",
                      borderRadius: 8,
                      background: activeTab === tab ? "white" : "transparent",
                      color: activeTab === tab ? "#3a4847" : "#666",
                      fontSize: "0.8rem", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase",
                      boxShadow: activeTab === tab ? "0 1px 4px rgba(0,0,0,0.08)" : "none",
                      transition: "all 0.18s",
                    }}
                  >
                    {tab === "replace" ? t.replace : t.above}
                  </button>
                ))}
              </div>
              <button
                className="d-only"
                onClick={() => setShowOriginal(v => !v)}
                disabled={!originalImageUrl}
                style={{
                  width: "100%", marginBottom: 12, padding: "9px 0", borderRadius: 10,
                  border: "1.5px solid rgba(0,0,0,0.12)",
                  background: showOriginal ? "#1a1a2e" : "rgba(255,255,255,0.72)",
                  color: showOriginal ? "white" : "#3a4847",
                  fontSize: "0.78rem", fontWeight: 900, cursor: originalImageUrl ? "pointer" : "not-allowed",
                }}
              >
                {showOriginal ? t.viewRendered : t.viewOriginal}
              </button>
              {/* Sheet image */}
              <div className="d-only" style={{ position: "relative", borderRadius: 12, overflow: "hidden", background: "white" }}>
                {previewSrc && (
                  <img
                    ref={imgRef}
                    src={previewSrc}
                    alt={showOriginal ? t.originalSheetAlt : t.renderedSheetAlt(activeTab)}
                    style={{ width: "100%", display: "block", cursor: addModeActive && !showOriginal ? "crosshair" : "default" }}
                    onLoad={e => setImgNaturalSize({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
                    onClick={handleImageClick}
                    onMouseMove={handleImageMouseMove}
                    onMouseLeave={handleImageMouseLeave}
                    onTouchMove={handleImageTouchMove}
                    onTouchEnd={handleImageTouchEnd}
                  />
                )}
                {addModeOverlays}
              </div>

              {/* Chord position modal */}
              {pendingPosition && (
                <div style={{
                  position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)",
                  background: "white", borderRadius: 12, padding: "20px 24px",
                  boxShadow: "0 8px 32px rgba(0,0,0,0.25)", zIndex: 1000, minWidth: 260,
                }}>
                  <p style={{ margin: "0 0 12px", fontSize: "0.85rem", fontWeight: 700, color: "#1a1a2e" }}>Add chord at position</p>
                  <input
                    autoFocus
                    type="text"
                    placeholder="e.g. Dm7"
                    value={pendingChordText}
                    onChange={e => setPendingChordText(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === "Enter") confirmPositionedChord();
                      if (e.key === "Escape") { setPendingPosition(null); setPendingChordText(""); }
                    }}
                    style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1.5px solid #e05d00", fontSize: "0.9rem", fontWeight: 700, outline: "none", boxSizing: "border-box" }}
                  />
                  <div style={{ display: "flex", gap: 8, marginTop: 12, justifyContent: "flex-end" }}>
                    <button
                      onClick={() => { setPendingPosition(null); setPendingChordText(""); }}
                      style={{ background: "none", border: "1px solid rgba(0,0,0,0.15)", borderRadius: 8, padding: "7px 16px", fontSize: "0.8rem", fontWeight: 600, cursor: "pointer", color: "#666" }}
                    >Cancel</button>
                    <button
                      onClick={confirmPositionedChord}
                      disabled={!pendingChordText.trim()}
                      style={{ background: "linear-gradient(135deg,#a34200,#7f3000)", border: "none", borderRadius: 8, padding: "7px 16px", fontSize: "0.8rem", fontWeight: 700, cursor: "pointer", color: "white", opacity: pendingChordText.trim() ? 1 : 0.5 }}
                    >Add</button>
                  </div>
                </div>
              )}
              {/* Download */}
              <button
                className="d-only"
                onClick={handleDownload}
                disabled={showOriginal}
                style={{
                  width: "100%", marginTop: 16, padding: "12px 0", borderRadius: 10, border: "none",
                  background: showOriginal ? "linear-gradient(135deg, #aaa, #999)" : "linear-gradient(135deg, #1a9e50, #158040)",
                  color: "white", fontSize: "0.85rem", fontWeight: 700, cursor: showOriginal ? "not-allowed" : "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center", gap: 7,
                  boxShadow: showOriginal ? "none" : "0 3px 12px rgba(21,128,64,0.25)", transition: "all 0.18s",
                }}
              >
                <Download size={15} />
                {t.downloadPng}
              </button>

              {/* Chord editor */}
              {!showOriginal && editableChords.length > 0 && (
                <div className="chord-editor" style={{ marginTop: 20, paddingTop: 18, borderTop: "1px solid rgba(0,0,0,0.07)" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                    <span style={{ fontSize: "0.68rem", fontWeight: 700, color: "#695c42", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                      Detected Chords
                    </span>
                    {JSON.stringify(editableChords) !== JSON.stringify(detectedChords) && (
                      <button
                        onClick={() => { setEditableChords(detectedChords); setEditingIdx(null); setAddingChord(false); }}
                        style={{ background: "none", border: "1px solid rgba(0,0,0,0.15)", borderRadius: 20, padding: "3px 12px", fontSize: "0.7rem", fontWeight: 700, color: "#595959", cursor: "pointer" }}
                      >
                        Reset
                      </button>
                    )}
                  </div>

                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
                    {editableChords.map((chord, i) => (
                      editingIdx === i ? (
                        <input
                          key={i}
                          autoFocus
                          defaultValue={chord.text}
                          onBlur={e => {
                            const v = e.target.value.trim();
                            if (v) setEditableChords(prev => prev.map((c, j) => j === i ? { ...c, text: v } : c));
                            setEditingIdx(null);
                          }}
                          onKeyDown={e => {
                            if (e.key === "Enter") (e.target as HTMLInputElement).blur();
                            if (e.key === "Escape") setEditingIdx(null);
                          }}
                          style={{ width: 72, padding: "4px 8px", borderRadius: 20, border: "1.5px solid #e05d00", fontSize: "0.8rem", fontWeight: 700, outline: "none", textAlign: "center" }}
                        />
                      ) : (
                        <span
                          key={i}
                          onClick={() => setEditingIdx(i)}
                          style={{ display: "inline-flex", alignItems: "center", gap: 3, background: "rgba(255,255,255,0.85)", border: "1px solid rgba(0,0,0,0.12)", borderRadius: 20, padding: "4px 6px 4px 10px", fontSize: "0.8rem", fontWeight: 700, color: "#1a1a2e", cursor: "pointer", userSelect: "none" }}
                        >
                          {chord.text}
                          <button
                            onClick={e => { e.stopPropagation(); setEditableChords(prev => prev.filter((_, j) => j !== i)); if (editingIdx === i) setEditingIdx(null); }}
                            style={{ background: "none", border: "none", cursor: "pointer", padding: "0 2px", color: "#bbb", fontSize: "0.7rem", lineHeight: 1 }}
                          >✕</button>
                        </span>
                      )
                    ))}

                    {addingChord ? (
                      <input
                        autoFocus
                        value={addInput}
                        onChange={e => setAddInput(e.target.value)}
                        placeholder="e.g. Am7"
                        onBlur={() => { setAddingChord(false); setAddInput(""); }}
                        onKeyDown={e => {
                          if (e.key === "Enter") {
                            const v = addInput.trim();
                            if (v) setEditableChords(prev => [...prev, { text: v, bbox: null }]);
                            setAddingChord(false);
                            setAddInput("");
                          }
                          if (e.key === "Escape") { setAddingChord(false); setAddInput(""); }
                        }}
                        style={{ width: 84, padding: "4px 10px", borderRadius: 20, border: "1.5px solid #e05d00", fontSize: "0.8rem", fontWeight: 700, outline: "none" }}
                      />
                    ) : (
                      <button
                        onClick={() => setAddingChord(true)}
                        style={{ background: "none", border: "1.5px dashed rgba(0,0,0,0.18)", borderRadius: 20, padding: "4px 12px", fontSize: "0.78rem", fontWeight: 700, color: "#646464", cursor: "pointer" }}
                      >
                        + Add
                      </button>
                    )}
                    {!addingChord && (
                      <button
                        onClick={() => setAddModeActive(true)}
                        style={{ background: "none", border: "1.5px dashed rgba(156,61,0,0.5)", borderRadius: 20, padding: "4px 12px", fontSize: "0.78rem", fontWeight: 700, color: "#9c3d00", cursor: "pointer" }}
                      >
                        + Add at position
                      </button>
                    )}
                  </div>

                  {editableChords.some(c => c.bbox === null) && (
                    <p style={{ margin: "8px 0 0", fontSize: "0.7rem", color: "#9c3d00", fontWeight: 600 }}>
                      ⚠ Added chords won't be positioned on the image.
                    </p>
                  )}

                  {JSON.stringify(editableChords) !== JSON.stringify(detectedChords) && (
                    <button
                      onClick={handleReRender}
                      disabled={reRendering}
                      style={{
                        marginTop: 12, width: "100%", padding: "11px 0", borderRadius: 10, border: "none",
                        background: reRendering ? "linear-gradient(135deg,#aaa,#999)" : "linear-gradient(135deg,#3a4847,#2a3837)",
                        color: "white", fontSize: "0.85rem", fontWeight: 700,
                        cursor: reRendering ? "not-allowed" : "pointer",
                        display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                        transition: "all 0.2s",
                      }}
                    >
                      {reRendering
                        ? <><Loader2 size={15} style={{ animation: "spin 1s linear infinite" }} /> Re-rendering…</>
                        : "↺ Re-render with edits"}
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        )}


        {/* Footer */}
        <footer style={{ borderTop: "1px solid rgba(0,0,0,0.06)", padding: "18px 24px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
          <span style={{ fontSize: "0.75rem", color: "#675d4a", fontWeight: 700, fontStyle: "italic", fontFamily: "Georgia, serif" }}>
            Capo<span style={{ color: "#9c3d00" }}>matic</span>
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <span style={{ fontSize: "0.7rem", color: "#666", fontWeight: 500 }}>{t.footerTagline}</span>
            <Link href="/privacy" style={{ fontSize: "0.7rem", color: "#665e54" }}>{t.privacy}</Link>
            <Link href="/terms" style={{ fontSize: "0.7rem", color: "#665e54" }}>{t.terms}</Link>
          </div>
        </footer>

        <input ref={fileInputRef} type="file" accept="image/png,image/jpeg" style={{ display: "none" }} onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }} />

        {/* Guide modal */}
        {guideOpen && (() => {
          const steps = [
            { icon: "\uD834\uDD1E", label: t.featureUploadLabel, desc: t.featureUploadDesc },
            { icon: "\u22AB", label: t.featureCapoLabel, desc: t.featureCapoDesc },
            { icon: "\u266A", label: t.featureDownloadLabel, desc: t.featureDownloadDesc },
          ];
          const step = steps[guideStep];
          const isLast = guideStep === steps.length - 1;
          return (
            <div style={{ position: "fixed", inset: 0, zIndex: 300, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.35)" }}
              onClick={() => setGuideOpen(false)}>
              <div ref={guideDialogRef} role="dialog" aria-modal="true" aria-labelledby="guide-title" onKeyDown={trapGuideFocus}
                style={{ background: "white", borderRadius: 20, width: "min(380px, 90vw)", padding: "40px 32px 28px", textAlign: "center", boxShadow: "0 16px 48px rgba(0,0,0,0.18)" }}
                onClick={e => e.stopPropagation()}>
                {/* Icon */}
                <div aria-hidden="true" style={{ fontSize: "3rem", marginBottom: 20, color: "#9c3d00", lineHeight: 1 }}>{step.icon}</div>
                {/* Title */}
                <h2 id="guide-title" style={{ margin: "0 0 10px", fontSize: "1.3rem", fontWeight: 800, color: "#1a1a2e" }}>{step.label}</h2>
                {/* Description */}
                <p style={{ margin: "0 0 28px", fontSize: "0.88rem", color: "#666", lineHeight: 1.5 }}>{step.desc}</p>
                {/* Dot indicators */}
                <div aria-hidden="true" style={{ display: "flex", justifyContent: "center", gap: 8, marginBottom: 28 }}>
                  {steps.map((_, i) => (
                    <div key={i} style={{ width: 10, height: 10, borderRadius: "50%", background: i === guideStep ? "#e05d00" : "#e8ddd0", transition: "background 0.2s" }} />
                  ))}
                </div>
                {/* Buttons */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 16 }}>
                  <button onClick={() => setGuideOpen(false)}
                    style={{ background: "none", border: "none", cursor: "pointer", padding: "12px 28px", fontSize: "0.9rem", fontWeight: 600, color: "#595959" }}>
                    {t.skip}
                  </button>
                  <button onClick={() => { if (isLast) setGuideOpen(false); else setGuideStep(guideStep + 1); }}
                    style={{ background: "#a34200", color: "white", border: "none", cursor: "pointer", borderRadius: 12, padding: "12px 48px", fontSize: "0.95rem", fontWeight: 700, boxShadow: "0 4px 14px rgba(163,66,0,0.35)", transition: "all 0.2s" }}
                    onMouseEnter={e => (e.currentTarget.style.background = "#7f3000")}
                    onMouseLeave={e => (e.currentTarget.style.background = "#a34200")}>
                    {isLast ? t.done : t.next}
                  </button>
                </div>
              </div>
            </div>
          );
        })()}

        {saveOverlayUrl && (
          <div
            role="dialog"
            aria-modal="true"
            aria-label={t.saveImageTitle}
            onClick={closeSaveOverlay}
            style={{
              position: "fixed", inset: 0, zIndex: 1000, background: "rgba(20,16,10,0.92)",
              display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
              gap: 14, padding: 16,
            }}
          >
            <p style={{ margin: 0, color: "white", fontSize: "0.95rem", fontWeight: 700, textAlign: "center" }}>
              {t.longPressToSave}
            </p>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={saveOverlayUrl}
              alt={t.saveImageTitle}
              onClick={e => e.stopPropagation()}
              style={{ maxWidth: "100%", maxHeight: "75vh", objectFit: "contain", borderRadius: 8, background: "white" }}
            />
            <button
              onClick={closeSaveOverlay}
              style={{
                minHeight: 44, padding: "10px 28px", borderRadius: 10, border: "1px solid rgba(255,255,255,0.6)",
                background: "transparent", color: "white", fontSize: "0.9rem", fontWeight: 600, cursor: "pointer",
              }}
            >
              {t.closeDialog}
            </button>
          </div>
        )}

        <style>{`
          @keyframes spin { to { transform: rotate(360deg); } }
          ::-webkit-scrollbar { height: 5px; }
          ::-webkit-scrollbar-track { background: rgba(0,0,0,0.04); }
          ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.18); border-radius: 3px; }
        `}</style>
      </div>
    </>
  );
}
