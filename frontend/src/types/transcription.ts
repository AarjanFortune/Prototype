export type SourceType = 'upload' | 'youtube' | 'live'
export type FeatureType = 'cqt' | 'mel'

export interface TranscribedNote {
  stringIdx: number
  fret: number
  time: number
}

export interface BackendMetadata {
  duration: number
  sample_rate: number
  n_frames: number
  tempo: number
  feature_type: string
}

export interface BackendSourceMetadata {
  kind: 'upload' | 'youtube'
  name: string
  size_bytes: number
  url?: string | null
}

export interface BackendTranscriptionResponse {
  status: 'success'
  source: BackendSourceMetadata
  tab?: unknown[]
  pitch?: unknown[]
  confidence?: number[][]
  pianoroll?: {
    notes?: unknown[]
    total_duration?: number
  }
  metadata: BackendMetadata
  audio_url?: string | null
}

export interface TranscriptionResult {
  notes: TranscribedNote[]
  metadata: BackendMetadata
  source: BackendSourceMetadata
  audioUrl?: string | null
  sourceFile?: File | null
  confidence?: number[][]
}
