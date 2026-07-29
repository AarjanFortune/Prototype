import React, { useState, useRef } from 'react'
import InteractiveStaffScore from '../studio/InteractiveStaffScore'

export interface TranscribedNote {
  stringIdx: number
  fret: number
  time: number
  technique?: 'bend' | 'slide' | 'hammer' | 'pull' | 'vibrato'
}

export default function UploadTab() {
  const [file, setFile] = useState<File | null>(null)
  const [processingMethod, setProcessingMethod] = useState('cqt')
  const [status, setStatus] = useState<'idle' | 'processing' | 'complete'>('idle')
  const [realNoteData, setRealNoteData] = useState<TranscribedNote[]>([])
  const [backendMeta, setBackendMeta] = useState<any>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const handleProcess = async () => {
    if (!file) return
    setStatus('processing')

    console.log('[GUITARICA TELEMETRY] INITIATING UPLOAD', { name: file.name, sizeBytes: file.size })

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('feature_type', processingMethod)

      const startTime = performance.now()
      const response = await fetch('http://localhost:8000/api/transcribe/upload', {
        method: 'POST',
        body: formData
      })

      const endTime = performance.now()

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      console.log('[GUITARICA TELEMETRY] RAW BACKEND RESPONSE:', data)
      console.log(`[GUITARICA TELEMETRY] Network Time: ${((endTime - startTime) / 1000).toFixed(2)}s`)

      setBackendMeta(data.metadata || null)

      let cleanNotes: TranscribedNote[] = []

      if (data && data.pianoroll && Array.isArray(data.pianoroll.notes)) {
        const rawNotes = data.pianoroll.notes
        
        // Calculate the ConvStack downsampling scale factor (Fixes the 4x time compression bug)
        const audioDuration = data.metadata?.duration || 0
        const pianorollDuration = data.pianoroll?.total_duration || 0
        const timeScale = (audioDuration > 0 && pianorollDuration > 0) 
          ? (audioDuration / pianorollDuration) 
          : 1.0

        console.log(`[GUITARICA TELEMETRY] Applied Time Scale Factor: ${timeScale.toFixed(4)}x`)

        rawNotes.forEach((note: any) => {
          const mappedStringIdx = 5 - Number(note.string)
          cleanNotes.push({
            time: Number(note.start_time) * timeScale,
            stringIdx: mappedStringIdx,
            fret: Number(note.fret)
          })
        })

        const maxTimestamp = cleanNotes.length > 0 ? Math.max(...cleanNotes.map(n => n.time)) : 0
        console.log(`[GUITARICA TELEMETRY] Scaled Max Note Timestamp: ${maxTimestamp.toFixed(2)}s`)
        console.log(`[GUITARICA TELEMETRY] Total Notes Processed: ${cleanNotes.length}`)
      } else {
        console.error('[GUITARICA TELEMETRY] Backend missing data.pianoroll.notes array', data)
      }

      setRealNoteData(cleanNotes)
      setStatus('complete')

    } catch (error) {
      console.error('[GUITARICA TELEMETRY] BACKEND CONNECTION ERROR:', error)
      alert('Failed to connect to backend on http://localhost:8000')
      setStatus('idle')
    }
  }

  const handleReset = () => {
    setStatus('idle')
    setFile(null)
    setRealNoteData([])
    setBackendMeta(null)
  }

  return (
    <div style={{ width: '100%', height: '100%' }}>
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

      {status !== 'complete' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', maxWidth: '440px' }}>
          <div>
            <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.75rem', fontWeight: 400, marginBottom: '6px', color: 'var(--color-ink)' }}>
              Convert Audio to Tablature
            </h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--color-muted)', lineHeight: '1.4' }}>
              Upload an audio file to map pitch frequencies and construct fingerstyle scores
            </p>
          </div>

          <div 
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: '1px dashed var(--color-border)',
              borderRadius: '6px',
              padding: '24px 16px',
              background: file ? 'rgba(0,0,0,0.015)' : 'transparent',
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-ink)" strokeWidth="1.5">
              <path d="M9 18V5l12-2v13" />
              <circle cx="6" cy="18" r="3" />
              <circle cx="18" cy="16" r="3" />
            </svg>

            {file ? (
              <div style={{ textAlign: 'center' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-ink)', display: 'block' }}>{file.name}</span>
                <span style={{ fontSize: '0.62rem', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  {(file.size / (1024 * 1024)).toFixed(2)} MB • Click to replace
                </span>
              </div>
            ) : (
              <div style={{ textAlign: 'center' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--color-ink)', display: 'block' }}>Choose audio file or drag here</span>
                <span style={{ fontSize: '0.62rem', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>MP3, WAV, FLAC, AAC</span>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--color-muted)', fontWeight: 600 }}>
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
              <option value="cqt">Constant-Q Pitch Tracking</option>
              <option value="mel">Polyphonic Spectral Analysis</option>
            </select>
          </div>

          <button 
            onClick={handleProcess}
            disabled={!file || status === 'processing'}
            style={{
              alignSelf: 'flex-start',
              background: 'none',
              border: 'none',
              borderBottom: '2px solid var(--color-ink)',
              color: 'var(--color-ink)',
              fontSize: '0.72rem',
              fontWeight: 600,
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              cursor: (!file || status === 'processing') ? 'not-allowed' : 'pointer',
              opacity: (!file || status === 'processing') ? 0.35 : 1,
              paddingBottom: '2px',
              marginTop: '6px'
            }}
          >
            {status === 'processing' ? '[ Transcribing Audio... ]' : '[ Transcribe Audio ]'}
          </button>
        </div>
      )}

      {status === 'complete' && (
        <InteractiveStaffScore 
          audioFile={file}
          fileInfo={{ name: file?.name || 'Track.mp3', size: `${((file?.size || 2000000) / (1024 * 1024)).toFixed(2)} MB` }}
          onReset={handleReset}
          transcriptionData={realNoteData}
          backendMeta={backendMeta}
        />
      )}
    </div>
  )
}