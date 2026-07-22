import React, { useState } from 'react'
import FretboardVisualizer from './FretboardVisualizer'

interface TablatureViewerProps {
  rawTab: string
  tuning?: string
  tempo?: number
}

export default function TablatureViewer({
  rawTab,
  tuning = 'Standard (E A D G B E)',
  tempo = 120
}: TablatureViewerProps) {
  const [copied, setCopied] = useState(false)

  // Example active notes mapped directly for visual demo
  const sampleNotes = [
    { stringIdx: 0, fret: 12, label: '12' },
    { stringIdx: 1, fret: 10, label: '10' },
    { stringIdx: 2, fret: 9, label: '9' },
    { stringIdx: 2, fret: 7, label: '7' }
  ]

  const handleCopy = () => {
    navigator.clipboard.writeText(rawTab)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div style={{
      width: '100%',
      marginTop: '24px',
      display: 'flex',
      flexDirection: 'column',
      gap: '16px'
    }}>
      {/* Editorial Header */}
      <div style={{
        display: 'flex',
        justify: 'space-between',
        alignItems: 'center',
        borderBottom: '1px solid var(--color-border)',
        paddingBottom: '10px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.15em', color: 'var(--color-muted)', fontWeight: 600 }}>
            Generated Score
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--color-ink)', fontWeight: 500 }}>
            {tuning} • {tempo} BPM
          </span>
        </div>

        <button
          onClick={handleCopy}
          style={{
            background: 'transparent',
            border: 'none',
            borderBottom: '1px solid var(--color-ink)',
            color: 'var(--color-ink)',
            fontSize: '0.7rem',
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            cursor: 'pointer',
            paddingBottom: '2px',
            fontWeight: 600
          }}
        >
          {copied ? 'Copied' : 'Copy Text Tab'}
        </button>
      </div>

      {/* Vector Notation Staff (Light Editorial Aesthetic) */}
      <div style={{
        width: '100%',
        padding: '20px',
        background: '#f9f9fb',
        border: '1px solid var(--color-border)',
        borderRadius: '8px',
        overflowX: 'auto',
        fontFamily: 'Consolas, Monaco, "Courier New", monospace',
        fontSize: '0.85rem',
        lineHeight: '1.6',
        color: 'var(--color-ink)',
        whiteSpace: 'pre'
      }}>
        {rawTab || `e|--12--10--------------------|--12--10--------------------|\nB|----------12--10------------|----------12--10------------|\nG|------------------12--9--7~-|------------------12--9--7~-|\nD|----------------------------|----------------------------|\nA|----------------------------|----------------------------|\nE|----------------------------|----------------------------|`}
      </div>

      {/* Embedded Fretboard Mapping */}
      <FretboardVisualizer activeNotes={sampleNotes} />
    </div>
  )
}