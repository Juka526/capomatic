import { useState, useRef, useCallback, useEffect, useMemo } from "react";
import { Upload, Download, Loader2, AlertCircle, ArrowRight, CheckCircle2 } from "lucide-react";
import Head from "next/head";
import Link from "next/link";
import LoginButton from "@/components/LoginButton";
import { useAuth } from "@/components/AuthProvider";
import { useLang, LangToggle } from "@/components/LangProvider";
import { GuitarFretboard } from "@/components/GuitarFretboard";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const MAX_FILE_SIZE = 8 * 1024 * 1024;

type ChordItem = { text: string; bbox: number[] | null };
const ESTIMATED_DETECT_MS = 13000;
const KEY_NAMES = ["C","Db","D","Eb","E","F","F#","G","Ab","A","Bb","B"];

function computeTargetKey(originalKey: string, semitones: number): string {
  const idx = KEY_NAMES.indexOf(originalKey);
  if (idx === -1) return originalKey;
  return KEY_NAMES[((idx + semitones) % 12 + 12) % 12];
}

type Row = { y1: number; y2: number; yCenter: number };

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
  const { user, isAuthenticated, login } = useAuth();
  const { t } = useLang();

  const [file, setFile] = useState<File | null>(null);
  const [selection, setSelection] = useState<number>(0); // capo/down transpose, 0 to 7
  const [transposeUp, setTransposeUp] = useState<number>(0); // positive semitone transpose, 0 to 7
  const [useGptHybrid, setUseGptHybrid] = useState(false);
  const [hybridRefining, setHybridRefining] = useState(false);
  const [hybridApplied, setHybridApplied] = useState(false);
  const [hybridStatus, setHybridStatus] = useState<string | null>(null);

  const [detectionId, setDetectionId] = useState<string | null>(null);
  const [originalKey, setOriginalKey] = useState<string | null>(null);
  const [detecting, setDetecting] = useState(false);
  const [detectProgress, setDetectProgress] = useState(0);
  const [detectElapsed, setDetectElapsed] = useState(0);

  const [replaceResult, setReplaceResult] = useState<string | null>(null);
  const [aboveResult, setAboveResult] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"replace" | "above">("replace");
  const [rendering, setRendering] = useState(false);

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
  const imgRef = useRef<HTMLImageElement>(null);

  // Close hamburger menu on outside click
  useEffect(() => {
    if (!menuOpen) return;
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [menuOpen]);

  const capoFret = selection > 0 ? selection : null;
  const semitones = transposeUp > 0 ? transposeUp : -selection;

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
    const el = imgRef.current;
    if (!el) return;
    const handler = (e: TouchEvent) => { if (addModeActive) e.preventDefault(); };
    el.addEventListener("touchmove", handler, { passive: false });
    return () => el.removeEventListener("touchmove", handler);
  }, [addModeActive]);

  useEffect(() => {
    if (!detecting) return;
    const start = Date.now();
    const id = setInterval(() => {
      const dt = Date.now() - start;
      setDetectElapsed(dt);
      setDetectProgress(Math.min(95, (1 - Math.exp(-3 * dt / ESTIMATED_DETECT_MS)) * 100));
    }, 200);
    return () => clearInterval(id);
  }, [detecting]);

  const runDetection = useCallback(async (f: File) => {
    setDetecting(true);
    setDetectProgress(0);
    setDetectElapsed(0);
    setError(null);
    setDetectionId(null);
    setHybridApplied(false);
    setHybridStatus(null);
    setOriginalKey(null);
    setReplaceResult(null);
    setAboveResult(null);
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
      formData.append("ocr_engine", useGptHybrid ? "paddle-gpt" : "paddle");
      const res = await fetch(`${API_URL}/detect`, { method: "POST", body: formData });
      if (!res.ok) throw new Error((await res.text()) || `Server error (${res.status})`);
      const data = await res.json();
      setDetectProgress(100);
      setDetectionId(data.detection_id);
      setOriginalKey(data.original_key);
      const chords: ChordItem[] = (data.chords || []).map((c: any) => ({ text: c.text, bbox: c.bbox }));
      setDetectedChords(chords);
      setEditableChords(chords);
      setHybridApplied(data.meta?.ocr_engine === "paddle-gpt-hybrid");
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedConnect);
    } finally {
      setDetecting(false);
    }
  }, [t, useGptHybrid]);

  const handleFile = useCallback((f: File) => {
    if (!f.type.match(/^image\/(png|jpeg)$/)) { setError(t.onlyPngJpg); return; }
    if (f.size > MAX_FILE_SIZE) { setError(t.fileTooLarge); return; }
    setFile(f);
    setError(null);
    setSelection(0);
    setTransposeUp(0);
    runDetection(f);
  }, [runDetection, t]);

  const performRender = async (chordsOverride?: ChordItem[]) => {
    if (!detectionId) return;
    setRendering(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("detection_id", detectionId);
      formData.append("semitones", semitones.toString());
      if (chordsOverride) {
        formData.append("chords_override", JSON.stringify(chordsOverride));
      }
      const res = await fetch(`${API_URL}/render`, { method: "POST", body: formData });
      if (!res.ok) throw new Error((await res.text()) || `Server error (${res.status})`);
      const data = await res.json();
      setReplaceResult(data.replace_image);
      setAboveResult(data.above_image);
      setActiveTab("replace");
      saveToLocalHistory(file?.name, originalKey, data.target_key, semitones);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 150);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedConnect);
    } finally {
      setRendering(false);
    }
  };

  const handleConvert = async () => {
    if (!detectionId || semitones === 0) return;
    await performRender();
  };

  const saveToLocalHistory = (fileName: string | undefined, origKey: string | null, tgtKey: string | null, semi: number) => {
    try {
      const existing = JSON.parse(localStorage.getItem("tc-history") || "[]");
      const entry = {
        id: Math.random().toString(36).slice(2),
        song_name: fileName ? fileName.replace(/\.[^.]+$/, "") : null,
        original_key: origKey,
        target_key: tgtKey,
        semitones: semi,
        timestamp: new Date().toISOString(),
      };
      const updated = [entry, ...existing].slice(0, 50);
      localStorage.setItem("tc-history", JSON.stringify(updated));
    } catch {}
  };

  const handleReRender = async () => {
    if (!detectionId) return;
    setReRendering(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("detection_id", detectionId);
      formData.append("semitones", semitones.toString());
      formData.append("chords_override", JSON.stringify(editableChords));
      const res = await fetch(`${API_URL}/render`, { method: "POST", body: formData });
      if (!res.ok) throw new Error((await res.text()) || `Server error (${res.status})`);
      const data = await res.json();
      setReplaceResult(data.replace_image);
      setAboveResult(data.above_image);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedConnect);
    } finally {
      setReRendering(false);
    }
  };

  const handleGptHybridRefine = async () => {
    if (!detectionId || hybridRefining) return;
    const shouldRenderAfterRefine = Boolean((replaceResult || aboveResult) && semitones !== 0);
    setHybridRefining(true);
    setError(null);
    setHybridStatus(null);
    try {
      const formData = new FormData();
      formData.append("detection_id", detectionId);
      const res = await fetch(`${API_URL}/detect/refine`, { method: "POST", body: formData });
      if (!res.ok) {
        let message = `Server error (${res.status})`;
        try {
          const errData = await res.json();
          message = errData.detail || message;
        } catch {
          message = (await res.text()) || message;
        }
        throw new Error(message);
      }
      const data = await res.json();
      const meta = data.meta || {};
      if (!meta.gpt_used) {
        throw new Error(meta.gpt_error || t.gptHybridUnavailable);
      }
      const chords: ChordItem[] = (data.chords || []).map((c: any) => ({ text: c.text, bbox: c.bbox }));
      setDetectedChords(chords);
      setEditableChords(chords);
      setHybridApplied(true);
      const added = Number(meta.gpt_gap_candidates_accepted ?? meta.gpt_gap_count ?? 0);
      const corrected = Number(meta.gpt_text_replaced ?? 0);
      setHybridStatus(
        added > 0 || corrected > 0
          ? t.gptHybridChanged(added, corrected)
          : t.gptHybridNoChange
      );
      setEditingIdx(null);
      setAddingChord(false);
      setAddModeActive(false);
      setPendingPosition(null);
      setPendingChordText("");
      setHoverImgPos(null);
      if (shouldRenderAfterRefine) {
        await performRender(chords);
      } else {
        setReplaceResult(null);
        setAboveResult(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedConnect);
    } finally {
      setHybridRefining(false);
    }
  };

  const handleImageClick = (e: React.MouseEvent<HTMLImageElement>) => {
    if (!addModeActive || !imgNaturalSize) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = Math.round((e.clientX - rect.left) * (imgNaturalSize.w / rect.width));
    const y = Math.round((e.clientY - rect.top) * (imgNaturalSize.h / rect.height));
    const row = nearestRow(detectedRows, y);
    setPendingPosition({ x, y1: row?.y1 ?? y, y2: row?.y2 ?? (y + 35) });
    setAddModeActive(false);
    setHoverImgPos(null);
  };

  const handleImageMouseMove = (e: React.MouseEvent<HTMLImageElement>) => {
    if (!addModeActive || !imgNaturalSize) return;
    const rect = e.currentTarget.getBoundingClientRect();
    setHoverImgPos({
      x: Math.round((e.clientX - rect.left) * (imgNaturalSize.w / rect.width)),
      y: Math.round((e.clientY - rect.top)  * (imgNaturalSize.h / rect.height)),
    });
  };

  const handleImageMouseLeave = () => setHoverImgPos(null);

  const handleImageTouchMove = (e: React.TouchEvent<HTMLImageElement>) => {
    if (!addModeActive || !imgNaturalSize) return;
    const touch = e.touches[0];
    const rect = e.currentTarget.getBoundingClientRect();
    setHoverImgPos({
      x: Math.round((touch.clientX - rect.left) * (imgNaturalSize.w / rect.width)),
      y: Math.round((touch.clientY - rect.top)  * (imgNaturalSize.h / rect.height)),
    });
  };

  const handleImageTouchEnd = (e: React.TouchEvent<HTMLImageElement>) => {
    if (!addModeActive || !imgNaturalSize || !hoverImgPos) return;
    e.preventDefault();
    const row = nearestRow(detectedRows, hoverImgPos.y);
    setPendingPosition({ x: hoverImgPos.x, y1: row?.y1 ?? hoverImgPos.y, y2: row?.y2 ?? (hoverImgPos.y + 35) });
    setAddModeActive(false);
    setHoverImgPos(null);
  };

  const confirmPositionedChord = () => {
    if (!pendingPosition || !pendingChordText.trim()) return;
    const { x, y1, y2 } = pendingPosition;
    setEditableChords(prev => [...prev, {
      text: pendingChordText.trim(),
      bbox: [x, y1, x + 80, y2],
    }]);
    setPendingPosition(null);
    setPendingChordText("");
  };

  const handleDownload = () => {
    const activeResult = activeTab === "replace" ? replaceResult : aboveResult;
    if (!activeResult) return;
    const a = document.createElement("a");
    a.href = activeResult;
    a.download = `transposed_${activeTab}_${file?.name || "output.png"}`;
    a.click();
  };

  const clearFile = () => {
    setFile(null);
    setDetectionId(null);
    setHybridRefining(false);
    setHybridApplied(false);
    setHybridStatus(null);
    setOriginalKey(null);
    setReplaceResult(null);
    setAboveResult(null);
    setError(null);
    setSelection(0);
    setTransposeUp(0);
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

  const handleSelect = (value: number) => {
    setSelection(value);
    if (value > 0) setTransposeUp(0);
    setReplaceResult(null);
    setAboveResult(null);
  };

  const handleTransposeUpSelect = (value: number) => {
    setTransposeUp(value);
    if (value > 0) setSelection(0);
    setReplaceResult(null);
    setAboveResult(null);
  };

  const activeResult = activeTab === "replace" ? replaceResult : aboveResult;

  return (
    <>
      <Head>
        <title>Capomatic</title>
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <meta name="description" content="Transpose chord sheets instantly" />
      </Head>

      <div style={{ minHeight: "100vh", backgroundColor: "#F5EDD8", fontFamily: "'Inter', 'Segoe UI', Arial, sans-serif", overflowX: "hidden" }}>

        {/* Nav */}
        <nav style={{
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
              Capo<span style={{ color: "#e05d00" }}>matic</span>
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <LangToggle />
            <LoginButton />
          </div>
        </nav>

        {/* Hamburger backdrop + side panel */}
        <div className={`hamburger-backdrop${menuOpen ? " open" : ""}`} onClick={() => setMenuOpen(false)} />
        <div className={`hamburger-menu${menuOpen ? " open" : ""}`} ref={menuRef}>
          {/* Panel header */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 20px", height: 52, borderBottom: "1px solid rgba(0,0,0,0.07)" }}>
            <span style={{ fontWeight: 800, fontSize: "0.96rem", color: "#1a1a2e", fontFamily: "Georgia, serif", fontStyle: "italic" }}>
              Capo<span style={{ color: "#e05d00" }}>matic</span>
            </span>
            <button onClick={() => setMenuOpen(false)} style={{ background: "none", border: "none", cursor: "pointer", padding: 4, display: "flex" }}>
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
            {user?.role === "admin" && (
              <Link href="/admin/dashboard" onClick={() => setMenuOpen(false)}
                style={{ display: "block", padding: "14px 24px", fontSize: "0.9rem", fontWeight: 600, color: "#1a1a2e", textDecoration: "none" }}>
                {t.admin}
              </Link>
            )}
            <button
              onClick={() => { setMenuOpen(false); setGuideStep(0); setGuideOpen(true); }}
              style={{ display: "block", width: "100%", textAlign: "left", background: "none", border: "none", cursor: "pointer", padding: "14px 24px", fontSize: "0.9rem", fontWeight: 600, color: "#1a1a2e" }}>
              {t.guide}
            </button>
          </nav>
        </div>

        {/* Upload-first hero */}
        {!file && (
          <section style={{
            maxWidth: 900,
            margin: "0 auto",
            padding: "54px 20px 26px",
            display: "grid",
            gridTemplateColumns: "minmax(0, 1fr)",
            justifyItems: "center",
            textAlign: "center",
          }}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: 7, marginBottom: 16, padding: "6px 10px", borderRadius: 999, background: "rgba(255,255,255,0.7)", border: "1px solid rgba(0,0,0,0.06)", color: "#7d6a57", fontSize: "0.72rem", fontWeight: 800 }}>
              <CheckCircle2 size={14} color="#1a9e50" />
              {t.workflowCaption}
            </div>
            <h1 style={{ maxWidth: 720, margin: "0 0 12px", fontSize: "clamp(2.45rem, 7vw, 4.35rem)", lineHeight: 0.98, fontWeight: 900, color: "#171923", letterSpacing: 0 }}>
              {t.heroHeadline}
            </h1>
            <p style={{ maxWidth: 610, margin: "0 auto 24px", fontSize: "clamp(1rem, 2.2vw, 1.16rem)", lineHeight: 1.55, color: "#5f5a52", fontWeight: 600 }}>
              {t.heroSubcopy}
            </p>
            <button
              onClick={() => fileInputRef.current?.click()}
              style={{
                display: "inline-flex", alignItems: "center", gap: 10,
                background: "linear-gradient(135deg, #e05d00, #c84b00)",
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
            <p style={{ margin: "10px 0 18px", fontSize: "0.78rem", color: "#8b8174", fontWeight: 700 }}>
              {t.heroTrust}
            </p>
            <label style={{
              display: "flex", alignItems: "flex-start", gap: 9,
              maxWidth: 360, cursor: "pointer", userSelect: "none",
              color: "#4f4a43", fontSize: "0.78rem", lineHeight: 1.35,
              padding: "10px 12px", borderRadius: 12,
              background: "rgba(255,255,255,0.5)", border: "1px solid rgba(0,0,0,0.05)",
            }}>
              <input
                type="checkbox"
                checked={useGptHybrid}
                onChange={e => setUseGptHybrid(e.target.checked)}
                style={{ marginTop: 2, accentColor: "#0b4ea2" }}
              />
              <span>
                <span style={{ display: "block", fontWeight: 800 }}>{t.gptHybridLabel}</span>
                <span style={{ display: "block", color: "#8a8174", fontSize: "0.72rem", marginTop: 2 }}>{t.gptHybridDesc}</span>
              </span>
            </label>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, flexWrap: "wrap", marginTop: 18, color: "#7d6a57", fontSize: "0.75rem", fontWeight: 800 }}>
              <span>{t.workflowStepUpload}</span>
              <ArrowRight size={13} />
              <span>{t.workflowStepTranspose}</span>
              <ArrowRight size={13} />
              <span>{t.workflowStepDownload}</span>
            </div>
            {error && (
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 14, color: "#d4183d", fontSize: "0.78rem", fontWeight: 600 }}>
                <AlertCircle size={13} />
                {error}
              </div>
            )}
          </section>
        )}

        {file && (
          <div style={{ textAlign: "center", padding: "30px 24px 0" }}>
            <h1 style={{ margin: "0 0 6px", fontSize: "clamp(1.8rem, 5vw, 2.5rem)", fontWeight: 900, color: "#1a1a2e", letterSpacing: 0 }}>
              {t.subtitle}
            </h1>
          </div>
        )}

        {/* Active info bar — shown once a file is loaded */}
        {file && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "24px 20px 16px", gap: 10 }}>
            {detecting && (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6, width: 260 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#e05d00", fontSize: "0.8rem", fontWeight: 600 }}>
                  <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
                  {t.detectingChords}
                </div>
                <div style={{ width: "100%", height: 4, background: "rgba(0,0,0,0.1)", borderRadius: 2, overflow: "hidden" }}>
                  <div style={{ width: `${detectProgress}%`, height: "100%", background: "linear-gradient(90deg,#e05d00,#c84b00)", borderRadius: 2, transition: "width 0.3s ease-out" }} />
                </div>
                <span style={{ fontSize: "0.7rem", color: "#aaa" }}>{(detectElapsed / 1000).toFixed(1)}s</span>
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
                    <span style={{ fontWeight: 700, color: "#e05d00", background: "rgba(224,93,0,0.08)", padding: "2px 10px", borderRadius: 20 }}>
                      {targetKey}
                    </span>
                    {semitones < 0 ? (
                      <span style={{ fontSize: "0.72rem", color: "#aaa", fontWeight: 600 }}>
                        {t.capo} {selection}
                      </span>
                    ) : (
                      <span style={{ fontSize: "0.72rem", color: "#aaa", fontWeight: 600 }}>
                        {t.transposeUpInfo(semitones)}
                      </span>
                    )}
                  </>
                )}
              </div>
            )}

            {!detecting && (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flexWrap: "wrap", gap: 8 }}>
                {detectionId && (
                  <button
                    onClick={handleGptHybridRefine}
                    disabled={hybridRefining || rendering}
                    style={{
                      border: "1.5px solid rgba(11,78,162,0.24)",
                      borderRadius: 20,
                      padding: "6px 14px",
                      fontSize: "0.75rem",
                      fontWeight: 800,
                      color: hybridApplied ? "#0b6b3a" : "#0b4ea2",
                      background: hybridApplied ? "rgba(11,107,58,0.08)" : "rgba(11,78,162,0.08)",
                      cursor: hybridRefining || rendering ? "not-allowed" : "pointer",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                    }}
                  >
                    {hybridRefining ? (
                      <><Loader2 size={13} style={{ animation: "spin 1s linear infinite" }} />{t.gptHybridRefining}</>
                    ) : hybridApplied ? t.gptHybridApplied : t.gptHybridButton}
                  </button>
                )}
                <button
                  onClick={clearFile}
                  style={{ background: "none", border: "1.5px solid rgba(0,0,0,0.15)", borderRadius: 20, padding: "5px 14px", fontSize: "0.75rem", fontWeight: 700, color: "#888", cursor: "pointer", letterSpacing: "0.04em" }}
                >
                  {t.changeSheet}
                </button>
                {hybridStatus && (
                  <span style={{ flexBasis: "100%", textAlign: "center", color: "#0b6b3a", fontSize: "0.72rem", fontWeight: 700 }}>
                    {hybridStatus}
                  </span>
                )}
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

        {/* Fretboard section — full width, no card, responsive padding via CSS */}
        <section className="fretboard-section">
          <GuitarFretboard capoFret={capoFret} onFretSelect={detectionId && !detecting ? handleSelect : undefined} />
        </section>

        {/* Capo selector — single section, responsive grid */}
        <div style={{ maxWidth: 560, margin: "16px auto 0", padding: "0 20px" }}>
          <div style={{ background: "rgba(255,255,255,0.55)", borderRadius: 16, padding: "14px 16px", border: "1px solid rgba(255,255,255,0.8)", backdropFilter: "blur(8px)", boxShadow: "0 2px 12px rgba(0,0,0,0.05)" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
              <div style={{ fontSize: "0.68rem", fontWeight: 700, color: "#a09070", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                {t.capoPosition}
              </div>
              {(!detectionId || detecting) && (
                <span style={{ fontSize: "0.68rem", color: "#c0b090", fontStyle: "italic" }}>{t.uploadFirst}</span>
              )}
            </div>
            <div className="capo-grid">
              {[0, 1, 2, 3, 4, 5, 6, 7].map(f => {
                const active = selection === f;
                return (
                  <button
                    key={f}
                    onClick={() => handleSelect(f)}
                    disabled={!detectionId || detecting}
                    style={{
                      padding: "10px 4px", borderRadius: 10,
                      border: active ? "2px solid #e05d00" : "1.5px solid rgba(0,0,0,0.1)",
                      background: active ? "linear-gradient(135deg, #e05d00, #c84b00)" : "rgba(255,255,255,0.6)",
                      color: active ? "white" : "#555",
                      fontWeight: 800, textAlign: "center" as const,
                      cursor: detectionId && !detecting ? "pointer" : "not-allowed",
                      opacity: detectionId && !detecting ? 1 : 0.4,
                      boxShadow: active ? "0 3px 10px rgba(224,93,0,0.3)" : "0 1px 3px rgba(0,0,0,0.06)",
                      transition: "all 0.18s",
                    }}
                  >
                    <div style={{ fontSize: "0.95rem" }}>{f === 0 ? t.open : f}</div>
                  </button>
                );
              })}
            </div>
          </div>

        </div>

        {/* Transpose-up selector — positive semitone shifts without capo info */}
        <div style={{ maxWidth: 560, margin: "12px auto 0", padding: "0 20px" }}>
          <div style={{ background: "rgba(255,255,255,0.45)", borderRadius: 16, padding: "14px 16px", border: "1px solid rgba(255,255,255,0.7)", backdropFilter: "blur(8px)", boxShadow: "0 2px 12px rgba(0,0,0,0.04)" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
              <div style={{ fontSize: "0.68rem", fontWeight: 700, color: "#a09070", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                {t.transposeUp}
              </div>
              {(!detectionId || detecting) && (
                <span style={{ fontSize: "0.68rem", color: "#c0b090", fontStyle: "italic" }}>{t.uploadFirst}</span>
              )}
            </div>
            <div className="capo-grid">
              {[0, 1, 2, 3, 4, 5, 6, 7].map(step => {
                const active = transposeUp === step;
                return (
                  <button
                    key={step}
                    onClick={() => handleTransposeUpSelect(step)}
                    disabled={!detectionId || detecting}
                    style={{
                      padding: "10px 4px", borderRadius: 10,
                      border: active ? "2px solid #0b4ea2" : "1.5px solid rgba(0,0,0,0.1)",
                      background: active ? "linear-gradient(135deg, #0b4ea2, #093b7a)" : "rgba(255,255,255,0.6)",
                      color: active ? "white" : "#555",
                      fontWeight: 800, textAlign: "center" as const,
                      cursor: detectionId && !detecting ? "pointer" : "not-allowed",
                      opacity: detectionId && !detecting ? 1 : 0.4,
                      boxShadow: active ? "0 3px 10px rgba(11,78,162,0.25)" : "0 1px 3px rgba(0,0,0,0.06)",
                      transition: "all 0.18s",
                    }}
                  >
                    <div style={{ fontSize: "0.95rem" }}>{step === 0 ? t.open : t.transposeUpShort(step)}</div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Generate button — below transpose selectors, when a shift is selected */}
        {detectionId && !detecting && semitones !== 0 && (
          <div style={{ maxWidth: 400, margin: "20px auto 0", padding: "0 20px" }}>
            <button
              onClick={handleConvert}
              disabled={rendering}
              style={{
                width: "100%", padding: "13px 20px", borderRadius: 12, border: "none",
                background: rendering ? "linear-gradient(135deg, #aaa, #999)" : "linear-gradient(135deg, #e05d00, #c84b00)",
                color: "white", fontSize: "0.9rem", fontWeight: 700,
                cursor: rendering ? "not-allowed" : "pointer",
                boxShadow: rendering ? "none" : "0 4px 16px rgba(224,93,0,0.28)",
                transition: "all 0.2s",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
              }}
            >
              {rendering ? (
                <><Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} />{t.rendering}</>
              ) : t.generateSheet(semitones)}
            </button>
          </div>
        )}

        {/* Result section */}
        {(replaceResult || aboveResult) && (
          <div ref={resultRef} style={{ maxWidth: 720, margin: "32px auto 48px", padding: "0 20px" }}>
            <div style={{ background: "rgba(230, 226, 219, 0.5)", borderRadius: 18, padding: "20px 20px 20px", border: "1px solid rgba(0,0,0,0.05)" }}>
              {/* Replace / Above toggle */}
              <div style={{ display: "flex", gap: 6, marginBottom: 16, background: "rgba(0,0,0,0.04)", borderRadius: 10, padding: 4 }}>
                {(["replace", "above"] as const).map(tab => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    style={{
                      flex: 1, padding: "10px 0", border: "none", cursor: "pointer",
                      borderRadius: 8,
                      background: activeTab === tab ? "white" : "transparent",
                      color: activeTab === tab ? "#3a4847" : "#999",
                      fontSize: "0.8rem", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase",
                      boxShadow: activeTab === tab ? "0 1px 4px rgba(0,0,0,0.08)" : "none",
                      transition: "all 0.18s",
                    }}
                  >
                    {tab === "replace" ? t.replace : t.above}
                  </button>
                ))}
              </div>
              {/* Sheet image */}
              <div style={{ position: "relative", borderRadius: 12, overflow: "hidden", background: "white" }}>
                {activeResult && (
                  <img
                    ref={imgRef}
                    src={activeResult}
                    alt={`Transposed chord sheet (${activeTab} mode)`}
                    style={{ width: "100%", display: "block", cursor: addModeActive ? "crosshair" : "default" }}
                    onLoad={e => setImgNaturalSize({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
                    onClick={handleImageClick}
                    onMouseMove={handleImageMouseMove}
                    onMouseLeave={handleImageMouseLeave}
                    onTouchMove={handleImageTouchMove}
                    onTouchEnd={handleImageTouchEnd}
                  />
                )}
                {/* Ghost bbox preview — snaps to nearest detected chord row */}
                {addModeActive && snapRow && hoverImgPos && imgNaturalSize && (
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
                {addModeActive && (
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
                      style={{ background: "linear-gradient(135deg,#e05d00,#c84b00)", border: "none", borderRadius: 8, padding: "7px 16px", fontSize: "0.8rem", fontWeight: 700, cursor: "pointer", color: "white", opacity: pendingChordText.trim() ? 1 : 0.5 }}
                    >Add</button>
                  </div>
                </div>
              )}
              {/* Download */}
              <button
                onClick={handleDownload}
                style={{
                  width: "100%", marginTop: 16, padding: "12px 0", borderRadius: 10, border: "none",
                  background: "linear-gradient(135deg, #1a9e50, #158040)",
                  color: "white", fontSize: "0.85rem", fontWeight: 700, cursor: "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center", gap: 7,
                  boxShadow: "0 3px 12px rgba(21,128,64,0.25)", transition: "all 0.18s",
                }}
              >
                <Download size={15} />
                {t.downloadPng}
              </button>

              <div style={{
                marginTop: 12,
                padding: "13px 14px",
                borderRadius: 12,
                background: "rgba(255,255,255,0.72)",
                border: "1px solid rgba(0,0,0,0.07)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 12,
                flexWrap: "wrap",
              }}>
                <div style={{ minWidth: 220, flex: "1 1 260px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 3, color: "#1a1a2e", fontSize: "0.82rem", fontWeight: 900 }}>
                    <CheckCircle2 size={15} color="#1a9e50" />
                    {t.savePromptTitle}
                  </div>
                  <p style={{ margin: 0, color: "#70685e", fontSize: "0.75rem", lineHeight: 1.4, fontWeight: 600 }}>
                    {isAuthenticated ? t.savePromptDescAuthed : t.savePromptDescAnon}
                  </p>
                </div>
                {isAuthenticated ? (
                  <Link
                    href="/history"
                    style={{
                      display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 7,
                      borderRadius: 10, padding: "9px 13px",
                      background: "#1a1a2e", color: "white", textDecoration: "none",
                      fontSize: "0.76rem", fontWeight: 900,
                    }}
                  >
                    {t.savePromptHistory}
                    <ArrowRight size={14} />
                  </Link>
                ) : (
                  <button
                    onClick={login}
                    style={{
                      display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 7,
                      borderRadius: 10, padding: "9px 13px",
                      border: "none", background: "#1a1a2e", color: "white",
                      cursor: "pointer", fontSize: "0.76rem", fontWeight: 900,
                    }}
                  >
                    {t.savePromptLogin}
                    <ArrowRight size={14} />
                  </button>
                )}
              </div>

              {/* Chord editor */}
              {editableChords.length > 0 && (
                <div style={{ marginTop: 20, paddingTop: 18, borderTop: "1px solid rgba(0,0,0,0.07)" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                    <span style={{ fontSize: "0.68rem", fontWeight: 700, color: "#a09070", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                      Detected Chords
                    </span>
                    {JSON.stringify(editableChords) !== JSON.stringify(detectedChords) && (
                      <button
                        onClick={() => { setEditableChords(detectedChords); setEditingIdx(null); setAddingChord(false); }}
                        style={{ background: "none", border: "1px solid rgba(0,0,0,0.15)", borderRadius: 20, padding: "3px 12px", fontSize: "0.7rem", fontWeight: 700, color: "#888", cursor: "pointer" }}
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
                        style={{ background: "none", border: "1.5px dashed rgba(0,0,0,0.18)", borderRadius: 20, padding: "4px 12px", fontSize: "0.78rem", fontWeight: 700, color: "#aaa", cursor: "pointer" }}
                      >
                        + Add
                      </button>
                    )}
                    {!addingChord && (
                      <button
                        onClick={() => setAddModeActive(true)}
                        style={{ background: "none", border: "1.5px dashed rgba(224,93,0,0.4)", borderRadius: 20, padding: "4px 12px", fontSize: "0.78rem", fontWeight: 700, color: "#e05d00", cursor: "pointer" }}
                      >
                        + Add at position
                      </button>
                    )}
                  </div>

                  {editableChords.some(c => c.bbox === null) && (
                    <p style={{ margin: "8px 0 0", fontSize: "0.7rem", color: "#e05d00", fontWeight: 600 }}>
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
          <span style={{ fontSize: "0.75rem", color: "#c0b090", fontWeight: 700, fontStyle: "italic", fontFamily: "Georgia, serif" }}>
            Capo<span style={{ color: "#e05d00" }}>matic</span>
          </span>
          <span style={{ fontSize: "0.7rem", color: "#ccc", fontWeight: 500 }}>{t.footerTagline}</span>
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
              <div style={{ background: "white", borderRadius: 20, width: "min(380px, 90vw)", padding: "40px 32px 28px", textAlign: "center", boxShadow: "0 16px 48px rgba(0,0,0,0.18)" }}
                onClick={e => e.stopPropagation()}>
                {/* Icon */}
                <div style={{ fontSize: "3rem", marginBottom: 20, color: "#e05d00", lineHeight: 1 }}>{step.icon}</div>
                {/* Title */}
                <h2 style={{ margin: "0 0 10px", fontSize: "1.3rem", fontWeight: 800, color: "#1a1a2e" }}>{step.label}</h2>
                {/* Description */}
                <p style={{ margin: "0 0 28px", fontSize: "0.88rem", color: "#999", lineHeight: 1.5 }}>{step.desc}</p>
                {/* Dot indicators */}
                <div style={{ display: "flex", justifyContent: "center", gap: 8, marginBottom: 28 }}>
                  {steps.map((_, i) => (
                    <div key={i} style={{ width: 10, height: 10, borderRadius: "50%", background: i === guideStep ? "#e05d00" : "#e8ddd0", transition: "background 0.2s" }} />
                  ))}
                </div>
                {/* Buttons */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 16 }}>
                  <button onClick={() => setGuideOpen(false)}
                    style={{ background: "none", border: "none", cursor: "pointer", padding: "12px 28px", fontSize: "0.9rem", fontWeight: 600, color: "#b0a8c0" }}>
                    {t.skip}
                  </button>
                  <button onClick={() => { if (isLast) setGuideOpen(false); else setGuideStep(guideStep + 1); }}
                    style={{ background: "#e05d00", color: "white", border: "none", cursor: "pointer", borderRadius: 12, padding: "12px 48px", fontSize: "0.95rem", fontWeight: 700, boxShadow: "0 4px 14px rgba(224,93,0,0.35)", transition: "all 0.2s" }}
                    onMouseEnter={e => (e.currentTarget.style.background = "#c84b00")}
                    onMouseLeave={e => (e.currentTarget.style.background = "#e05d00")}>
                    {isLast ? t.done : t.next}
                  </button>
                </div>
              </div>
            </div>
          );
        })()}

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
