import React from 'react'

type TabType = 'upload' | 'youtube' | 'live'

interface NavigationProps {
  activeTab: TabType
  onTabChange: (tab: TabType) => void
}

export default function Navigation({ activeTab, onTabChange }: NavigationProps) {
  const navStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'center',
    gap: '48px',
    padding: '24px 0 0 0',
    width: '100%'
  }

  const getLinkStyle = (isActive: boolean): React.CSSProperties => ({
    background: 'none',
    border: 'none',
    fontFamily: 'var(--font-sans)',
    fontSize: '0.75rem',
    fontWeight: isActive ? 600 : 400,
    textTransform: 'uppercase',
    letterSpacing: '0.2em',
    color: isActive ? 'var(--color-ink)' : 'var(--color-muted)',
    cursor: 'pointer',
    padding: '8px 0',
    borderBottom: isActive ? '1px solid var(--color-ink)' : '1px solid transparent',
    transition: 'all 0.3s ease'
  })

  return (
    <nav style={navStyle}>
      <button 
        style={getLinkStyle(activeTab === 'upload')}
        onClick={() => onTabChange('upload')}
      >
        Upload File
      </button>
      <button 
        style={getLinkStyle(activeTab === 'youtube')}
        onClick={() => onTabChange('youtube')}
      >
        YouTube Link
      </button>
      <button 
        style={getLinkStyle(activeTab === 'live')}
        onClick={() => onTabChange('live')}
      >
        Live Stream
      </button>
    </nav>
  )
}