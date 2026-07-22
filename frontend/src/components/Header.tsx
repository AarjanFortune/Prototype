import React from 'react'

export default function Header() {
  const headerStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    width: '100%',
    paddingBottom: '32px',
    borderBottom: '1px solid var(--color-border)',
    position: 'relative'
  }

  const logoStyle: React.CSSProperties = {
    fontFamily: 'var(--font-serif)',
    fontWeight: 600,
    fontSize: '1.5rem',
    letterSpacing: '0.05em'
  }

  const scriptStyle: React.CSSProperties = {
    fontFamily: 'var(--font-cursive)',
    fontSize: '2.5rem',
    color: 'var(--color-muted)',
    position: 'absolute',
    left: '50%',
    transform: 'translateX(-50%)',
    opacity: 0.6,
    pointerEvents: 'none'
  }

  const metaStyle: React.CSSProperties = {
    fontSize: '0.75rem',
    textTransform: 'uppercase',
    letterSpacing: '0.15em',
    color: 'var(--color-muted)'
  }

  return (
    <header style={headerStyle}>
      <div style={logoStyle}>Guitarica</div>
      <div style={scriptStyle}>Silhouette</div>
      <div style={metaStyle}>Transcription Studio</div>
    </header>
  )
}