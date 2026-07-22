import React, { useState, useRef } from 'react'
import InteractiveStaffScore from '../studio/InteractiveStaffScore'

export default function UploadTab() {
  const [file, setFile] = useState<File | null>(null)
  const [processingMethod, setProcessingMethod] = useState('cqt')
  const [status, setStatus] = useState<'idle' | 'processing' | 'complete'>('idle')
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const handleProcess = () => {
    if (!file) return
    setStatus('processing')

    setTimeout(() => {
      setStatus('complete')
    }, 1800)
  }

  return (
    <div style={{ display: 'flex', width: '100%', gap: '32px' }}>
      {/* LEFT COLUMN: STATIC CONTROL CARD (~42%) */}
      <div style={{ flex: '0 0 42%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.75rem', fontWeight: 400, marginBottom: '6px', color: 'var(--color-ink)' }}>
            Convert Audio to Tablature
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--color-muted)', lineHeight: '1.4' }}>
            Upload audio to extract notes, pitches, and interactive tablature
          </p>
        </div>

        <input 
          ref={fileInputRef}
          type="file" 
          accept="audio/*"
          style={{ display: 'none' }}
          onChange={(e) => {
            setFile(e.target.files?.[0] || null)
            setStatus('idle')
          }}
        />

        {/* Upload Box */}
        <div 
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: '1px dashed var(--color-border)',
            borderRadius: '8px',
            padding: '24px 16px',
            background: file ? 'rgba(0,0,0,0.015)' : 'transparent',
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-ink)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 18V5l12-2v13" />
            <circle cx="6" cy="18" r="3" />
            <circle cx="18" cy="16" r="3" />
          </svg>

          {file ? (
            <div style={{ textAlign: 'center' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-ink)', display: 'block' }}>{file.name}</span>
              <span style={{ fontSize: '0.65rem', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                {(file.size / (1024 * 1024)).toFixed(2)} MB • Click to change
              </span>
            </div>
          ) : (
            <div style={{ textAlign: 'center' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--color-ink)', display: 'block' }}>Choose an audio file or drag it here</span>
              <span style={{ fontSize: '0.65rem', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Supports MP3, WAV, FLAC, AAC</span>
            </div>
          )}
        </div>

        {/* Processing Method */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--color-muted)', fontWeight: 600 }}>
            Analysis Engine
          </label>
          <select 
            style={{ 
              background: 'transparent', 
              border: 'none', 
              borderBottom: '1px solid var(--color-ink)', 
              padding: '6px 0', 
              fontSize: '0.85rem', 
              outline: 'none', 
              cursor: 'pointer',
              color: 'var(--color-ink)',
              fontWeight: 500
            }}
            value={processingMethod} 
            onChange={(e) => setProcessingMethod(e.target.value)}
          >
            <option value="cqt">Constant-Q Guitar Pitch Tracking</option>
            <option value="mel">High-Detail Polyphonic Tracking</option>
          </select>
        </div>

        {/* Action Button */}
        <button 
          onClick={handleProcess}
          disabled={!file || status === 'processing'}
          style={{
            padding: '12px',
            backgroundColor: 'var(--color-ink)',
            color: '#ffffff',
            border: 'none',
            borderRadius: '6px',
            fontSize: '0.75rem',
            fontWeight: 600,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            cursor: (!file || status === 'processing') ? 'not-allowed' : 'pointer',
            opacity: (!file || status === 'processing') ? 0.35 : 1
          }}
        >
          {status === 'processing' ? 'Transcribing...' : 'Transcribe Audio'}
        </button>
      </div>

      {/* RIGHT COLUMN: INTERACTIVE RESULT WORKBENCH (~58%) */}
      <div style={{ flex: '0 0 58%' }}>
        {status === 'complete' ? (
          <InteractiveStaffScore />
        ) : (
          <div style={{
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justify: 'center',
            borderLeft: '1px solid var(--color-border)',
            paddingLeft: '24px'
          }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>
              [ Generated tab score will render here ]
            </span>
          </div>
        )}
      </div>
    </div>
  )
}