import { useState } from 'react'

export default function LiveStreamTab() {
  const [recording, setRecording] = useState(false)
  const [tempo, setTempo] = useState(120)

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
          Live Recording
        </h2>
        <p style={{ fontSize: '0.8rem', color: 'var(--color-muted)' }}>
          Capture audio input through your microphone to map pitch frequencies instantly
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.15em', color: 'var(--color-muted)' }}>Target Tempo (BPM)</label>
          <input 
            type="number" 
            style={{ background: 'transparent', border: 'none', borderBottom: '1px solid var(--color-ink)', width: '60px', padding: '4px 0', fontSize: '1rem', textAlign: 'center', outline: 'none' }} 
            value={tempo} 
            onChange={(e) => setTempo(parseInt(e.target.value) || 120)}
            disabled={recording}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', color: recording ? '#c94b4b' : 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#c94b4b', opacity: recording ? 1 : 0.4 }} />
          <span>{recording ? 'Active Session Live' : 'Ready'}</span>
        </div>

        <button 
          className="btn-primary" 
          onClick={() => setRecording(!recording)}
          style={{ background: recording ? '#c94b4b' : 'var(--color-ink)' }}
        >
          {recording ? 'Stop Recording' : 'Start Recording'}
        </button>
      </div>

      <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '16px', textAlign: 'left', marginTop: '12px' }}>
        <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.15em', color: 'var(--color-muted)' }}>Dynamic Tracking</span>
        <p style={{ fontSize: '0.75rem', color: 'var(--color-muted)', marginTop: '4px', lineHeight: '1.4' }}>
          Position your instrument near the system microphone. The system processes note transients continuously without storing audio blocks.
        </p>
      </div>
    </div>
  )
}