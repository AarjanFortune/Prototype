import React, { useState } from 'react'

interface TablatureViewerProps {
  content: string
  tuning?: string
  tempo?: number
}

export default function TablatureViewer({
  content,
  tuning = 'Standard (E A D G B E)',
  tempo = 120
}: TablatureViewerProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div
      style={{
        marginTop: '24px',
        width: '100%',
        borderRadius: '12px',
        border: '1px solid var(--color-border, #e5e5ea)',
        backgroundColor: '#1c1c1e',
        color: '#f2f2f7',
        fontFamily: 'ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace',
        overflow: 'hidden',
        boxShadow: '0 8px 30px rgba(0, 0, 0, 0.12)'
      }}
    >
      {/* Studio Bar Header */}
      <div
        style={{
          display: 'flex',
          justify: 'space-between',
          alignItems: 'center',
          padding: '12px 16px',
          borderBottom: '1px solid #2c2c2e',
          backgroundColor: '#2c2c2e'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#8e8e93' }}>
            {tuning}
          </span>
          <span style={{ fontSize: '0.7rem', color: '#636366' }}>•</span>
          <span style={{ fontSize: '0.7rem', color: '#8e8e93' }}>{tempo} BPM</span>
        </div>

        <button
          onClick={handleCopy}
          style={{
            background: copied ? '#34c759' : '#0a84ff',
            color: '#ffffff',
            border: 'none',
            borderRadius: '6px',
            padding: '5px 12px',
            fontSize: '0.7rem',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'background-color 0.2s ease'
          }}
        >
          {copied ? 'Copied' : 'Copy ASCII'}
        </button>
      </div>

      {/* Monospaced Staff Display */}
      <div
        style={{
          padding: '20px 16px',
          overflowX: 'auto',
          fontSize: '0.82rem',
          lineHeight: '1.5',
          letterSpacing: '0.05em',
          color: '#e5e5ea',
          whiteSpace: 'pre'
        }}
      >
        {content || `e|--------------------------------------------------|\nB|--------------------------------------------------|\nG|--------------------------------------------------|\nD|--------------------------------------------------|\nA|--------------------------------------------------|\nE|--------------------------------------------------|`}
      </div>
    </div>
  )
}