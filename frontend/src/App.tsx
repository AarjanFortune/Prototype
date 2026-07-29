import { useState } from 'react'
import './App.css'
import IntroLoader from './components/IntroLoader'
import LiveInputPanel from './components/LiveInputPanel'
import SourceMenu from './components/SourceMenu'
import SourceTabs from './components/SourceTabs'
import TranscriptionReport from './components/TranscriptionReport'
import UploadPanel from './components/UploadPanel'
import YouTubePanel from './components/YouTubePanel'
import { FeatureType, SourceType, TranscriptionResult } from './types/transcription'

export default function App() {
  const [showLoader, setShowLoader] = useState(true)
  const [view, setView] = useState<'menu' | 'studio'>('menu')
  const [activeSource, setActiveSource] = useState<SourceType>('upload')
  const [featureType, setFeatureType] = useState<FeatureType>('cqt')
  const [result, setResult] = useState<TranscriptionResult | null>(null)

  const reset = () => setResult(null)

  const openSource = (source: SourceType) => {
    setActiveSource(source)
    setResult(null)
    setView('studio')
  }

  const openMenu = () => {
    setResult(null)
    setView('menu')
  }

  return (
    <main className="app-shell">
      {showLoader && <IntroLoader onComplete={() => setShowLoader(false)} />}

      <header className="studio-header">
        <button type="button" className="brand-home" onClick={openMenu} aria-label="Guitarica home">
          <img src="/images/logo.svg" alt="Guitarica" />
        </button>
        {view === 'studio' && !result && (
          <SourceTabs activeSource={activeSource} onChange={setActiveSource} />
        )}
        <span className="header-note">Guitar transcription</span>
      </header>

      {!result && view === 'menu' && <SourceMenu onSelect={openSource} />}

      {!result && view === 'studio' && (
        <div className={`workspace workspace-${activeSource}`}>
          <div className="workspace-art" aria-hidden="true">
            <span>{activeSource === 'upload' ? '01' : activeSource === 'youtube' ? '02' : '03'}</span>
            <img src="/images/Guitarica.png" alt="" />
          </div>
          {activeSource === 'upload' && (
            <UploadPanel
              featureType={featureType}
              onFeatureTypeChange={setFeatureType}
              onComplete={setResult}
            />
          )}

          {activeSource === 'youtube' && (
            <YouTubePanel
              featureType={featureType}
              onFeatureTypeChange={setFeatureType}
              onComplete={setResult}
            />
          )}

          {activeSource === 'live' && <LiveInputPanel />}
        </div>
      )}

      {result && <TranscriptionReport result={result} onReset={reset} />}
    </main>
  )
}
