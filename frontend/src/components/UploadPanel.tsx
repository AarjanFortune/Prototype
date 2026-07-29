import { useRef, useState } from 'react'
import { transcribeUpload } from '../services/transcriptionApi'
import { FeatureType, TranscriptionResult } from '../types/transcription'
import { formatBytes, mapBackendNotes } from '../utils/formatTranscription'
import AnalysisControls from './AnalysisControls'

interface UploadPanelProps {
  featureType: FeatureType
  onFeatureTypeChange: (featureType: FeatureType) => void
  onComplete: (result: TranscriptionResult) => void
}

export default function UploadPanel({
  featureType,
  onFeatureTypeChange,
  onComplete,
}: UploadPanelProps) {
  const [file, setFile] = useState<File | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement | null>(null)

  const handleSubmit = async () => {
    if (!file) return
    setIsProcessing(true)
    setError('')

    try {
      const payload = await transcribeUpload(file, featureType)
      onComplete({
        notes: mapBackendNotes(payload),
        metadata: payload.metadata || null,
        audioUrl: null,
        sourceFile: file,
        confidence: payload.confidence || [],
        fileName: file.name,
        fileSize: formatBytes(file.size),
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to transcribe this file.')
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <section className="input-section" aria-labelledby="upload-title">
      <div className="section-heading">
        <p className="section-kicker">Audio file</p>
        <h2 id="upload-title">Convert a performance into tablature.</h2>
        <p>
          Upload a clean guitar recording. The analysis returns synchronized tab,
          timing metadata, and a playable report.
        </p>
      </div>

      <div className="form-stack">
        <input
          ref={inputRef}
          type="file"
          accept="audio/*"
          className="visually-hidden"
          onChange={(event) => {
            setFile(event.target.files?.[0] || null)
            setError('')
          }}
        />

        <div className="file-row">
          <button type="button" className="text-action" onClick={() => inputRef.current?.click()}>
            Choose file
          </button>
          <span className="file-summary">
            {file ? `${file.name} / ${formatBytes(file.size)}` : 'MP3, WAV, FLAC, OGG, M4A, AAC'}
          </span>
        </div>

        <AnalysisControls featureType={featureType} onFeatureTypeChange={onFeatureTypeChange} />

        {error && <p className="form-error">{error}</p>}

        <button
          type="button"
          className="primary-action"
          disabled={!file || isProcessing}
          onClick={handleSubmit}
        >
          {isProcessing ? 'Transcribing' : 'Run transcription'}
        </button>
      </div>
    </section>
  )
}
