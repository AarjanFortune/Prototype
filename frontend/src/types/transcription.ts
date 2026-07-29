export type SourceType = 'upload' | 'youtube' | 'live'
export type FeatureType = 'cqt' | 'mel'

export interface TranscribedNote {
  stringIdx: number
  fret: number
  time: number
}

export interface BackendMetadata {
  duration?: number
  sample_rate?: number
  n_frames?: number
  tempo?: number
  feature_type?: string
}

export interface TranscriptionResult {
  notes: TranscribedNote[]
  metadata: BackendMetadata | null
  audioUrl?: string | null
  sourceFile?: File | null
  confidence?: number[][]
  fileName: string
  fileSize: string
}
