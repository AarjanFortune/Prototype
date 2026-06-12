import './Navigation.css'

interface NavigationProps {
  activeTab: string
  onTabChange: (tab: 'upload' | 'youtube' | 'live') => void
}

export default function Navigation({ activeTab, onTabChange }: NavigationProps) {
  return (
    <nav className="navigation">
      <div className="nav-container">
        <button
          className={`nav-button ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => onTabChange('upload')}
        >
          📁 Upload File
        </button>
        <button
          className={`nav-button ${activeTab === 'youtube' ? 'active' : ''}`}
          onClick={() => onTabChange('youtube')}
        >
          🎬 YouTube Link
        </button>
        <button
          className={`nav-button ${activeTab === 'live' ? 'active' : ''}`}
          onClick={() => onTabChange('live')}
        >
          🎙️ Live Stream
        </button>
      </div>
    </nav>
  )
}
