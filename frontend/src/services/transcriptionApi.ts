import { BackendTranscriptionResponse, FeatureType } from '../types/transcription'

const API_BASE = ''

async function parseResponse(response: Response): Promise<BackendTranscriptionResponse> {
  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    const message = payload?.detail || payload?.error || `Request failed with status ${response.status}`
    throw new Error(message)
  }

  if (payload?.status === 'error') {
    throw new Error(payload.error || 'Transcription failed')
  }

  if (
    payload?.status !== 'success' ||
    !payload.source ||
    typeof payload.source.name !== 'string' ||
    payload.source.name.trim().length === 0 ||
    typeof payload.source.size_bytes !== 'number' ||
    !payload.metadata ||
    typeof payload.metadata.duration !== 'number' ||
    typeof payload.metadata.sample_rate !== 'number' ||
    typeof payload.metadata.n_frames !== 'number' ||
    typeof payload.metadata.tempo !== 'number' ||
    typeof payload.metadata.feature_type !== 'string' ||
    !Array.isArray(payload?.pianoroll?.notes)
  ) {
    throw new Error('Backend returned an incomplete transcription result.')
  }

  return payload as BackendTranscriptionResponse
}

export async function transcribeUpload(file: File, featureType: FeatureType) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('feature_type', featureType)

  const response = await fetch(`${API_BASE}/api/transcribe/upload`, {
    method: 'POST',
    body: formData,
  })

  return parseResponse(response)
}

export async function transcribeYoutube(url: string, featureType: FeatureType) {
  const response = await fetch(`${API_BASE}/api/transcribe/youtube`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, feature_type: featureType }),
  })

  return parseResponse(response)
}
