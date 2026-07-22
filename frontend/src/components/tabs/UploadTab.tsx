import React, { useState } from 'react'
import TablatureViewer from '../studio/TablatureViewer'

export default function UploadTab() {
  const [file, setFile] = useState<File | null>(null)
  const [status, setStatus] = useState<'idle' | 'processing' | 'complete'>('idle')
  const [tabData, setTabData] = useState<string>('')

  const handleProcess = () => {
    if (!file) return
    setStatus('processing')

    // Replace with your actual backend API call
    setTimeout(() => {
      setTabData(
        `e|--12--10--------------------|--12--10--------------------|\nB|----------12--10------------|----------12--10------------|\nG|------------------12--9--7~-|------------------12--9--7~-|\nD|----------------------------|----------------------------|\nA|----------------------------|----------------------------|\nE|----------------------------|----------------------------|`
      )
      setStatus('complete')
    }, 2200)
  }

  return (
    <div style={{ width: '100%', paddingBottom: '32px' }}>
      <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--color-ink, #1d1d1f)', marginBottom: '6px', letterSpacing: '-0.02em' }}>
        Convert Audio to Tablature
      </h2>
      <p style={{ fontSize: '0.8rem', color: '#8e8e93', marginBottom: '24px' }}>
        Select an audio file from your device to perform neural pitch estimation and generate guitar tabs.
      </p>

      <div style={{ marginBottom: '20px' }}>
        <input 
          type="file" 
          accept="audio/*"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          style={{ fontSize: '0.8rem', color: '#1d1d1f' }}
        />
      </div>

      <button
        onClick={handleProcess}
        disabled={!file || status === 'processing'}
        style={{
          width: '100%',
          padding: '12px',
          background: status === 'processing' ? '#8e8e93' : '#1d1d1f',
          color: '#ffffff',
          border: 'none',
          borderRadius: '8px',
          fontWeight: 600,
          fontSize: '0.75rem',
          letterSpacing: '0.05em',
          textTransform: 'uppercase',
          cursor: status === 'processing' ? 'not-allowed' : 'pointer'
        }}
      >
        {status === 'processing' ? 'Analyzing Audio Spectrum...' : 'Analyze Audio'}
      </button>

      {status === 'complete' && <TablatureViewer content={tabData} />}
    </div>
  )
}