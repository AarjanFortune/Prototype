import React, { useState } from 'react'
import InteractiveStaffScore from '../studio/InteractiveStaffScore'
import { TranscribedNote } from './UploadTab'

export default function YouTubeTab() {
  const [url, setUrl] = useState('')
  const [processingMethod, setProcessingMethod] = useState('cqt')
  const [status, setStatus] = useState<'idle' | 'processing' | 'complete'>('idle')
  const [realNoteData, setRealNoteData] = useState<TranscribedNote[]>([])
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [backendMeta, setBackendMeta] = useState<any>(null)

  const handleProcess = async () => {
    if (!url.trim()) return
    setStatus('processing')

    try {
      const response = await fetch('http://localhost:8000/api/transcribe/youtube', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim(), feature_type: processingMethod })
      })

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)

      const data = await response.json()
      
      if (data.status === 'error') {
        alert(`Backend Error: ${data.error}`)
        setStatus('idle')
        return
      }

      setBackendMeta(data.metadata || null)
      setAudioUrl(data.audio_url || null)

      let cleanNotes: TranscribedNote[] = []

      if (data && data.pianoroll && Array.isArray(data.pianoroll.notes)) {
        const rawNotes = data.pianoroll.notes
        const audioDuration = data.metadata?.duration || 0
        const pianorollDuration = data.pianoroll?.total_duration || 0
        const timeScale = (audioDuration > 0 && pianorollDuration > 0) ? (audioDuration / pianorollDuration) : 1.0

        rawNotes.forEach((note: any) => {
          cleanNotes.push({
            time: Number(note.start_time) * timeScale,
            stringIdx: 5 - Number(note.string),
            fret: Number(note.fret)
          })
        })

        // SORT AND DE-DUPLICATE OVERLAPPING NOTES (Fixes Visual Overlap Ghosting)
        cleanNotes.sort((a, b) => a.time - b.time)
        const filteredNotes: TranscribedNote[] = []
        const minTimeGap = 0.08 // Minimum 80ms gap required on same string

        cleanNotes.forEach(note => {
          const lastOnSameString = [...filteredNotes].reverse().find(n => n.stringIdx === note.stringIdx)
          if (!lastOnSameString || (note.time - lastOnSameString.time) >= minTimeGap) {
            filteredNotes.push(note)
          }
        })

        cleanNotes = filteredNotes
      }

      setRealNoteData(cleanNotes)
      setStatus('complete')

    } catch (error) {
      alert('Failed to connect to backend on http://localhost:8000.')
      setStatus('idle')
    }
  }

  const handleReset = () => {
    setStatus('idle')
    setUrl('')
    setRealNoteData([])
    setAudioUrl(null)
    setBackendMeta(null)
  }

  return (
    <div style={{ width: '100%', height: '100%' }}>
      {status !== 'complete' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', maxWidth: '440px' }}>
          <div>
            <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.75rem', fontWeight: 400, marginBottom: '6px', color: 'var(--color-ink)' }}>
              Transcribe via YouTube
            </h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--color-muted)', lineHeight: '1.4' }}>
              Paste a YouTube URL to extract, play audio, and view synchronized tablature.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--color-muted)', fontWeight: 600 }}>
              YouTube URL
            </label>
            <input 
              type="text"
              placeholder="https://www.youtube.com/watch?v=..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              style={{
                background: 'transparent', border: 'none', borderBottom: '1px solid var(--color-border)',
                padding: '8px 0', fontSize: '0.85rem', outline: 'none', color: 'var(--color-ink)', width: '100%'
              }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--color-muted)', fontWeight: 600 }}>
              Analysis Engine
            </label>
            <select 
              style={{ background: 'transparent', border: 'none', borderBottom: '1px solid var(--color-ink)', padding: '6px 0', fontSize: '0.85rem', outline: 'none', cursor: 'pointer', color: 'var(--color-ink)', fontWeight: 500 }}
              value={processingMethod} 
              onChange={(e) => setProcessingMethod(e.target.value)}
            >
              <option value="cqt">Constant-Q Pitch Tracking</option>
              <option value="mel">Polyphonic Spectral Analysis</option>
            </select>
          </div>

          <button 
            onClick={handleProcess}
            disabled={!url.trim() || status === 'processing'}
            style={{
              alignSelf: 'flex-start', background: 'none', border: 'none', borderBottom: '2px solid var(--color-ink)',
              color: 'var(--color-ink)', fontSize: '0.72rem', fontWeight: 600, letterSpacing: '0.12em',
              textTransform: 'uppercase', cursor: (!url.trim() || status === 'processing') ? 'not-allowed' : 'pointer',
              opacity: (!url.trim() || status === 'processing') ? 0.35 : 1, paddingBottom: '2px', marginTop: '6px'
            }}
          >
            {status === 'processing' ? '[ Extracting Audio & Transcribing... ]' : '[ Transcribe Link ]'}
          </button>
        </div>
      )}

      {status === 'complete' && (
        <InteractiveStaffScore 
          audioFile={null} 
          audioUrl={audioUrl}
          fileInfo={{ name: 'YouTube Audio Stream', size: 'Live Sync' }}
          onReset={handleReset}
          transcriptionData={realNoteData}
          backendMeta={backendMeta}
        />
      )}
    </div>
  )
}