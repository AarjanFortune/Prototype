import axios from 'axios'
import { useState } from 'react'
import './UploadTab.css'
import { CombinedViewer } from '../CombinedViewer'
import LoadingSpinner from '../LoadingSpinner'

interface PianorollNote {
  midi: number
  string: number
  fret: number
  start_time: number
  duration: number
}

interface TranscriptionResult {
  status: string
  tab: string[]
  confidence: number[][]
  pianoroll?: {
    notes: PianorollNote[]
    total_duration: number
  }
  metadata: {
    duration: number
    sample_rate: number
    n_frames: number
    tempo: number
    feature_type: string
  }
  error?: string
}

export default function UploadTab() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<TranscriptionResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [featureType, setFeatureType] = useState('cqt')

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      const validTypes = ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/flac', 'audio/mp4']
      if (!validTypes.some(type => selectedFile.type.includes(type.split('/')[1]))) {
        setError('Please upload an audio file (mp3, wav, ogg, flac, m4a)')
        return
      }
      setFile(selectedFile)
      setError(null)
    }
  }

  const handleTranscribe = async () => {
    if (!file) {
      setError('Please select a file first')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('feature_type', featureType)

      const response = await axios.post<TranscriptionResult>('/api/transcribe/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      if (response.data.status === 'success') {
        setResult(response.data)
      } else {
        setError(response.data.error || 'Transcription failed')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to transcribe audio')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="upload-tab">
      <div className="upload-container">
        <div className="upload-card">
          <h2>Upload Audio File</h2>
          
          <div className="upload-form">
            <div className="form-group">
              <label htmlFor="feature-type">Feature Type:</label>
              <select
                id="feature-type"
                value={featureType}
                onChange={(e) => setFeatureType(e.target.value)}
                disabled={loading}
              >
                <option value="cqt">CQT (Constant-Q Transform)</option>
                <option value="mel">Mel-Spectrogram</option>
              </select>
            </div>

            <div className="file-input-wrapper">
              <input
                type="file"
                id="file-input"
                accept="audio/*"
                onChange={handleFileChange}
                disabled={loading}
              />
              <label htmlFor="file-input" className="file-label">
                {file ? `📁 ${file.name}` : '📁 Click to select audio file'}
              </label>
            </div>

            {file && (
              <div className="file-info">
                <p>File: <strong>{file.name}</strong></p>
                <p>Size: <strong>{(file.size / 1024 / 1024).toFixed(2)} MB</strong></p>
              </div>
            )}

            {error && <div className="error-message">{error}</div>}

            <button
              className="transcribe-button"
              onClick={handleTranscribe}
              disabled={!file || loading}
            >
              {loading ? 'Transcribing...' : '🎵 Transcribe'}
            </button>
          </div>
        </div>

        {loading && <LoadingSpinner />}

        {result && (
          <div className="results-container">
            <div className="metadata">
              <h3>Audio Information</h3>
              <div className="metadata-grid">
                <div className="metadata-item">
                  <span className="label">Duration:</span>
                  <span className="value">{result.metadata.duration.toFixed(2)}s</span>
                </div>
                <div className="metadata-item">
                  <span className="label">Tempo:</span>
                  <span className="value">{result.metadata.tempo.toFixed(0)} BPM</span>
                </div>
                <div className="metadata-item">
                  <span className="label">Frames:</span>
                  <span className="value">{result.metadata.n_frames}</span>
                </div>
                <div className="metadata-item">
                  <span className="label">Feature Type:</span>
                  <span className="value">{result.metadata.feature_type.toUpperCase()}</span>
                </div>
              </div>
            </div>

            <CombinedViewer
              tabData={result.tab}
              confidenceData={result.confidence}
              pianorollData={result.pianoroll}
              metadata={{
                duration: result.metadata.duration,
                tempo: result.metadata.tempo,
                frames: result.metadata.n_frames,
              }}
            />
          </div>
        )}
      </div>
    </div>
  )
}
