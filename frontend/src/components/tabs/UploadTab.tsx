import axios from 'axios'
import { useState } from 'react'
import { CombinedViewer } from '../CombinedViewer'
import LoadingSpinner from '../LoadingSpinner'

interface TranscriptionResult {
  status: string
  tab: string[]
  confidence: number[][]
  metadata: { duration: number; tempo: number; n_frames: number; feature_type: string }
}

export default function UploadTab() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<TranscriptionResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [processingMethod, setProcessingMethod] = useState('cqt')

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      setFile(selectedFile)
      setError(null)
    }
  }

  const handleTranscribe = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('feature_type', processingMethod)
      const response = await axios.post<TranscriptionResult>('/api/transcribe/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      if (response.data.status === 'success') setResult(response.data)
    } catch (err) {
      setError('Unable to analyze this audio file.')
    } finally {
      setLoading(false)
    }
  }

  // --- Inline Clean Styles ---
  const wrapperStyle: React.CSSProperties = { width: '100%', maxWidth: '640px', textAlign: 'center' }
  const titleStyle: React.CSSProperties = { fontFamily: 'var(--font-serif)', fontSize: '2rem', fontWeight: 400, marginBottom: '8px' }
  const subtitleStyle: React.CSSProperties = { fontSize: '0.85rem', color: 'var(--color-muted)', marginBottom: '40px' }
  const groupStyle: React.CSSProperties = { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', marginBottom: '32px' }
  const labelStyle: React.CSSProperties = { fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.15em', color: 'var(--color-muted)' }
  
  const selectStyle: React.CSSProperties = {
    background: 'transparent', border: 'none', borderBottom: '1px solid var(--color-ink)',
    padding: '6px 16px', fontSize: '0.9rem', outline: 'none', cursor: 'pointer', textAlignLast: 'center'
  }

  const fileInputWrapper: React.CSSProperties = {
    borderBottom: '1px solid var(--color-muted)', display: 'inline-block', padding: '8px 0',
    margin: '24px 0', color: 'var(--color-muted)', fontSize: '0.9rem', cursor: 'pointer', position: 'relative'
  }

  const actionButtonStyle: React.CSSProperties = {
    background: 'var(--color-ink)', color: '#ffffff', border: 'none', padding: '14px 44px',
    fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.2em',
    cursor: 'pointer', marginTop: '24px', transition: 'opacity 0.2s'
  }

  return (
    <div style={wrapperStyle}>
      <h2 style={titleStyle}>Convert Audio to Tablature</h2>
      <p style={subtitleStyle}>Select an audio file from your device to automatically generate guitar tabs</p>
      
      <div>
        <div style={groupStyle}>
          <label style={labelStyle}>Processing Method</label>
          <select 
            style={selectStyle} 
            value={processingMethod} 
            onChange={(e) => setProcessingMethod(e.target.value)}
          >
            <option value="cqt">Constant-Q Transform</option>
            <option value="mel">Mel Spectrogram</option>
          </select>
        </div>

        <div style={{ margin: '32px 0' }}>
          <label style={fileInputWrapper}>
            <input type="file" accept="audio/*" onChange={handleFileChange} style={{ display: 'none' }} />
            {file ? file.name : 'Choose an audio file'}
          </label>
        </div>

        {error && <p style={{ color: '#c94b4b', fontSize: '0.8rem', margin: '16px 0' }}>{error}</p>}

        <button 
          style={{ ...actionButtonStyle, opacity: (!file || loading) ? 0.4 : 1 }}
          onClick={handleTranscribe}
          disabled={!file || loading}
        >
          {loading ? 'Analyzing...' : 'Analyze Audio'}
        </button>
      </div>

      {loading && <div style={{ marginTop: '40px' }}><LoadingSpinner /></div>}

      {result && (
        <div style={{ marginTop: '60px', borderTop: '1px solid var(--color-border)', paddingTop: '40px' }}>
          <CombinedViewer tabData={result.tab} confidenceData={result.confidence} />
        </div>
      )}
    </div>
  )
}