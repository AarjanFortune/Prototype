import { useRef, useState } from 'react'
import { transcribeUpload } from '../services/transcriptionApi'
import { FeatureType, TranscriptionResult } from '../types/transcription'
import { formatBytes, mapBackendNotes } from '../utils/formatTranscription'
import AnalysisControls from './AnalysisControls'
import ProgressMeter from './ProgressMeter'

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
        <span>Audio file</span>
        <h1 id="upload-title">Select audio</h1>
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
          <button type="button" className="secondary-action" onClick={() => inputRef.current?.click()}>
            Choose file
          </button>
          <span className="file-summary">
            {file ? `${file.name} / ${formatBytes(file.size)}` : 'MP3, WAV, FLAC, OGG, M4A or AAC'}
          </span>
        </div>

        <AnalysisControls featureType={featureType} onFeatureTypeChange={onFeatureTypeChange} />

        {error && <p className="form-error">{error}</p>}
        <ProgressMeter active={isProcessing} />

        <button
          type="button"
          className="primary-action"
          disabled={!file || isProcessing}
          onClick={handleSubmit}
        >
          {isProcessing ? 'Transcribing' : 'Transcribe'}
        </button>
      </div>
    </section>
  )
}
