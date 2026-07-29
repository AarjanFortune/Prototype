import { useEffect, useMemo, useRef, useState } from 'react'
import { TranscribedNote, TranscriptionResult } from '../types/transcription'
import { formatDuration, formatTempo } from '../utils/formatTranscription'

interface TranscriptionReportProps {
  result: TranscriptionResult
  onReset: () => void
}

const STRING_LABELS = ['e', 'B', 'G', 'D', 'A', 'E']

export default function TranscriptionReport({ result, onReset }: TranscriptionReportProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(result.metadata?.duration || 0)
  const [hasAudio, setHasAudio] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const frameRef = useRef<number | null>(null)

  const confidenceAverage = useMemo(() => averageConfidence(result.confidence), [result.confidence])
  const effectiveDuration = Math.max(duration, result.metadata?.duration || 0, maxNoteTime(result.notes) + 1, 8)
  const pixelsPerSecond = 88
  const totalWidth = Math.max(720, effectiveDuration * pixelsPerSecond)
  const playheadX = 120

  useEffect(() => {
    let src = result.audioUrl || null
    let shouldRevoke = false

    if (!src && result.sourceFile) {
      src = URL.createObjectURL(result.sourceFile)
      shouldRevoke = true
    }

    if (!src) return undefined

    const audio = new Audio(src)
    audioRef.current = audio
    setHasAudio(true)

    const handleMetadata = () => setDuration(audio.duration)
    const handleEnded = () => {
      setIsPlaying(false)
      setCurrentTime(0)
    }

    audio.addEventListener('loadedmetadata', handleMetadata)
    audio.addEventListener('ended', handleEnded)

    return () => {
      audio.pause()
      audio.removeEventListener('loadedmetadata', handleMetadata)
      audio.removeEventListener('ended', handleEnded)
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

    if (isPlaying) {
      frameRef.current = requestAnimationFrame(update)
    }

    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current)
    }
  }, [isPlaying])

  const togglePlayback = () => {
    const audio = audioRef.current
    if (!audio) return

    if (isPlaying) {
      audio.pause()
      setIsPlaying(false)
      return
    }

    audio.play().then(() => setIsPlaying(true)).catch(() => setIsPlaying(false))
  }

  const activeNotes = result.notes.filter((note) => Math.abs(note.time - currentTime) < 0.12)

  return (
    <section className="report" aria-labelledby="report-title">
      <div className="report-header">
        <div>
          <p className="section-kicker">Analysis report</p>
          <h2 id="report-title">{result.fileName}</h2>
          <p>{result.fileSize}</p>
        </div>
        <button type="button" className="text-action" onClick={onReset}>
          New analysis
        </button>
      </div>

      <dl className="report-metrics">
        <Metric label="Duration" value={formatDuration(result.metadata?.duration)} />
        <Metric label="Tempo" value={formatTempo(result.metadata?.tempo)} />
        <Metric label="Detected notes" value={result.notes.length.toString()} />
        <Metric label="Mean confidence" value={confidenceAverage} />
        <Metric label="Sample rate" value={result.metadata?.sample_rate ? `${result.metadata.sample_rate} Hz` : 'Unavailable'} />
        <Metric label="Feature set" value={(result.metadata?.feature_type || 'cqt').toUpperCase()} />
      </dl>

      <div className="report-actions">
        <button
          type="button"
          className="primary-action"
          onClick={togglePlayback}
          disabled={!hasAudio}
        >
          {isPlaying ? 'Pause playback' : 'Play synchronized audio'}
        </button>
        <span>{formatDuration(currentTime)} elapsed</span>
      </div>

      <div className="score-frame" aria-label="Synchronized tablature">
        <div className="score-label">
          <span>T</span>
          <span>A</span>
          <span>B</span>
        </div>
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

      <div className="report-notes">
        <h3>Interpretation</h3>
        <p>
          The output is a frame-level model estimate converted into guitar
          tablature. Use the synchronized score as a review surface before
          exporting or arranging the final transcription.
        </p>
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
    <svg viewBox={`0 0 ${totalWidth} 220`} className="score-svg" role="img">
      {Array.from({ length: Math.ceil(effectiveDuration / 2) + 1 }).map((_, index) => {
        const x = index * 2 * pixelsPerSecond
        return (
          <g key={`measure-${index}`}>
            <line x1={x} y1="26" x2={x} y2="172" className="measure-line" />
            <text x={x + 8} y="18" className="measure-label">{index * 2}s</text>
          </g>
        )
      })}

      {STRING_LABELS.map((label, index) => {
        const y = 42 + index * 24
        return (
          <g key={label}>
            <text x="16" y={y + 4} className="string-label">{label}</text>
            <line x1="36" y1={y} x2={totalWidth} y2={y} className="string-line" />
          </g>
        )
      })}

      {notes.map((note, index) => {
        const x = 36 + note.time * pixelsPerSecond
        const y = 42 + note.stringIdx * 24
        const isActive = activeNotes.some((active) => (
          active.time === note.time &&
          active.stringIdx === note.stringIdx &&
          active.fret === note.fret
        ))

        return (
          <g key={`${note.time}-${note.stringIdx}-${index}`}>
            <rect x={x - 9} y={y - 9} width="18" height="18" className="note-mask" />
            {isActive && <rect x={x - 10} y={y - 10} width="20" height="20" className="active-note-box" />}
            <text x={x} y={y + 4} className={isActive ? 'note-text active-note-text' : 'note-text'}>
              {note.fret}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

function averageConfidence(confidence?: number[][]): string {
  const values = confidence?.flat().filter((value) => Number.isFinite(value)) || []
  if (values.length === 0) return 'Unavailable'
  const average = values.reduce((sum, value) => sum + value, 0) / values.length
  return `${Math.round(average * 100)} / 100`
}

function maxNoteTime(notes: TranscribedNote[]): number {
  return notes.length ? Math.max(...notes.map((note) => note.time)) : 0
}
