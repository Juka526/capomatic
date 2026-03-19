import { useState, useRef, useCallback, useEffect, useMemo } from "react";
import { Upload, Download, Music, Loader2, X } from "lucide-react";
import Head from "next/head";

const API_URL = "http://localhost:8000";
const MAX_FILE_SIZE = 8 * 1024 * 1024; // 8MB
const ESTIMATED_DETECT_MS = 13000;

// Must match backend/chords/transpose.py _KEY_NAMES
const KEY_NAMES = ["C","Db","D","Eb","E","F","F#","G","Ab","A","Bb","B"];

function computeTargetKey(originalKey: string, semitones: number): string {
  const idx = KEY_NAMES.indexOf(originalKey);
  if (idx === -1) return originalKey;
  return KEY_NAMES[((idx + semitones) % 12 + 12) % 12];
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [semitones, setSemitones] = useState(0);

  // Detection state
  const [detectionId, setDetectionId] = useState<string | null>(null);
  const [originalKey, setOriginalKey] = useState<string | null>(null);
  const [detecting, setDetecting] = useState(false);
  const [detectProgress, setDetectProgress] = useState(0);
  const [detectElapsed, setDetectElapsed] = useState(0);

  // Render state
  const [replaceResult, setReplaceResult] = useState<string | null>(null);
  const [aboveResult, setAboveResult] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"replace" | "above">("replace");
  const [rendering, setRendering] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Client-side target key computation
  const targetKey = useMemo(() => {
    if (!originalKey || semitones === 0) return originalKey;
    return computeTargetKey(originalKey, semitones);
  }, [originalKey, semitones]);

  // Detection progress bar
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

  // Auto-detect on file select
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

      const res = await fetch(`${API_URL}/detect`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Server error (${res.status})`);
      }

      const data = await res.json();
      setDetectProgress(100);
      setDetectionId(data.detection_id);
      setOriginalKey(data.original_key);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to connect to server."
      );
    } finally {
      setDetecting(false);
    }
  }, []);

  const handleFile = useCallback((f: File) => {
    if (!f.type.match(/^image\/(png|jpeg)$/)) {
      setError("Only PNG and JPG files are supported.");
      return;
    }
    if (f.size > MAX_FILE_SIZE) {
      setError("File size exceeds 8MB limit.");
      return;
    }
    setFile(f);
    setError(null);
    runDetection(f);
  }, [runDetection]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  const handleConvert = async () => {
    if (!detectionId) return;
    setRendering(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("detection_id", detectionId);
      formData.append("semitones", semitones.toString());

      const res = await fetch(`${API_URL}/render`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Server error (${res.status})`);
      }

      const data = await res.json();
      setReplaceResult(data.replace_image);
      setAboveResult(data.above_image);
      setActiveTab("replace");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to connect to server."
      );
    } finally {
      setRendering(false);
    }
  };

  const activeResult = activeTab === "replace" ? replaceResult : aboveResult;

  const handleDownload = () => {
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
    setSemitones(0);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <>
      <Head>
        <title>TransChord</title>
        <meta name="description" content="Transpose chord sheets instantly" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white border-b border-gray-200">
          <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-3">
            <Music className="w-6 h-6 text-blue-600" />
            <h1 className="text-xl font-semibold text-gray-900">TransChord</h1>
          </div>
        </header>

        <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
          {/* Upload Section */}
          <section className="bg-white rounded-2xl shadow-sm p-6">
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-4">
              Upload
            </h2>

            {!file ? (
              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
                  dragOver
                    ? "border-blue-500 bg-blue-50/50"
                    : "border-gray-300 hover:border-blue-500 hover:bg-blue-50/50"
                }`}
              >
                <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-700 font-medium">Click or drag file here</p>
                <p className="text-gray-500 text-sm mt-1">PNG, JPG (max 8MB)</p>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <Music className="w-5 h-5 text-blue-600 shrink-0" />
                    <span className="text-gray-900 text-sm truncate">{file.name}</span>
                    <span className="text-gray-500 text-xs shrink-0">
                      ({(file.size / 1024 / 1024).toFixed(1)} MB)
                    </span>
                  </div>
                  <button onClick={clearFile} className="text-gray-400 hover:text-gray-600 p-1">
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Detection progress */}
                {detecting && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Detecting chords...
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                        style={{ width: `${detectProgress}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>{Math.round(detectProgress)}%</span>
                      <span>{(detectElapsed / 1000).toFixed(1)}s</span>
                    </div>
                  </div>
                )}

                {/* Detection complete — show key */}
                {detectionId && originalKey && !detecting && (
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-gray-600">Detected key:</span>
                    <span className="font-semibold text-blue-700 bg-blue-50 px-2.5 py-0.5 rounded-full">
                      {originalKey}
                    </span>
                  </div>
                )}
              </div>
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFile(f);
              }}
            />
          </section>

          {/* Options Section — only show after detection */}
          {detectionId && !detecting && (
            <section className="bg-white rounded-2xl shadow-sm p-6 space-y-6">
              <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
                Options
              </h2>

              {/* Capo / Semitones Slider */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-gray-700">
                    Capo / Semitones
                  </label>
                  <span
                    className={`text-sm font-semibold px-2.5 py-0.5 rounded-full ${
                      semitones === 0
                        ? "bg-gray-100 text-gray-600"
                        : "bg-orange-100 text-orange-700"
                    }`}
                  >
                    {semitones === 0 ? "0" : `${semitones} (Capo ${-semitones})`}
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="11"
                  value={-semitones}
                  onChange={(e) => {
                    setSemitones(-Number(e.target.value));
                    // Clear previous results when semitones change
                    setReplaceResult(null);
                    setAboveResult(null);
                  }}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>0</span>
                  <span>-11 (Capo 11)</span>
                </div>
              </div>

              {/* Key info */}
              {originalKey && semitones !== 0 && targetKey && (
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <span>Key:</span>
                  <span className="font-semibold">{originalKey}</span>
                  <span>→</span>
                  <span className="font-semibold text-blue-700">{targetKey}</span>
                </div>
              )}

              {/* Convert Button */}
              <button
                onClick={handleConvert}
                disabled={rendering || semitones === 0}
                className={`w-full py-3 px-4 rounded-lg text-sm font-medium transition-colors ${
                  rendering || semitones === 0
                    ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                    : "bg-blue-600 text-white hover:bg-blue-700"
                }`}
              >
                {rendering ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Rendering...
                  </span>
                ) : (
                  "Convert"
                )}
              </button>

              {error && (
                <p className="text-red-600 text-sm text-center">{error}</p>
              )}
            </section>
          )}

          {/* Error outside of sections */}
          {error && !detectionId && (
            <p className="text-red-600 text-sm text-center">{error}</p>
          )}

          {/* Result Section */}
          {(replaceResult || aboveResult) && (
            <section className="bg-white rounded-2xl shadow-sm p-6 space-y-4">
              <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
                Result
              </h2>

              {/* Tab Toggle */}
              <div className="flex gap-2">
                {(["replace", "above"] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`py-2 px-4 rounded-lg text-sm font-medium transition-colors flex-1 ${
                      activeTab === tab
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    {tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </button>
                ))}
              </div>

              {/* Image */}
              <div className="border border-gray-200 rounded-xl overflow-hidden">
                {activeResult && (
                  <img
                    src={activeResult}
                    alt={`Transposed chord sheet (${activeTab} mode)`}
                    className="w-full"
                  />
                )}
              </div>

              {/* Download */}
              <button
                onClick={handleDownload}
                className="w-full py-3 px-4 rounded-lg text-sm font-medium bg-green-600 text-white hover:bg-green-700 transition-colors flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" />
                Download
              </button>
            </section>
          )}
        </main>
      </div>
    </>
  );
}
