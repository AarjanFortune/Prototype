import { useEffect, useMemo, useRef, useState } from 'react'
import { TranscribedNote, TranscriptionResult } from '../types/transcription'
import { formatBytes, formatDuration, formatTempo } from '../utils/formatTranscription'

interface TranscriptionReportProps {
  result: TranscriptionResult
  onReset: () => void
}

const STRING_LABELS = ['e', 'B', 'G', 'D', 'A', 'E']

export default function TranscriptionReport({ result, onReset }: TranscriptionReportProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(result.metadata.duration || 0)
  const [hasAudio, setHasAudio] = useState(false)
  const [playbackError, setPlaybackError] = useState('')
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const frameRef = useRef<number | null>(null)

  const confidenceAverage = useMemo(() => averageConfidence(result.confidence), [result.confidence])
  const effectiveDuration = Math.max(duration, result.metadata.duration || 0, maxNoteTime(result.notes) + 1, 1)
  const pixelsPerSecond = 92
  const totalWidth = Math.max(1100, effectiveDuration * pixelsPerSecond)
  const playheadX = 74

  const metrics = [
    { label: 'Duration', value: formatDuration(result.metadata.duration) },
    { label: 'Tempo', value: formatTempo(result.metadata.tempo) },
    { label: 'Detected notes', value: result.notes.length.toString() },
    confidenceAverage ? { label: 'Confidence', value: confidenceAverage } : null,
    { label: 'Sample rate', value: `${result.metadata.sample_rate} Hz` },
    { label: 'Feature set', value: result.metadata.feature_type.toUpperCase() },
  ].filter((metric): metric is { label: string; value: string } => metric !== null)

  useEffect(() => {
    let src = result.audioUrl || null
    let shouldRevoke = false

    if (!src && result.sourceFile) {
      src = URL.createObjectURL(result.sourceFile)
      shouldRevoke = true
    }

    if (!src) return undefined

    const audio = new Audio(src)
    audio.preload = 'metadata'
    audioRef.current = audio

    const handleMetadata = () => {
      setDuration(audio.duration)
      setHasAudio(true)
      setPlaybackError('')
    }
    const handleEnded = () => {
      setIsPlaying(false)
      setCurrentTime(audio.duration)
    }
    const handleError = () => {
      setHasAudio(false)
      setIsPlaying(false)
      setPlaybackError('Audio could not be loaded')
    }

    audio.addEventListener('loadedmetadata', handleMetadata)
    audio.addEventListener('ended', handleEnded)
    audio.addEventListener('error', handleError)
    audio.load()

    return () => {
      audio.pause()
      audio.removeEventListener('loadedmetadata', handleMetadata)
      audio.removeEventListener('ended', handleEnded)
      audio.removeEventListener('error', handleError)
      if (shouldRevoke && src) URL.revokeObjectURL(src)
      audioRef.current = null
      setHasAudio(false)
    }
  }, [result.audioUrl, result.sourceFile])

  useEffect(() => {
    const update = () => {
      if (!audioRef.current || !isPlaying) return
      setCurrentTime(audioRef.current.currentTime)
      frameRef.current = requestAnimationFrame(update)
    }

    if (isPlaying) frameRef.current = requestAnimationFrame(update)
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current)
    }
  }, [isPlaying])

  const togglePlayback = () => {
    const audio = audioRef.current
    if (!audio) return
    setPlaybackError('')

    if (isPlaying) {
      audio.pause()
      setIsPlaying(false)
      return
    }

    if (audio.currentTime >= audio.duration) {
      audio.currentTime = 0
      setCurrentTime(0)
    }

    audio.play().then(() => setIsPlaying(true)).catch(() => {
      setIsPlaying(false)
      setPlaybackError('Playback was blocked')
    })
  }

  const seek = (time: number) => {
    const audio = audioRef.current
    if (!audio) return
    audio.currentTime = time
    setCurrentTime(time)
  }

  const activeNotes = result.notes.filter((note) => Math.abs(note.time - currentTime) < 0.14)

  return (
    <section className="report" aria-labelledby="report-title">
      <header className="report-header">
        <div className="report-identity">
          <p>Analysis report</p>
          <h1 id="report-title">{result.source.name}</h1>
          <span>
            {result.source.kind === 'youtube' ? 'YouTube' : 'Audio file'}
            {' / '}
            {formatBytes(result.source.size_bytes)}
          </span>
        </div>
        <button type="button" className="report-new" onClick={onReset}>New analysis</button>
      </header>

      <div className="report-body">
        <aside className="report-summary" aria-label="Analysis summary">
          <dl className="report-metrics">
            {metrics.map((metric) => (
              <Metric key={metric.label} label={metric.label} value={metric.value} />
            ))}
          </dl>

          <div className="playback-controls">
            <button type="button" onClick={togglePlayback} disabled={!hasAudio}>
              {isPlaying ? 'Pause' : 'Play'}
            </button>
            <div className="playback-time">
              <span>{formatDuration(currentTime)}</span>
              <span>{formatDuration(duration || result.metadata.duration)}</span>
            </div>
            <input
              type="range"
              min="0"
              max={Math.max(duration || result.metadata.duration, 0.01)}
              step="0.01"
              value={Math.min(currentTime, duration || result.metadata.duration)}
              onChange={(event) => seek(Number(event.target.value))}
              disabled={!hasAudio}
              aria-label="Playback position"
            />
            {playbackError && <p className="form-error">{playbackError}</p>}
          </div>
        </aside>

        <section className="report-score" aria-label="Synchronized tablature">
          <header className="score-header">
            <span>Tablature</span>
            <span>{formatDuration(currentTime)}</span>
          </header>
          <div className="score-viewport">
            <div className="playhead" style={{ left: playheadX }} />
            <div
              className="score-track"
              style={{
                width: totalWidth,
                transform: `translateX(${playheadX - currentTime * pixelsPerSecond}px)`,
              }}
            >
              <ScoreSvg
                notes={result.notes}
                activeNotes={activeNotes}
                totalWidth={totalWidth}
                effectiveDuration={effectiveDuration}
                pixelsPerSecond={pixelsPerSecond}
              />
            </div>
          </div>
        </section>
      </div>
    </section>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  )
}

function ScoreSvg({
  notes,
  activeNotes,
  totalWidth,
  effectiveDuration,
  pixelsPerSecond,
}: {
  notes: TranscribedNote[]
  activeNotes: TranscribedNote[]
  totalWidth: number
  effectiveDuration: number
  pixelsPerSecond: number
}) {
  return (
    <svg viewBox={`0 0 ${totalWidth} 300`} className="score-svg" role="img">
      {Array.from({ length: Math.ceil(effectiveDuration / 2) + 1 }).map((_, index) => {
        const x = index * 2 * pixelsPerSecond
        return (
          <g key={`measure-${index}`}>
            <line x1={x} y1="54" x2={x} y2="242" className="measure-line" />
            <text x={x + 9} y="36" className="measure-label">{index * 2}s</text>
          </g>
        )
      })}

      {STRING_LABELS.map((label, index) => {
        const y = 78 + index * 30
        return (
          <g key={label}>
            <text x="18" y={y + 4} className="string-label">{label}</text>
            <line x1="42" y1={y} x2={totalWidth} y2={y} className="string-line" />
          </g>
        )
      })}

      {notes.map((note, index) => {
        const x = 42 + note.time * pixelsPerSecond
        const y = 78 + note.stringIdx * 30
        const isActive = activeNotes.some((active) => (
          active.time === note.time &&
          active.stringIdx === note.stringIdx &&
          active.fret === note.fret
        ))

        return (
          <g key={`${note.time}-${note.stringIdx}-${index}`}>
            <rect x={x - 10} y={y - 10} width="20" height="20" className="note-mask" />
            {isActive && <rect x={x - 11} y={y - 11} width="22" height="22" className="active-note-box" />}
            <text x={x} y={y + 4} className={isActive ? 'note-text active-note-text' : 'note-text'}>
              {note.fret}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

function averageConfidence(confidence?: number[][]): string | null {
  const values = confidence?.flat().filter((value) => Number.isFinite(value)) || []
  if (values.length === 0) return null
  const average = values.reduce((sum, value) => sum + value, 0) / values.length
  return `${Math.round(average * 100)}%`
}

function maxNoteTime(notes: TranscribedNote[]): number {
  return notes.length ? Math.max(...notes.map((note) => note.time)) : 0
}
