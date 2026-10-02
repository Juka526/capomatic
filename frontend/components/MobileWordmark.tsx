import { useCallback, useEffect, useRef } from "react";
import { LETTER_PATHS, LOGO_VIEWBOX, M_INDEX } from "@/lib/logo-geometry.mjs";
import { REST_M_PATH, pluckFrame } from "@/lib/logo-pluck.mjs";

const INK = "#1a1a2e";
const ACCENT = "#E05D00";

/**
 * Capomatic wordmark for the mobile top bar. The m is a plucked string: it
 * vibrates once on first load and again on each tap, unless the user prefers
 * reduced motion. Outlines are baked in (no runtime font loading).
 */
export function MobileWordmark({ height = 23 }: { height?: number }) {
  const mRef = useRef<SVGPathElement>(null);
  const frameRef = useRef<number | null>(null);

  const stop = useCallback(() => {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    frameRef.current = null;
  }, []);

  const pluck = useCallback(() => {
    const path = mRef.current;
    if (!path || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    // The mobile bar is display:none on desktop; don't animate an invisible logo.
    if (path.getClientRects().length === 0) return;
    stop();
    let start: number | null = null;
    const step = (now: number) => {
      if (start === null) start = now;
      const d = pluckFrame((now - start) / 1000);
      if (d === null) {
        path.setAttribute("d", REST_M_PATH);
        frameRef.current = null;
        return;
      }
      path.setAttribute("d", d);
      frameRef.current = requestAnimationFrame(step);
    };
    frameRef.current = requestAnimationFrame(step);
  }, [stop]);

  useEffect(() => {
    pluck();
    return stop;
  }, [pluck, stop]);

  return (
    <svg
      viewBox={LOGO_VIEWBOX}
      role="img"
      aria-label="Capomatic"
      onClick={pluck}
      style={{ display: "block", height, width: "auto", overflow: "visible", cursor: "pointer" }}
    >
      {LETTER_PATHS.map((d, i) => (
        i === M_INDEX
          ? <path key={i} ref={mRef} d={REST_M_PATH} fill={ACCENT} data-m="" />
          : <path key={i} d={d ?? ""} fill={INK} />
      ))}
    </svg>
  );
}
