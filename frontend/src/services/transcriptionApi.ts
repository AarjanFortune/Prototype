import { FeatureType } from '../types/transcription'

const API_BASE = ''

async function parseResponse(response: Response) {
  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    const message = payload?.detail || payload?.error || `Request failed with status ${response.status}`
    throw new Error(message)
  }

  if (payload?.status === 'error') {
    throw new Error(payload.error || 'Transcription failed')
  }

  return payload
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
