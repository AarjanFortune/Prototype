import { useState } from 'react'
import './App.css'
import LiveInputPanel from './components/LiveInputPanel'
import SourceTabs from './components/SourceTabs'
import TranscriptionReport from './components/TranscriptionReport'
import UploadPanel from './components/UploadPanel'
import YouTubePanel from './components/YouTubePanel'
import { FeatureType, SourceType, TranscriptionResult } from './types/transcription'

export default function App() {
  const [activeSource, setActiveSource] = useState<SourceType>('upload')
  const [featureType, setFeatureType] = useState<FeatureType>('cqt')
  const [result, setResult] = useState<TranscriptionResult | null>(null)

  const reset = () => setResult(null)

  return (
    <main className="app-shell">
      <section className="hero" aria-labelledby="app-title">
        <div>
          <p className="section-kicker">Guitarica</p>
          <h1 id="app-title">Guitar transcription, presented as analysis.</h1>
        </div>
        <p>
          Convert recorded or streamed guitar performances into synchronized
          tablature with a review surface designed for careful listening.
        </p>
      </section>

      {!result && (
        <div className="workspace">
          <SourceTabs activeSource={activeSource} onChange={setActiveSource} />

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
