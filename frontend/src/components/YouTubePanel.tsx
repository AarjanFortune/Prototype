import { useState } from 'react'
import { transcribeYoutube } from '../services/transcriptionApi'
import { FeatureType, TranscriptionResult } from '../types/transcription'
import { mapBackendNotes } from '../utils/formatTranscription'
import AnalysisControls from './AnalysisControls'

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
      onComplete({
        notes: mapBackendNotes(payload),
        metadata: payload.metadata || null,
        audioUrl: payload.audio_url || null,
        confidence: payload.confidence || [],
        fileName: 'YouTube source',
        fileSize: 'Extracted audio',
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
        <p className="section-kicker">YouTube source</p>
        <h2 id="youtube-title">Analyze a single YouTube performance.</h2>
        <p>
          Supports standard watch URLs, Shorts, live links, embeds, and youtu.be
          links. Playlist-only links are rejected to keep the report scoped.
        </p>
      </div>

      <div className="form-stack">
        <label className="field">
          <span className="field-label">YouTube URL</span>
          <input
            type="url"
            className="text-input"
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(event) => {
              setUrl(event.target.value)
              setError('')
            }}
          />
        </label>

        <AnalysisControls featureType={featureType} onFeatureTypeChange={onFeatureTypeChange} />

        {error && <p className="form-error">{error}</p>}

        <button
          type="button"
          className="primary-action"
          disabled={!url.trim() || isProcessing}
          onClick={handleSubmit}
        >
          {isProcessing ? 'Extracting and transcribing' : 'Run transcription'}
        </button>
      </div>
    </section>
  )
}
