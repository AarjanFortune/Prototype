import './Header.css'

export default function Header() {
  return (
    <header className="header">
      <div className="header-content">
        <div className="header-logo">
          <h1>🎸 Guitar Transcription</h1>
          <p>Automatic Music-to-Tab Conversion</p>
        </div>
        <div className="header-subtitle">
          <p>AI-powered guitar tablature generation from audio</p>
        </div>
      </div>
    </header>
  )
}
