import React from 'react'

interface NotePosition {
  stringIdx: number // 0 (High E) to 5 (Low E)
  fret: number      // 0 to 15
  label?: string
}

interface FretboardProps {
  activeNotes?: NotePosition[]
}

const STRING_NAMES = ['e', 'B', 'G', 'D', 'A', 'E']
const FRET_MARKERS = [3, 5, 7, 9, 12, 15]

export default function FretboardVisualizer({ activeNotes = [] }: FretboardProps) {
  const fretCount = 15

  return (
    <div style={{
      width: '100%',
      padding: '16px 20px',
      background: '#fbfbfd',
      border: '1px solid var(--color-border)',
      borderRadius: '8px',
      marginTop: '16px'
    }}>
      <div style={{
        display: 'flex',
        justify: 'space-between',
        alignItems: 'center',
        marginBottom: '12px'
      }}>
        <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.15em', color: 'var(--color-muted)', fontWeight: 600 }}>
          Interactive Fretboard Map
        </span>
        <span style={{ fontSize: '0.65rem', color: 'var(--color-muted)', letterSpacing: '0.05em' }}>
          Standard Tuning (E2-E4)
        </span>
      </div>

      <div style={{ position: 'relative', width: '100%', overflowX: 'auto', paddingBottom: '8px' }}>
        <svg viewBox="0 0 800 120" style={{ width: '100%', minWidth: '600px', display: 'block' }}>
          {/* Fretboard Wood Base */}
          <rect x="30" y="15" width="750" height="90" fill="#f2f0eb" rx="2" stroke="var(--color-border)" strokeWidth="1" />

          {/* Fret Lines & Inlay Markers */}
          {Array.from({ length: fretCount + 1 }).map((_, i) => {
            const x = 30 + (i * (750 / fretCount))
            const isFretMarker = FRET_MARKERS.includes(i)
            const isDoubleMarker = i === 12

            return (
              <g key={`fret-${i}`}>
                {/* Silver Fret Wire */}
                <line x1={x} y1="15" x2={x} y2="105" stroke="#d1d1d6" strokeWidth={i === 0 ? "4" : "1.5"} />
                
                {/* Fret Position Numbering */}
                {i > 0 && (
                  <text x={x - (750 / fretCount / 2)} y="116" fontSize="9" fill="var(--color-muted)" textAnchor="middle" fontFamily="sans-serif">
                    {i}
                  </text>
                )}

                {/* Pearl Inlay Dots */}
                {isFretMarker && !isDoubleMarker && (
                  <circle x={x - (750 / fretCount / 2)} cx={x - (750 / fretCount / 2)} cy="60" r="3.5" fill="#dedad2" />
                )}
                {isDoubleMarker && (
                  <>
                    <circle cx={x - (750 / fretCount / 2)} cy="38" r="3" fill="#dedad2" />
                    <circle cx={x - (750 / fretCount / 2)} cy="82" r="3" fill="#dedad2" />
                  </>
                )}
              </g>
            )
          })}

          {/* Guitar Strings (Thicker for Low Strings) */}
          {STRING_NAMES.map((name, sIdx) => {
            const y = 22 + (sIdx * 15.2)
            const strokeWidth = 0.8 + (sIdx * 0.35)

            return (
              <g key={`string-${sIdx}`}>
                {/* String Label */}
                <text x="15" y={y + 3} fontSize="10" fontWeight="600" fill="var(--color-ink)" textAnchor="middle" fontFamily="sans-serif">
                  {name}
                </text>
                {/* Steel Guitar String Line */}
                <line x1="30" y1={y} x2="780" y2={y} stroke="#8e8e93" strokeWidth={strokeWidth} opacity="0.85" />
              </g>
            )
          })}

          {/* Active Note Placement Markers */}
          {activeNotes.map((note, idx) => {
            const fretWidth = 750 / fretCount
            const x = note.fret === 0 ? 30 : 30 + (note.fret * fretWidth) - (fretWidth / 2)
            const y = 22 + (note.stringIdx * 15.2)

            return (
              <g key={`note-${idx}`}>
                <circle cx={x} cy={y} r="7.5" fill="var(--color-ink)" />
                <text x={x} y={y + 3} fontSize="8" fontWeight="700" fill="#ffffff" textAnchor="middle" fontFamily="sans-serif">
                  {note.label || note.fret}
                </text>
              </g>
            )
          })}
        </svg>
      </div>
    </div>
  )
}