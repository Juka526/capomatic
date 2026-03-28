import { useState } from 'react';

// ── Layout ──
const SVG_HEIGHT = 180;
const NUT_X = 36;
const FRET_WIDTH = 88;
const NUM_FRETS = 8;
const NECK_LEN = NUM_FRETS * FRET_WIDTH;   // 704
const BOARD_END = NUT_X + NECK_LEN;        // 740
const SVG_WIDTH = BOARD_END + 4;           // 744

// Fretboard taper — maximised vertical space for prominence
const TOP_NUT = 40;
const BOT_NUT = 150;
const TOP_END = 34;
const BOT_END = 156;

const SM_NUT = 8;
const SM_END = 10;

const SINGLE_MARKERS = [3, 5, 7];
const STRING_NAMES   = ['e', 'B', 'G', 'D', 'A', 'E'];
const SELECTABLE_FRETS = [1, 2, 3, 4, 5, 6, 7];

// ── Math helpers ──
function lerp(a: number, b: number, t: number) { return a + (b - a) * t; }
function nt(x: number) { return Math.max(0, Math.min(1, (x - NUT_X) / NECK_LEN)); }
function tY(x: number) { return lerp(TOP_NUT, TOP_END, nt(x)); }
function bY(x: number) { return lerp(BOT_NUT, BOT_END, nt(x)); }
function mY(x: number) { return (tY(x) + bY(x)) / 2; }
function fX(wire: number) { return NUT_X + wire * FRET_WIDTH; }
function fcX(fret: number) { return NUT_X + (fret - 0.5) * FRET_WIDTH; }

function snY(si: number) {
  return TOP_NUT + SM_NUT + si * (BOT_NUT - TOP_NUT - 2 * SM_NUT) / 5;
}
function sbY(si: number) {
  return TOP_END + SM_END + si * (BOT_END - TOP_END - 2 * SM_END) / 5;
}
function sY(si: number, x: number) { return lerp(snY(si), sbY(si), nt(x)); }
function sTk(si: number) { return 0.8 + si * 0.52; }

interface GuitarFretboardProps {
  capoFret: number | null;
  onFretSelect?: (fret: number) => void;
}

export function GuitarFretboard({ capoFret, onFretSelect }: GuitarFretboardProps) {
  const [hoveredFret, setHoveredFret] = useState<number | null>(null);

  const capoX = fcX(capoFret ?? 1);
  const capoVisible = capoFret !== null;
  const capoT = tY(capoX);
  const capoB = bY(capoX);

  return (
    <div>
      <svg
        viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
        style={{ display: 'block', width: '100%', height: 'auto' }}
      >
        <defs>
          <linearGradient id="fbWood" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#3d3838" />
            <stop offset="15%"  stopColor="#544C4D" />
            <stop offset="50%"  stopColor="#4a4344" />
            <stop offset="85%"  stopColor="#544C4D" />
            <stop offset="100%" stopColor="#3d3838" />
          </linearGradient>
          <linearGradient id="nutG" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#FEC66C" />
            <stop offset="50%"  stopColor="#e0ad50" />
            <stop offset="100%" stopColor="#FEC66C" />
          </linearGradient>
          <linearGradient id="capoBar" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%"   stopColor="#1c1c1c" />
            <stop offset="35%"  stopColor="#545454" />
            <stop offset="65%"  stopColor="#444444" />
            <stop offset="100%" stopColor="#1c1c1c" />
          </linearGradient>
          <linearGradient id="capoCap" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#383838" />
            <stop offset="100%" stopColor="#181818" />
          </linearGradient>
          <filter id="capoShd" x="-50%" y="-15%" width="200%" height="130%">
            <feDropShadow dx="4" dy="0" stdDeviation="5" floodColor="#000" floodOpacity="0.5" />
          </filter>
        </defs>

        {/* ── SHAPED HEADSTOCK ── */}
        <path
          d={`
            M ${NUT_X},${TOP_NUT - 4}
            L 18,${TOP_NUT - 10}
            Q 8,${TOP_NUT - 12} 4,${TOP_NUT - 6}
            Q 0,${TOP_NUT} 0,${TOP_NUT + 14}
            L 0,${BOT_NUT - 14}
            Q 0,${BOT_NUT} 4,${BOT_NUT + 6}
            Q 8,${BOT_NUT + 12} 18,${BOT_NUT + 10}
            L ${NUT_X},${BOT_NUT + 4}
            Z
          `}
          fill="#3a4847"
        />

        {/* ── FRETBOARD TRAPEZOID ── */}
        <polygon
          points={`
            ${NUT_X},${TOP_NUT}
            ${BOARD_END},${TOP_END}
            ${BOARD_END},${BOT_END}
            ${NUT_X},${BOT_NUT}
          `}
          fill="url(#fbWood)"
        />

        {/* Binding lines */}
        <line x1={NUT_X} y1={TOP_NUT} x2={BOARD_END} y2={TOP_END}
          stroke="#FEC66C" strokeWidth={2} opacity={0.35} />
        <line x1={NUT_X} y1={BOT_NUT} x2={BOARD_END} y2={BOT_END}
          stroke="#FEC66C" strokeWidth={2} opacity={0.35} />

        {/* Position dot markers */}
        {SINGLE_MARKERS.map(fret => {
          const x = fcX(fret);
          return <circle key={fret} cx={x} cy={mY(x)} r={6} fill="#3a3234" opacity={0.6} />;
        })}

        {/* Fret wires */}
        {Array.from({ length: NUM_FRETS }, (_, i) => {
          const fx = fX(i + 1);
          return (
            <line key={i} x1={fx} y1={tY(fx)} x2={fx} y2={bY(fx)}
              stroke="#FEC66C" strokeWidth={2.8} strokeLinecap="round" />
          );
        })}

        {/* Nut */}
        <rect x={NUT_X - 4} y={TOP_NUT - 1} width={6}
          height={BOT_NUT - TOP_NUT + 2} fill="url(#nutG)" rx={2} />

        {/* Strings */}
        {Array.from({ length: 6 }, (_, si) => (
          <line key={si}
            x1={4}          y1={sY(si, 4)}
            x2={BOARD_END}  y2={sY(si, BOARD_END)}
            stroke={si < 3 ? '#c0bbb0' : '#9a9590'}
            strokeWidth={sTk(si)}
          />
        ))}

        {/* String name circles — on top of nut */}
        {STRING_NAMES.map((name, si) => {
          const cy = snY(si);
          return (
            <g key={`label-${si}`}>
              <circle cx={NUT_X} cy={cy} r={10} fill="#2e3c3b" />
              <text x={NUT_X} y={cy} textAnchor="middle" dominantBaseline="central"
                fill="#FFFFFF" fontSize={10} fontWeight="800"
              >{name.toUpperCase()}</text>
            </g>
          );
        })}

        {/* Fret number labels */}
        {[1, 2, 3, 4, 5, 6, 7, 8].map(fret => (
          <text key={fret} x={fcX(fret)} y={26} textAnchor="middle"
            fill={
              capoFret === fret ? '#e05d00'
              : [3, 5, 7].includes(fret) ? '#777'
              : fret === 8 ? '#bbb'
              : '#999'
            }
            fontSize={[3, 5, 7].includes(fret) ? 13 : 11}
            fontWeight={[3, 5, 7].includes(fret) ? '700' : '600'}
            opacity={fret === 8 ? 0.7 : 1}
          >{fret}</text>
        ))}

        {/* ── CLICK / HOVER ZONES (frets 1-7 only, fret 8 display-only) ── */}
        {onFretSelect && SELECTABLE_FRETS.map(fret => {
          const x0 = fX(fret - 1), x1 = fX(fret);
          return (
            <polygon key={fret}
              points={`${x0},${tY(x0)} ${x1},${tY(x1)} ${x1},${bY(x1)} ${x0},${bY(x0)}`}
              fill={
                capoFret === fret   ? 'rgba(224,93,0,0.10)'
                : hoveredFret === fret ? 'rgba(224,93,0,0.05)'
                : 'transparent'
              }
              style={{ cursor: 'pointer' }}
              onClick={() => onFretSelect(fret)}
              onMouseEnter={() => setHoveredFret(fret)}
              onMouseLeave={() => setHoveredFret(null)}
            />
          );
        })}

        {/* ── CAPO ── */}
        <g style={{
          transform: `translateX(${capoX}px)`,
          transition: 'transform 0.65s cubic-bezier(0.34, 1.4, 0.64, 1)',
          opacity: capoVisible ? 1 : 0,
          pointerEvents: 'none',
        }}>
          {/* Top clamp */}
          <rect x={-5} y={capoT - 20} width={10} height={28} rx={4}
            fill="url(#capoCap)" filter="url(#capoShd)" />
          <rect x={-12} y={capoT - 23} width={24} height={12} rx={4}
            fill="#242424" filter="url(#capoShd)" />
          <rect x={-8} y={capoT - 21} width={16} height={8} rx={3} fill="#3c3c3c" />
          <circle cx={0} cy={capoT - 17} r={2.8} fill="#181818" />
          <line x1={-2} y1={capoT - 17} x2={2} y2={capoT - 17}
            stroke="#555" strokeWidth={1.5} />

          {/* Main bar */}
          <rect x={-7} y={capoT} width={14} height={capoB - capoT} rx={5}
            fill="url(#capoBar)" filter="url(#capoShd)" />
          <rect x={-3} y={capoT + 4} width={4} height={capoB - capoT - 8} rx={2}
            fill="rgba(255,255,255,0.12)" />
          {/* Rubber pads */}
          {Array.from({ length: 6 }, (_, si) => {
            const sy = sY(si, capoX);
            return (
              <g key={si}>
                <rect x={-5} y={sy - 3} width={10} height={6} rx={3} fill="#0c0c0c" />
                <rect x={-3} y={sy - 1.5} width={4} height={3} rx={1.5} fill="#1c1c1c" />
              </g>
            );
          })}

          {/* Bottom clamp */}
          <rect x={-5} y={capoB - 8} width={10} height={28} rx={4}
            fill="url(#capoCap)" filter="url(#capoShd)" />
          <rect x={-12} y={capoB + 11} width={24} height={12} rx={4}
            fill="#242424" filter="url(#capoShd)" />
          <rect x={-8} y={capoB + 13} width={16} height={8} rx={3} fill="#3c3c3c" />
          <circle cx={0} cy={capoB + 17} r={2.8} fill="#181818" />

          {capoFret !== null && (
            <text x={20} y={mY(capoX)} textAnchor="start" dominantBaseline="middle"
              fill="#e05d00" fontSize={11} fontWeight="800">{capoFret}</text>
          )}
        </g>
      </svg>
    </div>
  );
}
