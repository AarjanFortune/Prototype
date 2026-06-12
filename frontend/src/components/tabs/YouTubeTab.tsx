import axios from 'axios'
import { useState } from 'react'
import './YouTubeTab.css'
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

export default function YouTubeTab() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<TranscriptionResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [featureType, setFeatureType] = useState('cqt')

  const handleTranscribe = async () => {
    if (!url.trim()) {
      setError('Please enter a YouTube URL')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await axios.post<TranscriptionResult>('/api/transcribe/youtube', {
        url: url.trim(),
        feature_type: featureType,
      })

      if (response.data.status === 'success') {
        setResult(response.data)
      } else {
        setError(response.data.error || 'Transcription failed')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to transcribe YouTube video')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="youtube-tab">
      <div className="youtube-container">
        <div className="youtube-card">
          <h2>Transcribe from YouTube</h2>
          
          <div className="youtube-form">
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

            <div className="url-input-group">
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=..."
                disabled={loading}
                className="url-input"
              />
            </div>

            {error && <div className="error-message">{error}</div>}

            <button
              className="transcribe-button"
              onClick={handleTranscribe}
              disabled={!url.trim() || loading}
            >
              {loading ? 'Downloading & Transcribing...' : '🎬 Transcribe YouTube'}
            </button>

            <div className="info-box">
              <p><strong>⏱️ Supported Video Length:</strong> Up to 10 minutes</p>
              <p><strong>🎵 Audio Quality:</strong> Best available from YouTube</p>
              <p><strong>💡 Tip:</strong> Paste any YouTube link to transcribe the guitar playing</p>
            </div>
          </div>
        </div>

        {loading && <LoadingSpinner message="Downloading and processing video..." />}

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
