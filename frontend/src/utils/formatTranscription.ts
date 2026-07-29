import { TranscribedNote } from '../types/transcription'

export function formatBytes(bytes: number): string {
  if (bytes <= 0) return '0 MB'
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export function mapBackendNotes(payload: any): TranscribedNote[] {
  const rawNotes = payload?.pianoroll?.notes
  if (!Array.isArray(rawNotes)) return []

  return rawNotes
    .map((note: any) => ({
      time: Number(note.start_time),
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
}

export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) throw new Error('Invalid duration from backend.')
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.round(seconds % 60).toString().padStart(2, '0')
  return `${minutes}:${remainingSeconds}`
}

export function formatTempo(tempo: number): string {
  if (!Number.isFinite(tempo)) throw new Error('Invalid tempo from backend.')
  return `${Math.round(tempo)} BPM`
}
