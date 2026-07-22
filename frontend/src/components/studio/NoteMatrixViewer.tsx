import React, { useState } from 'react'

interface NoteEvent {
  stringIdx: number
  fret: number
  bar: number
  color: string
}

interface NoteMatrixProps {
  rawTab: string
}

const STRINGS = [
  { name: 'e', color: '#007aff' },
  { name: 'B', color: '#ff9500' },
  { name: 'G', color: '#af52de' },
  { name: 'D', color: '#34c759' },
  { name: 'A', color: '#ff2d55' },
  { name: 'E', color: '#5856d6' }
]

export default function NoteMatrixViewer({ rawTab }: NoteMatrixProps) {
  const [activeView, setActiveView] = useState<'matrix' | 'spectrogram' | 'ascii'>('matrix')

  const sampleEvents: NoteEvent[] = [
    { stringIdx: 1, fret: 6, bar: 0.1, color: '#ff9500' },
    { stringIdx: 2, fret: 7, bar: 0.1, color: '#af52de' },
    { stringIdx: 4, fret: 6, bar: 0.1, color: '#ff2d55' },
    { stringIdx: 3, fret: 8, bar: 0.5, color: '#34c759' },
    { stringIdx: 1, fret: 8, bar: 0.7, color: '#ff9500' },
    { stringIdx: 2, fret: 7, bar: 0.7, color: '#af52de' },
    { stringIdx: 3, fret: 8, bar: 1.0, color: '#34c759' },
    { stringIdx: 1, fret: 6, bar: 1.2, color: '#ff9500' },
    { stringIdx: 2, fret: 7, bar: 1.2, color: '#af52de' },
    { stringIdx: 0, fret: 8, bar: 2.0, color: '#007aff' },
    { stringIdx: 1, fret: 6, bar: 2.0, color: '#ff9500' },
    { stringIdx: 2, fret: 7, bar: 2.0, color: '#af52de' }
  ]

  const totalBars = 4
  const gridWidth = 720

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* View Mode Selector */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--color-muted)', fontWeight: 600 }}>
          Score View
        </span>

        <div style={{ display: 'flex', gap: '20px' }}>
          {(['matrix', 'spectrogram', 'ascii'] as const).map((view) => (
            <button
              key={view}
              onClick={() => setActiveView(view)}
              style={{
                background: 'none',
                border: 'none',
                borderBottom: activeView === view ? '2px solid var(--color-ink)' : '2px solid transparent',
                fontSize: '0.7rem',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                color: activeView === view ? 'var(--color-ink)' : 'var(--color-muted)',
                fontWeight: activeView === view ? 600 : 400,
                cursor: 'pointer',
                paddingBottom: '3px'
              }}
            >
              {view === 'matrix' && 'Visual Score'}
              {view === 'spectrogram' && 'Audio Spectrum'}
              {view === 'ascii' && 'Text Tab'}
            </button>
          ))}
        </div>
      </div>

      {/* 1. VISUAL SCORE (WIDE GRID) */}
      {activeView === 'matrix' && (
        <div style={{
          background: '#fcfcfd',
          border: '1px solid var(--color-border)',
          borderRadius: '8px',
          padding: '20px 24px',
          overflowX: 'auto'
        }}>
          <div style={{ position: 'relative', width: '100%', minWidth: `${gridWidth}px` }}>
            <svg viewBox={`0 0 ${gridWidth} 175`} style={{ width: '100%', display: 'block' }}>
              {/* Measure Lines */}
              {Array.from({ length: totalBars + 1 }).map((_, barIdx) => {
                const x = 35 + (barIdx * ((gridWidth - 45) / totalBars))
                return (
                  <g key={`bar-${barIdx}`}>
                    <line x1={x} y1="10" x2={x} y2="148" stroke="#e0e0e0" strokeWidth={barIdx === 0 || barIdx === totalBars ? "1.5" : "1"} strokeDasharray={barIdx === 0 || barIdx === totalBars ? "none" : "2 2"} />
                    <text x={x} y="166" fontSize="9" fill="var(--color-muted)" textAnchor="middle" fontFamily="sans-serif">
                      Measure {barIdx + 1}
                    </text>
                  </g>
                )
              })}

              {/* 6 Guitar Strings */}
              {STRINGS.map((st, sIdx) => {
                const y = 20 + (sIdx * 23.5)
                return (
                  <g key={`string-line-${sIdx}`}>
                    <text x="14" y={y + 4} fontSize="11" fontWeight="600" fill="var(--color-ink)" textAnchor="middle" fontFamily="sans-serif">
                      {st.name}
                    </text>
                    <line x1="30" y1={y} x2={gridWidth - 10} y2={y} stroke="#e8e8ed" strokeWidth="1" />
                  </g>
                )
              })}

              {/* Note Events */}
              {sampleEvents.map((evt, idx) => {
                const x = 35 + (evt.bar * ((gridWidth - 45) / totalBars))
                const y = 20 + (evt.stringIdx * 23.5)

                return (
                  <g key={`evt-${idx}`}>
                    <rect x={x - 9} y={y - 9} width="18" height="18" rx="4" fill="#ffffff" stroke={evt.color} strokeWidth="1.5" />
                    <text x={x} y={y + 3.5} fontSize="9.5" fontWeight="700" fill={evt.color} textAnchor="middle" fontFamily="sans-serif">
                      {evt.fret}
                    </text>
                  </g>
                )
              })}
            </svg>
          </div>
        </div>
      )}

      {/* 2. AUDIO SPECTRUM */}
      {activeView === 'spectrogram' && (
        <div style={{ background: '#121214', borderRadius: '8px', padding: '16px', border: '1px solid var(--color-border)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.65rem', color: '#8e8e93', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            <span>Frequency Energy Heatmap</span>
            <span>0.0s – 8.0s</span>
          </div>
          <div style={{
            height: '140px',
            width: '100%',
            borderRadius: '4px',
            background: 'linear-gradient(90deg, #0d0887 0%, #6a00a8 25%, #b12a90 50%, #e16462 75%, #fca636 100%)',
            opacity: 0.95
          }} />
        </div>
      )}

      {/* 3. TEXT TAB */}
      {activeView === 'ascii' && (
        <div style={{
          background: '#fcfcfd',
          border: '1px solid var(--color-border)',
          borderRadius: '8px',
          padding: '20px',
          fontFamily: 'Consolas, Monaco, monospace',
          fontSize: '0.82rem',
          lineHeight: '1.5',
          color: 'var(--color-ink)',
          whiteSpace: 'pre',
          overflowX: 'auto'
        }}>
          {rawTab || `e|--12--10--------------------|\nB|----------12--10------------|\nG|------------------12--9--7~-|\nD|----------------------------|\nA|----------------------------|\nE|----------------------------|`}
        </div>
      )}
    </div>
  )
}