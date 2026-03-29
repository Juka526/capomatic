import { useState, useRef, useCallback, useEffect, useMemo } from "react";
import { Upload, Download, Loader2, AlertCircle } from "lucide-react";
import Head from "next/head";
import Link from "next/link";
import LoginButton from "@/components/LoginButton";
import { useAuth } from "@/components/AuthProvider";
import { useLang, LangToggle } from "@/components/LangProvider";
import { getAccessToken } from "@/lib/auth0";
import { GuitarFretboard } from "@/components/GuitarFretboard";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const MAX_FILE_SIZE = 8 * 1024 * 1024;
const ESTIMATED_DETECT_MS = 13000;
const KEY_NAMES = ["C","Db","D","Eb","E","F","F#","G","Ab","A","Bb","B"];

function computeTargetKey(originalKey: string, semitones: number): string {
  const idx = KEY_NAMES.indexOf(originalKey);
  if (idx === -1) return originalKey;
  return KEY_NAMES[((idx + semitones) % 12 + 12) % 12];
}

export default function Home() {
  const { isAuthenticated, user } = useAuth();
  const { t } = useLang();

  const [file, setFile] = useState<File | null>(null);
  const [selection, setSelection] = useState<number>(0); // 0 to 7

  const [detectionId, setDetectionId] = useState<string | null>(null);
  const [originalKey, setOriginalKey] = useState<string | null>(null);
  const [detecting, setDetecting] = useState(false);
  const [detectProgress, setDetectProgress] = useState(0);
  const [detectElapsed, setDetectElapsed] = useState(0);

  const [replaceResult, setReplaceResult] = useState<string | null>(null);
  const [aboveResult, setAboveResult] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"replace" | "above">("replace");
  const [rendering, setRendering] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [guideOpen, setGuideOpen] = useState(false);
  const [guideStep, setGuideStep] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

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
  const semitones = -selection;

  const targetKey = useMemo(() => {
    if (!originalKey || semitones === 0) return originalKey;
    return computeTargetKey(originalKey, semitones);
  }, [originalKey, semitones]);

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
    setOriginalKey(null);
    setReplaceResult(null);
    setAboveResult(null);
    try {
      const formData = new FormData();
      formData.append("image", f);
      const res = await fetch(`${API_URL}/detect`, { method: "POST", body: formData });
      if (!res.ok) throw new Error((await res.text()) || `Server error (${res.status})`);
      const data = await res.json();
      setDetectProgress(100);
      setDetectionId(data.detection_id);
      setOriginalKey(data.original_key);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedConnect);
    } finally {
      setDetecting(false);
    }
  }, [t]);

  const handleFile = useCallback((f: File) => {
    if (!f.type.match(/^image\/(png|jpeg)$/)) { setError(t.onlyPngJpg); return; }
    if (f.size > MAX_FILE_SIZE) { setError(t.fileTooLarge); return; }
    setFile(f);
    setError(null);
    setSelection(0);
    runDetection(f);
  }, [runDetection, t]);

  const handleConvert = async () => {
    if (!detectionId || selection === 0) return;
    setRendering(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("detection_id", detectionId);
      formData.append("semitones", semitones.toString());
      const res = await fetch(`${API_URL}/render`, { method: "POST", body: formData });
      if (!res.ok) throw new Error((await res.text()) || `Server error (${res.status})`);
      const data = await res.json();
      setReplaceResult(data.replace_image);
      setAboveResult(data.above_image);
      setActiveTab("replace");
      if (isAuthenticated && file) {
        saveJobInBackground(file, semitones, "replace");
        saveJobInBackground(file, semitones, "above");
      }
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 150);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedConnect);
    } finally {
      setRendering(false);
    }
  };

  const saveJobInBackground = async (f: File, semi: number, mode: string) => {
    try {
      const token = await getAccessToken();
      if (!token) return;
      const form = new FormData();
      form.append("image", f);
      form.append("semitones", semi.toString());
      form.append("mode", mode);
      form.append("song_name", f.name.replace(/\.[^.]+$/, ""));
      await fetch(`${API_URL}/api/overlay`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form });
    } catch {}
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
    setOriginalKey(null);
    setReplaceResult(null);
    setAboveResult(null);
    setError(null);
    setSelection(0);
    if (fileInputRef.current) fileInputRef.current.value = "";
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleSelect = (value: number) => {
    setSelection(value);
    setReplaceResult(null);
    setAboveResult(null);
  };

  const activeResult = activeTab === "replace" ? replaceResult : aboveResult;

  return (
    <>
      <Head>
        <title>TransChord</title>
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
              Trans<span style={{ color: "#e05d00" }}>Chord</span>
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
              Trans<span style={{ color: "#e05d00" }}>Chord</span>
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

        {/* Hero */}
        <div style={{ textAlign: "center", padding: "44px 24px 0" }}>
          <h1 style={{ margin: "0 0 6px", fontSize: "clamp(2rem, 5vw, 2.8rem)", fontWeight: 900, fontStyle: "italic", fontFamily: "Georgia, serif", letterSpacing: "-0.02em", color: "#1a1a2e" }}>
            Trans<span style={{ color: "#e05d00" }}>Chord</span>
          </h1>
          <p style={{ margin: 0, fontSize: "0.84rem", color: "#aaa", fontWeight: 500, letterSpacing: "0.03em" }}>
            {t.subtitle}
          </p>
        </div>

        {/* Upload zone — only shown before a file is selected */}
        {!file && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "28px 0 20px", gap: 10 }}>
            <button
              onClick={() => fileInputRef.current?.click()}
              style={{
                display: "flex", alignItems: "center", gap: 12,
                background: "linear-gradient(135deg, #8A6958 0%, #7a5c4c 100%)",
                border: "none", cursor: "pointer",
                borderRadius: 14, padding: "14px 32px",
                color: "white", fontSize: "0.9rem", fontWeight: 700,
                boxShadow: "0 4px 16px rgba(138,105,88,0.35)",
                transition: "all 0.25s ease",
              }}
              onMouseEnter={e => { e.currentTarget.style.transform = "scale(1.03)"; e.currentTarget.style.background = "linear-gradient(135deg, #7a5c4c 0%, #6b4f40 100%)"; }}
              onMouseLeave={e => { e.currentTarget.style.transform = "scale(1)"; e.currentTarget.style.background = "linear-gradient(135deg, #8A6958 0%, #7a5c4c 100%)"; }}
            >
              <Upload size={20} color="white" strokeWidth={2} />
              {t.uploadYourScore}
            </button>
            {error && (
              <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#d4183d", fontSize: "0.78rem", fontWeight: 600 }}>
                <AlertCircle size={13} />
                {error}
              </div>
            )}
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
                {selection > 0 && targetKey && (
                  <>
                    <span style={{ color: "#ccc" }}>→</span>
                    <span style={{ fontWeight: 700, color: "#e05d00", background: "rgba(224,93,0,0.08)", padding: "2px 10px", borderRadius: 20 }}>
                      {targetKey}
                    </span>
                    <span style={{ fontSize: "0.72rem", color: "#aaa", fontWeight: 600 }}>
                      {t.capo} {selection}
                    </span>
                  </>
                )}
              </div>
            )}

            {!detecting && (
              <button
                onClick={clearFile}
                style={{ background: "none", border: "1.5px solid rgba(0,0,0,0.15)", borderRadius: 20, padding: "5px 14px", fontSize: "0.75rem", fontWeight: 700, color: "#888", cursor: "pointer", letterSpacing: "0.04em" }}
              >
                {t.changeSheet}
              </button>
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
            <div style={{ fontSize: "0.68rem", fontWeight: 700, color: "#a09070", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 10 }}>
              {t.capoPosition}
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

          {(!detectionId || detecting) && (
            <p style={{ textAlign: "center", fontSize: "0.72rem", color: "#c0b090", fontStyle: "italic", marginTop: 10 }}>
              {t.uploadFirst}
            </p>
          )}
        </div>

        {/* Generate button — below capo selector, when capo is selected */}
        {detectionId && !detecting && selection > 0 && (
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
              ) : t.generateSheet(selection)}
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
              <div style={{ borderRadius: 12, overflow: "hidden", background: "white" }}>
                {activeResult && <img src={activeResult} alt={`Transposed chord sheet (${activeTab} mode)`} style={{ width: "100%", display: "block" }} />}
              </div>
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
            </div>
          </div>
        )}


        {/* Footer */}
        <footer style={{ borderTop: "1px solid rgba(0,0,0,0.06)", padding: "18px 24px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
          <span style={{ fontSize: "0.75rem", color: "#c0b090", fontWeight: 700, fontStyle: "italic", fontFamily: "Georgia, serif" }}>
            Trans<span style={{ color: "#e05d00" }}>Chord</span>
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
