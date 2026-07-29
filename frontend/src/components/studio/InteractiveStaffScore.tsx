import React, { useState, useEffect, useRef } from 'react'
import { TranscribedNote } from '../tabs/UploadTab'

interface StaffScoreProps {
  audioFile?: File | null
  audioUrl?: string | null
  fileInfo: { name: string; size: string }
  onReset: () => void
  transcriptionData: TranscribedNote[]
  backendMeta?: any
}

export default function InteractiveStaffScore({ 
  audioFile, 
  audioUrl,
  fileInfo, 
  onReset, 
  transcriptionData,
  backendMeta 
}: StaffScoreProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [activeNotes, setActiveNotes] = useState<TranscribedNote[]>([])

  const audioRef = useRef<HTMLAudioElement | null>(null)
  const animFrameRef = useRef<number | null>(null)

  const stringLabels = ['e', 'B', 'G', 'D', 'A', 'E']
  const stringThicknesses = [0.8, 1.0, 1.2, 1.6, 2.0, 2.5] 

  const pixelsPerSecond = 100 
  
  const maxNoteTime = transcriptionData.length > 0 
    ? Math.max(...transcriptionData.map(n => n.time)) 
    : 0

  const effectiveDuration = Math.max(
    duration || 0, 
    backendMeta?.duration || 0, 
    maxNoteTime + 2, 
    10
  )
  
  const totalWidth = effectiveDuration * pixelsPerSecond
  const playheadFixedX = 140 

  // Initialize HTML5 Audio Element (Works for both Uploaded Blob and YouTube static URL)
  useEffect(() => {
    let srcToUse: string | null = null
    let createdBlob = false

    if (audioFile) {
      srcToUse = URL.createObjectURL(audioFile)
      createdBlob = true
    } else if (audioUrl) {
      srcToUse = audioUrl
    }

    if (!srcToUse) {
      setDuration(effectiveDuration)
      return
    }

    const audio = new Audio(srcToUse)
    audioRef.current = audio

    const handleLoadedMetadata = () => {
      setDuration(audio.duration)
    }

    const handleEnded = () => {
      setIsPlaying(false)
      setCurrentTime(0)
    }

    audio.addEventListener('loadedmetadata', handleLoadedMetadata)
    audio.addEventListener('ended', handleEnded)

    return () => {
      audio.pause()
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata)
      audio.removeEventListener('ended', handleEnded)
      if (createdBlob && srcToUse) URL.revokeObjectURL(srcToUse)
      audioRef.current = null
    }
  }, [audioFile, audioUrl, effectiveDuration])

  // Playhead Smooth Animation Loop
  useEffect(() => {
    const updateProgress = () => {
      if (!isPlaying || !audioRef.current) return

      const cur = audioRef.current.currentTime
      setCurrentTime(cur)

      // Active note highlighting window
      const currentActive = transcriptionData.filter(n => Math.abs(n.time - cur) < 0.12)
      setActiveNotes(currentActive)

      animFrameRef.current = requestAnimationFrame(updateProgress)
    }

    if (isPlaying) {
      animFrameRef.current = requestAnimationFrame(updateProgress)
    } else {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
      setActiveNotes([])
    }

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
    }
  }, [isPlaying, transcriptionData])

  const togglePlayback = () => {
    if (!audioRef.current) return

    if (isPlaying) {
      audioRef.current.pause()
      setIsPlaying(false)
    } else {
      audioRef.current.play()
        .then(() => setIsPlaying(true))
        .catch(err => console.error('Playback Error:', err))
    }
  }

  const scoreTranslateX = playheadFixedX - (currentTime * pixelsPerSecond)

  return (
    <div style={{ width: '100%', maxWidth: '620px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', paddingBottom: '12px', borderBottom: '1px solid var(--color-border)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <span style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--color-ink)', letterSpacing: '-0.02em' }}>
            {fileInfo.name}
          </span>
          <span style={{ fontSize: '0.62rem', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>
            Standard Tuning (E A D G B E) • {backendMeta?.tempo ? `${Math.round(backendMeta.tempo)} BPM` : '120 BPM'}
          </span>
        </div>

        <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
          <button
            onClick={togglePlayback}
            style={{
              background: 'none', border: 'none', color: 'var(--color-ink)',
              fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.15em',
              textTransform: 'uppercase', cursor: 'pointer', display: 'flex',
              alignItems: 'center', gap: '6px', padding: 0
            }}
          >
            {isPlaying ? <span style={{ color: '#c94b4b' }}>[ PAUSE SYNC ]</span> : <span>[ PLAY SYNC ]</span>}
          </button>

          <button
            onClick={onReset}
            style={{
              background: 'none', border: 'none', borderBottom: '1px solid var(--color-muted)',
              color: 'var(--color-muted)', fontSize: '0.65rem', letterSpacing: '0.12em',
              textTransform: 'uppercase', cursor: 'pointer', paddingBottom: '2px'
            }}
          >
            New Track
          </button>
        </div>
      </div>

      {/* Score Canvas */}
      <div style={{
        background: '#fcfcfd', border: '1px solid var(--color-border)', borderRadius: '4px',
        height: '210px', position: 'relative', overflow: 'hidden', boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.02)'
      }}>
        {/* Clef Overlay */}
        <div style={{
          position: 'absolute', left: 0, top: 0, bottom: 0, width: '40px',
          background: 'linear-gradient(90deg, #fcfcfd 80%, transparent 100%)', zIndex: 10,
          display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: '38px',
          gap: '12px', fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: '11px',
          color: 'var(--color-ink)', borderRight: '2px solid var(--color-ink)'
        }}>
          <span>T</span><span>A</span><span>B</span>
        </div>

        {/* Fixed Red Playhead Cursor */}
        <div style={{
          position: 'absolute', left: `${playheadFixedX}px`, top: 0, bottom: 0, width: '2px',
          backgroundColor: '#c94b4b', zIndex: 8, pointerEvents: 'none', boxShadow: '0 0 8px rgba(201, 75, 75, 0.4)'
        }}>
          <div style={{ position: 'absolute', top: 0, left: '-3px', width: '8px', height: '8px', backgroundColor: '#c94b4b' }} />
          <div style={{ position: 'absolute', bottom: 0, left: '-3px', width: '8px', height: '8px', backgroundColor: '#c94b4b' }} />
        </div>

        {/* Translating Score */}
        <div style={{
          position: 'absolute', left: 0, top: 0, height: '100%', width: `${totalWidth}px`,
          transform: `translateX(${scoreTranslateX}px)`, transition: isPlaying ? 'none' : 'transform 0.1s ease-out',
          willChange: 'transform'
        }}>
          <svg viewBox={`0 0 ${totalWidth} 210`} style={{ width: `${totalWidth}px`, height: '100%' }}>
            
            {/* Measures */}
            {Array.from({ length: Math.ceil(effectiveDuration / 2) + 1 }).map((_, i) => {
              const mX = i * 2 * pixelsPerSecond
              return (
                <g key={`measure-${i}`}>
                  <line x1={mX} y1="20" x2={mX} y2="160" stroke="#d1d1d6" strokeWidth="1" strokeDasharray="4 4" />
                  <text x={mX + 6} y="16" fontSize="9" fill="var(--color-muted)" fontFamily="var(--font-sans)">
                    {i * 2}s
                  </text>
                </g>
              )
            })}

            {/* 6 Guitar Strings */}
            {stringLabels.map((_, idx) => {
              const y = 38 + (idx * 24)
              return <line key={`string-${idx}`} x1="0" y1={y} x2={totalWidth} y2={y} stroke="#d1d1d6" strokeWidth={stringThicknesses[idx]} />
            })}

            {/* Transcribed Notes with Opaque Background Masks to eliminate text overlap */}
            {transcriptionData.map((n, idx) => {
              const xOffset = n.time * pixelsPerSecond
              const y = 38 + (n.stringIdx * 24)
              const isActive = activeNotes.some(an => an.time === n.time && an.stringIdx === n.stringIdx)

              return (
                <g key={`note-${idx}`}>
                  {/* Clean Background Box to mask out string line */}
                  <rect x={xOffset - 8} y={y - 8} width="16" height="16" fill="#fcfcfd" rx="2" />
                  
                  {isActive && (
                    <circle cx={xOffset} cy={y} r="10" fill="none" stroke="#c94b4b" strokeWidth="1.5" />
                  )}

                  <text 
                    x={xOffset} y={y + 4} fontSize="11" fontWeight={isActive ? "800" : "600"} 
                    fill={isActive ? "#c94b4b" : "var(--color-ink)"} 
                    textAnchor="middle" fontFamily="ui-monospace, 'SF Mono', Consolas, monospace"
                  >
                    {n.fret}
                  </text>
                </g>
              )
            })}
          </svg>
        </div>
      </div>

      {/* Live Fretboard Mapping */}
      <div style={{
        display: 'flex', flexDirection: 'column', gap: '8px', background: 'transparent',
        border: '1px solid var(--color-border)', borderRadius: '4px', padding: '12px 14px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.15em', color: 'var(--color-muted)', fontWeight: 600 }}>
            Live Fretboard Mapping
          </span>
          <span style={{ fontSize: '0.62rem', color: 'var(--color-ink)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            {activeNotes.length > 0 ? `Tracking ${activeNotes.length} Note(s)` : 'Awaiting Input'}
          </span>
        </div>

        <div style={{ position: 'relative', width: '100%', height: '36px', background: '#f5f5f7', border: '1px solid #e5e5ea', borderRadius: '3px' }}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} style={{ position: 'absolute', left: `${(i + 1) * 16.66}%`, top: 0, bottom: 0, width: '1px', background: '#d1d1d6' }} />
          ))}
          
          {activeNotes.map((note, i) => {
            const fretPos = ((note.fret as number) % 12) / 12 * 100
            const stringPos = (note.stringIdx / 5) * 26 + 4

            return (
              <div 
                key={`live-fret-${i}`}
                style={{
                  position: 'absolute', left: `${fretPos}%`, top: `${stringPos}px`, width: '8px', height: '8px',
                  borderRadius: '50%', background: '#c94b4b', transform: 'translate(-50%, 0)', boxShadow: '0 0 6px rgba(201, 75, 75, 0.6)'
                }}
              />
            )
          })}
        </div>
      </div>

    </div>
  )
}