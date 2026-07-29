import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'
import IntroLoader from './components/IntroLoader'
import LiveInputPanel from './components/LiveInputPanel'
import SourceMenu from './components/SourceMenu'
import SourceTabs from './components/SourceTabs'
import TranscriptionReport from './components/TranscriptionReport'
import UploadPanel from './components/UploadPanel'
import VisualCalibrator from './components/VisualCalibrator'
import YouTubePanel from './components/YouTubePanel'
import { FeatureType, SourceType, TranscriptionResult } from './types/transcription'
import {
  DEFAULT_VISUAL_CONFIG,
  mergeVisualConfig,
  VisualConfig,
  visualStyle,
} from './visualConfig'

const VISUAL_CONFIG_KEY = 'guitarica.visual-config.v1'

export default function App() {
  const [showLoader, setShowLoader] = useState(true)
  const [view, setView] = useState<'menu' | 'studio'>('menu')
  const [activeSource, setActiveSource] = useState<SourceType>('upload')
  const [featureType, setFeatureType] = useState<FeatureType>('cqt')
  const [result, setResult] = useState<TranscriptionResult | null>(null)
  const [showCalibrator, setShowCalibrator] = useState(false)
  const [visualConfig, setVisualConfig] = useState<VisualConfig>(() => {
    try {
      return mergeVisualConfig(JSON.parse(localStorage.getItem(VISUAL_CONFIG_KEY) || 'null'))
    } catch {
      return DEFAULT_VISUAL_CONFIG
    }
  })
  const soundRef = useRef<HTMLAudioElement | null>(null)
  const soundUnlockedRef = useRef(false)
  const debugSequenceRef = useRef('')

  useEffect(() => {
    const sound = new Audio('/images/GEF.wav')
    sound.preload = 'auto'
    sound.volume = 0.55
    soundRef.current = sound
    return () => {
      sound.pause()
      soundRef.current = null
    }
  }, [])

  useEffect(() => {
    localStorage.setItem(VISUAL_CONFIG_KEY, JSON.stringify(visualConfig))
  }, [visualConfig])

  useEffect(() => {
    const handleDebugShortcut = (event: KeyboardEvent) => {
      if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === 'd') {
        event.preventDefault()
        setShowCalibrator((current) => !current)
        return
      }

      const activeTag = document.activeElement?.tagName.toLowerCase()
      if (activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select') return
      debugSequenceRef.current = `${debugSequenceRef.current}${event.key.toLowerCase()}`.slice(-10)
      if (debugSequenceRef.current === 'studiomode') {
        setShowCalibrator((current) => !current)
        debugSequenceRef.current = ''
      }
    }

    window.addEventListener('keydown', handleDebugShortcut)
    return () => window.removeEventListener('keydown', handleDebugShortcut)
  }, [])

  const playFeedback = useCallback(() => {
    const sound = soundRef.current
    if (!sound) return
    sound.currentTime = 0
    sound.play().catch(() => undefined)
  }, [])

  const unlockFeedback = useCallback(() => {
    const sound = soundRef.current
    if (!sound || soundUnlockedRef.current) return
    sound.muted = true
    sound.play().then(() => {
      sound.pause()
      sound.currentTime = 0
      sound.muted = false
      soundUnlockedRef.current = true
    }).catch(() => {
      sound.muted = false
    })
  }, [])

  const reset = () => setResult(null)

  const acceptResult = (nextResult: TranscriptionResult) => {
    setResult(nextResult)
    playFeedback()
  }

  const openSource = (source: SourceType) => {
    unlockFeedback()
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
        <button
          type="button"
          className="brand-home"
          style={visualStyle(visualConfig.navLogo)}
          onClick={openMenu}
          aria-label="Guitarica home"
        >
          <img src="/images/logo.svg" alt="Guitarica" />
        </button>
        {view === 'studio' && !result && (
          <SourceTabs activeSource={activeSource} onChange={setActiveSource} />
        )}
        <span className="header-note">Guitar transcription</span>
      </header>

      {!result && view === 'menu' && (
        <SourceMenu
          onSelect={openSource}
          onGuitarClick={playFeedback}
          visualConfig={visualConfig}
        />
      )}

      {!result && view === 'studio' && (
        <div className={`workspace workspace-${activeSource}`}>
          <span className="workspace-index" style={visualStyle(visualConfig.studioIndex)} aria-hidden="true">
            {activeSource === 'upload' ? '01' : activeSource === 'youtube' ? '02' : '03'}
          </span>
          <button
            type="button"
            className="workspace-guitar"
            style={visualStyle(visualConfig.studioGuitar)}
            onClick={playFeedback}
            aria-label="Play Guitarica sound"
          >
            <img src="/images/Guitarica.png" alt="" />
          </button>
          <div className="workspace-content" style={visualStyle(visualConfig.studioContent)}>
            {activeSource === 'upload' && (
              <UploadPanel
                featureType={featureType}
                onFeatureTypeChange={setFeatureType}
                onComplete={acceptResult}
              />
            )}

            {activeSource === 'youtube' && (
              <YouTubePanel
                featureType={featureType}
                onFeatureTypeChange={setFeatureType}
                onComplete={acceptResult}
              />
            )}

            {activeSource === 'live' && <LiveInputPanel />}
          </div>
        </div>
      )}

      {result && <TranscriptionReport result={result} onReset={reset} />}

      {showCalibrator && (
        <VisualCalibrator
          config={visualConfig}
          onChange={setVisualConfig}
          onClose={() => setShowCalibrator(false)}
          onOpenMenu={openMenu}
          onOpenSource={openSource}
        />
      )}
    </main>
  )
}
