import React, { useState } from 'react'

interface NoteElement {
  stringIdx: number // 0 (e) to 5 (E)
  fret: number | string
  col: number
  technique?: 'bend' | 'slide' | 'hammer' | 'vibrato'
}

export default function InteractiveStaffScore() {
  const [activeMeasure, setActiveMeasure] = useState<number>(1)
  const [isPlaying, setIsPlaying] = useState<boolean>(false)

  // Rich sample tab data mapped for guitarists
  const measureNotes: NoteElement[] = [
    { stringIdx: 0, fret: 12, col: 1, technique: 'hammer' },
    { stringIdx: 0, fret: 15, col: 2, technique: 'bend' },
    { stringIdx: 1, fret: 12, col: 3 },
    { stringIdx: 1, fret: 15, col: 4, technique: 'vibrato' },
    { stringIdx: 2, fret: 14, col: 5, technique: 'slide' },
    { stringIdx: 3, fret: 14, col: 6 },
    { stringIdx: 4, fret: 12, col: 7 }
  ]

  const strings = ['e', 'B', 'G', 'D', 'A', 'E']

  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      gap: '14px',
      paddingLeft: '24px',
      borderLeft: '1px solid var(--color-border)'
    }}>
      {/* Workbench Result Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.15em', color: 'var(--color-muted)', fontWeight: 600 }}>
            Transcribed Interactive Score
          </span>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-ink)', marginTop: '2px' }}>
            Standard Tuning (E A D G B E) • 120 BPM
          </div>
        </div>

        <button
          onClick={() => setIsPlaying(!isPlaying)}
          style={{
            padding: '6px 14px',
            borderRadius: '20px',
            border: '1px solid var(--color-ink)',
            background: isPlaying ? 'var(--color-ink)' : 'transparent',
            color: isPlaying ? '#ffffff' : 'var(--color-ink)',
            fontSize: '0.68rem',
            fontWeight: 600,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <span>{isPlaying ? 'Pause Playback' : 'Play Audio Sync'}</span>
        </button>
      </div>

      {/* Vector Notation Canvas */}
      <div style={{
        background: '#fcfcfd',
        border: '1px solid var(--color-border)',
        borderRadius: '8px',
        padding: '20px 16px',
        position: 'relative'
      }}>
        <svg viewBox="0 0 460 160" style={{ width: '100%', display: 'block' }}>
          {/* Clef / Tuning Indicator */}
          <text x="10" y="24" fontSize="10" fontWeight="700" fill="var(--color-ink)" fontFamily="sans-serif">T</text>
          <text x="10" y="44" fontSize="10" fontWeight="700" fill="var(--color-ink)" fontFamily="sans-serif">A</text>
          <text x="10" y="64" fontSize="10" fontWeight="700" fill="var(--color-ink)" fontFamily="sans-serif">B</text>

          {/* Bar lines */}
          <line x1="30" y1="15" x2="30" y2="115" stroke="var(--color-ink)" strokeWidth="2" />
          <line x1="240" y1="15" x2="240" y2="115" stroke="#d1d1d6" strokeWidth="1.5" strokeDasharray="3 3" />
          <line x1="445" y1="15" x2="445" y2="115" stroke="var(--color-ink)" strokeWidth="2" />

          {/* 6 Guitar Staff Lines */}
          {strings.map((str, idx) => {
            const y = 18 + (idx * 19)
            return (
              <g key={`str-${idx}`}>
                <line x1="30" y1={y} x2="445" y2={y} stroke="#e5e5ea" strokeWidth="1.2" />
              </g>
            )
          })}

          {/* Render Expressive Note Events */}
          {measureNotes.map((note, idx) => {
            const x = 50 + (note.col * 50)
            const y = 18 + (note.stringIdx * 19)

            return (
              <g key={`note-${idx}`}>
                {/* Note Pill Mask */}
                <rect x={x - 8} y={y - 7} width="16" height="14" rx="3" fill="#ffffff" stroke="#d1d1d6" strokeWidth="1" />
                
                {/* Fret Number */}
                <text x={x} y={y + 3.5} fontSize="9.5" fontWeight="700" fill="var(--color-ink)" textAnchor="middle" fontFamily="sans-serif">
                  {note.fret}
                </text>

                {/* Guitar Technique Articulations */}
                {note.technique === 'bend' && (
                  <path d={`M ${x} ${y - 8} Q ${x + 6} ${y - 16} ${x + 12} ${y - 12}`} fill="none" stroke="#ff9500" strokeWidth="1.5" />
                )}
                {note.technique === 'vibrato' && (
                  <path d={`M ${x - 6} ${y - 10} Q ${x - 3} ${y - 14} ${x} ${y - 10} T ${x + 6} ${y - 10}`} fill="none" stroke="#34c759" strokeWidth="1.2" />
                )}
                {note.technique === 'slide' && (
                  <line x1={x - 12} y1={y + 6} x2={x - 4} y2={y - 2} stroke="#007aff" strokeWidth="1.5" />
                )}
              </g>
            )
          })}
        </svg>
      </div>

      {/* Guitarist Pro Feature: Interactive Fretboard Map */}
      <div style={{
        background: '#fafafa',
        border: '1px solid var(--color-border)',
        borderRadius: '8px',
        padding: '12px 16px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--color-muted)', fontWeight: 600 }}>
            Active Fretboard Position (Frets 12 - 15)
          </span>
          <span style={{ fontSize: '0.62rem', color: 'var(--color-muted)' }}>Key: E Minor</span>
        </div>

        {/* Fretboard Mini Map */}
        <svg viewBox="0 0 400 50" style={{ width: '100%', display: 'block' }}>
          <rect x="10" y="5" width="380" height="40" fill="#f2f0eb" rx="3" stroke="#e0e0e0" />
          {Array.from({ length: 5 }).map((_, i) => {
            const x = 10 + (i * 76)
            return <line key={i} x1={x} y1="5" x2={x} y2="45" stroke="#d1d1d6" strokeWidth="1.5" />
          })}
          {/* Active Fret Highlights */}
          <circle cx="162" cy="12" r="5" fill="var(--color-ink)" />
          <circle cx="314" cy="12" r="5" fill="#ff9500" />
          <circle cx="238" cy="20" r="5" fill="var(--color-ink)" />
        </svg>
      </div>
    </div>
  )
}