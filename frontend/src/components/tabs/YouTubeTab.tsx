import { useState } from 'react'

export default function YouTubeTab() {
  const [url, setUrl] = useState('')
  const [processingMethod, setProcessingMethod] = useState('cqt')

  const containerLayout: React.CSSProperties = {
    width: '100%',
    maxWidth: '560px',
    textAlign: 'center',
    display: 'flex',
    flexDirection: 'column',
    gap: '24px'
  }

  return (
    <div style={containerLayout}>
      <div>
        <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.8rem', fontWeight: 400, marginBottom: '6px' }}>
          Transcribe from YouTube
        </h2>
        <p style={{ fontSize: '0.8rem', color: 'var(--color-muted)' }}>
          Paste a video link to extract performance tablature
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.15em', color: 'var(--color-muted)' }}>Video URL</label>
          <input 
            type="text" 
            style={{ width: '100%', background: 'transparent', border: 'none', borderBottom: '1px solid var(--color-muted)', padding: '6px 0', fontSize: '0.9rem', outline: 'none', textAlign: 'center' }} 
            placeholder="https://www.youtube.com/watch?v=..." 
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.15em', color: 'var(--color-muted)' }}>Processing Method</label>
          <select 
            style={{ background: 'transparent', border: 'none', borderBottom: '1px solid var(--color-ink)', padding: '4px 12px', fontSize: '0.85rem', outline: 'none', cursor: 'pointer', textAlignLast: 'center' }}
            value={processingMethod} 
            onChange={(e) => setProcessingMethod(e.target.value)}
          >
            <option value="cqt">Constant-Q Transform</option>
            <option value="mel">Mel-Spectrogram</option>
          </select>
        </div>

        <button 
          className="btn-primary"
          disabled={!url}
          style={{ alignSelf: 'center', marginTop: '10px' }}
        >
          Transcribe YouTube Audio
        </button>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--color-border)', paddingTop: '16px', marginTop: '12px' }}>
        <div style={{ textAlign: 'left', width: '48%' }}>
          <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--color-muted)', fontWeight: 600 }}>Fidelity</span>
          <p style={{ fontSize: '0.75rem', color: 'var(--color-muted)', marginTop: '2px' }}>Uses premium high-resolution playback data.</p>
        </div>
        <div style={{ textAlign: 'right', width: '48%' }}>
          <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--color-muted)', fontWeight: 600 }}>Limits</span>
          <p style={{ fontSize: '0.75rem', color: 'var(--color-muted)', marginTop: '2px' }}>Optimized for video files up to 10 minutes.</p>
        </div>
      </div>
    </div>
  )
}