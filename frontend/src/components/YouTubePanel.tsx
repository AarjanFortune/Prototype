import { useState } from 'react'
import { transcribeYoutube } from '../services/transcriptionApi'
import { FeatureType, TranscriptionResult } from '../types/transcription'
import { mapBackendNotes } from '../utils/formatTranscription'
import AnalysisControls from './AnalysisControls'
import ProgressMeter from './ProgressMeter'

interface YouTubePanelProps {
  featureType: FeatureType
  onFeatureTypeChange: (featureType: FeatureType) => void
  onComplete: (result: TranscriptionResult) => void
}

export default function YouTubePanel({
  featureType,
  onFeatureTypeChange,
  onComplete,
}: YouTubePanelProps) {
  const [url, setUrl] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    const trimmedUrl = url.trim()
    if (!trimmedUrl) return

    setIsProcessing(true)
    setError('')

    try {
      const payload = await transcribeYoutube(trimmedUrl, featureType)
      if (!payload.audio_url) {
        throw new Error('Backend did not return playable audio for this result.')
      }
      onComplete({
        notes: mapBackendNotes(payload),
        metadata: payload.metadata,
        source: payload.source,
        audioUrl: payload.audio_url,
        confidence: payload.confidence || [],
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to process this YouTube link.')
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <section className="input-section" aria-labelledby="youtube-title">
      <div className="section-heading">
        <span>YouTube</span>
        <h1 id="youtube-title">Paste a link</h1>
      </div>

      <div className="form-stack">
        <label className="field">
          <span className="field-label">YouTube URL</span>
          <input
            type="url"
            className="text-input"
            value={url}
            onChange={(event) => {
              setUrl(event.target.value)
              setError('')
            }}
          />
        </label>

        <AnalysisControls featureType={featureType} onFeatureTypeChange={onFeatureTypeChange} />

        {error && <p className="form-error">{error}</p>}
        <ProgressMeter active={isProcessing} />

        <button
          type="button"
          className="primary-action"
          disabled={!url.trim() || isProcessing}
          onClick={handleSubmit}
        >
          {isProcessing ? 'Transcribing' : 'Transcribe'}
        </button>
      </div>
    </section>
  )
}
