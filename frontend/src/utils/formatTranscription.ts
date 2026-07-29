import { BackendMetadata, TranscribedNote } from '../types/transcription'

export function formatBytes(bytes: number): string {
  if (bytes <= 0) return '0 MB'
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export function mapBackendNotes(payload: any): TranscribedNote[] {
  const rawNotes = payload?.pianoroll?.notes
  if (!Array.isArray(rawNotes)) return []

  const metadata: BackendMetadata = payload.metadata || {}
  const audioDuration = metadata.duration || 0
  const pianorollDuration = payload.pianoroll?.total_duration || 0
  const timeScale = audioDuration > 0 && pianorollDuration > 0 ? audioDuration / pianorollDuration : 1

  const notes = rawNotes
    .map((note: any) => ({
      time: Number(note.start_time) * timeScale,
      stringIdx: 5 - Number(note.string),
      fret: Number(note.fret),
    }))
    .filter((note: TranscribedNote) => (
      Number.isFinite(note.time) &&
      Number.isFinite(note.stringIdx) &&
      Number.isFinite(note.fret) &&
      note.stringIdx >= 0 &&
      note.stringIdx <= 5 &&
      note.fret >= 0
    ))
    .sort((a: TranscribedNote, b: TranscribedNote) => a.time - b.time)

  return dedupeNotes(notes)
}

function dedupeNotes(notes: TranscribedNote[]): TranscribedNote[] {
  const result: TranscribedNote[] = []
  const minGapSeconds = 0.08

  notes.forEach((note) => {
    const previous = [...result].reverse().find((item) => item.stringIdx === note.stringIdx)
    if (!previous || note.time - previous.time >= minGapSeconds) {
      result.push(note)
    }
  })

  return result
}

export function formatDuration(seconds?: number): string {
  if (!seconds || seconds < 0) return 'Unavailable'
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.round(seconds % 60).toString().padStart(2, '0')
  return `${minutes}:${remainingSeconds}`
}

export function formatTempo(tempo?: number): string {
  return tempo ? `${Math.round(tempo)} BPM` : 'Unavailable'
}
