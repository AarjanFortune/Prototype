import { useState, useEffect, useRef } from 'react'
import Preloader from './components/studio/Preloader'
import StudioCalibrator, { AllElementsConfig, SingleElementAnim } from './components/studio/StudioCalibrator'
import StudioWorkspace from './components/studio/StudioWorkspace'
import ColumnCurtain from './components/studio/ColumnCurtain'

type TabType = 'upload' | 'youtube' | 'live'

const TR_SEQ = [115, 116, 117, 100, 105, 111, 109, 111, 100, 101]

const DEFAULT_CONFIG: AllElementsConfig = {
  "phase1": {
    "logo": { "duration": 0.95, "bezier": [0.25, 1, 0.3, 1], "presetName": "Figma Gentle", "entryType": "slide-down", "delay": 0, "x": 57, "y": 15, "scale": 1.65, "rotate": 0 },
    "guitar": { "duration": 0.95, "bezier": [0.25, 1, 0.3, 1], "presetName": "Figma Gentle", "entryType": "scale-up", "delay": 0.1, "x": 51, "y": 51, "scale": 0.55, "rotate": 0 },
    "leftBand": { "duration": 0.85, "bezier": [0.4, 0, 0.2, 1], "presetName": "Snappy Ease-Out", "entryType": "slide-right", "delay": 0, "x": 0, "y": 38, "scale": 1, "rotate": 0 },
    "rightBand": { "duration": 0.85, "bezier": [0.4, 0, 0.2, 1], "presetName": "Snappy Ease-Out", "entryType": "slide-left", "delay": 0, "x": 0, "y": 38, "scale": 1, "rotate": 0 },
    "navTabs": { "duration": 0.75, "bezier": [0.34, 1.56, 0.64, 1], "presetName": "Soft Overshoot", "entryType": "slide-up", "delay": 0, "x": 0, "y": 0, "scale": 1, "rotate": 0 },
    "formCard": { "duration": 0.9, "bezier": [0.25, 1, 0.3, 1], "presetName": "Figma Gentle", "entryType": "blur-in", "delay": 0, "x": 0, "y": 0, "scale": 1, "rotate": 0 },
    "closeBtn": { "duration": 0.6, "bezier": [0, 0, 1, 1], "presetName": "Linear Motion", "entryType": "fade", "delay": 0, "x": 0, "y": 0, "scale": 1, "rotate": 0 }
  },
  "phase2": {
    "logo": { "duration": 0.95, "bezier": [0.25, 1, 0.3, 1], "presetName": "Figma Gentle", "entryType": "slide-down", "delay": 0, "x": 8, "y": 8, "scale": 0.85, "rotate": 0 },
    "guitar": { "duration": 1.1, "bezier": [0.175, 0.885, 0.32, 1.275], "presetName": "Slow-In Spring", "entryType": "scale-up", "delay": 0.05, "x": 85, "y": 52, "scale": 0.35, "rotate": -91 },
    "leftBand": { "duration": 0.85, "bezier": [0.4, 0, 0.2, 1], "presetName": "Snappy Ease-Out", "entryType": "slide-right", "delay": 0, "x": -35, "y": 38, "scale": 1, "rotate": 0 },
    "rightBand": { "duration": 0.85, "bezier": [0.4, 0, 0.2, 1], "presetName": "Snappy Ease-Out", "entryType": "slide-left", "delay": 0, "x": -35, "y": 38, "scale": 1, "rotate": 0 },
    "navTabs": { "duration": 0.75, "bezier": [0.34, 1.56, 0.64, 1], "presetName": "Soft Overshoot", "entryType": "slide-up", "delay": 0.15, "x": 0, "y": 0, "scale": 1, "rotate": 0 },
    "formCard": { "duration": 0.9, "bezier": [0.25, 1, 0.3, 1], "presetName": "Figma Gentle", "entryType": "blur-in", "delay": 0.25, "x": 0, "y": 0, "scale": 1, "rotate": 0 },
    "closeBtn": { "duration": 0.6, "bezier": [0, 0, 1, 1], "presetName": "Linear Motion", "entryType": "fade", "delay": 0.3, "x": 0, "y": 0, "scale": 1, "rotate": 0 }
  }
}

export default function App() {
  const [phase, setPhase] = useState<number>(0) 
  const [curtainActive, setCurtainActive] = useState(false)
  const [showCurtain, setShowCurtain] = useState(false)
  
  const [activeTab, setActiveTab] = useState<TabType>('upload')
  const [sysDiagnostics, setSysDiagnostics] = useState(false)
  const [animConfig, setAnimConfig] = useState<AllElementsConfig>(DEFAULT_CONFIG)

  const keyBuffer = useRef<number[]>([])
  const soundRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    soundRef.current = new Audio('/images/GEF.mp3')
    soundRef.current.preload = 'auto'
  }, [])

  // Secret Obfuscated Keyboard Sequence Detection
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      const activeTag = document.activeElement?.tagName.toLowerCase()
      const isInputFocused = activeTag === 'input' || activeTag === 'textarea' || (document.activeElement as HTMLElement)?.isContentEditable

      if (isInputFocused) return

      const charCode = e.key.toLowerCase().charCodeAt(0)
      keyBuffer.current.push(charCode)

      if (keyBuffer.current.length > TR_SEQ.length) {
        keyBuffer.current.shift()
      }

      if (
        keyBuffer.current.length === TR_SEQ.length &&
        keyBuffer.current.every((code, idx) => code === TR_SEQ[idx])
      ) {
        setSysDiagnostics(prev => !prev)
        keyBuffer.current = []
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [])

  const playSoundAndTransitionToPhase2 = () => {
    if (soundRef.current) {
      soundRef.current.currentTime = 0
      soundRef.current.play().catch(() => {})
    }
    setPhase(2)
  }

  const triggerPhase1Transition = () => {
    setShowCurtain(true)
    setPhase(1)
    requestAnimationFrame(() => {
      setCurtainActive(true)
    })
  }

  const currentPhaseKey = phase === 2 ? 'phase2' : 'phase1'
  const activePhaseConfig = animConfig[currentPhaseKey]

  const getElementStyle = (item: SingleElementAnim, isLeftBand = false, isRightBand = false): React.CSSProperties => {
    const cubic = `cubic-bezier(${item.bezier.join(', ')})`
    const transition = `all ${item.duration}s ${cubic} ${item.delay}s`

    if (isLeftBand) {
      return {
        position: 'absolute',
        top: `${item.y}%`,
        left: phase === 2 ? `-${31}%` : `${item.x}%`,
        width: `31%`,
        height: '170px',
        backgroundColor: '#ebeeef',
        borderTopRightRadius: '80px',
        borderBottomRightRadius: '80px',
        opacity: phase === 2 ? 0 : 0.85,
        zIndex: 1,
        pointerEvents: 'none',
        transition
      }
    }

    if (isRightBand) {
      return {
        position: 'absolute',
        top: `${item.y}%`,
        right: phase === 2 ? `-${29}%` : `${item.x}%`,
        width: `29%`,
        height: '170px',
        backgroundColor: '#ebeeef',
        borderTopLeftRadius: '80px',
        borderBottomLeftRadius: '80px',
        opacity: phase === 2 ? 0 : 0.85,
        zIndex: 1,
        pointerEvents: 'none',
        transition
      }
    }

    return {
      position: 'absolute',
      top: `${item.y}%`,
      left: `${item.x}%`,
      transform: `translate(-50%, -50%) scale(${item.scale}) rotate(${item.rotate}deg)`,
      transition
    }
  }

  const containerStyle: React.CSSProperties = {
    background: 'var(--bg-panel)',
    width: '100%',
    maxWidth: '1340px',
    height: '84vh',
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
    border: '1px solid var(--color-border)',
    overflow: 'hidden',
    padding: '48px 64px',
    cursor: phase === 1 && !sysDiagnostics ? 'pointer' : 'default'
  }

  return (
    <div className="app-viewport" style={{ position: 'relative' }}>
      <div 
        style={containerStyle} 
        onClick={() => phase === 1 && !sysDiagnostics && playSoundAndTransitionToPhase2()}
      >
        {phase === 0 && (
          <Preloader onComplete={triggerPhase1Transition} />
        )}

        {showCurtain && (
          <ColumnCurtain 
            isActive={curtainActive} 
            onAnimationEnd={() => {
              setShowCurtain(false)
              setCurtainActive(false)
            }} 
          />
        )}

        {phase > 0 && (
          <>
            <div style={getElementStyle(activePhaseConfig.leftBand, true, false)} />
            <div style={getElementStyle(activePhaseConfig.rightBand, false, true)} />

            <img 
              src="/images/logo.svg" 
              alt="Guitarica Logo" 
              style={{ ...getElementStyle(activePhaseConfig.logo), width: '160px', zIndex: 3 }} 
            />

            <img 
              src="/images/Guitarica.png" 
              alt="Guitar" 
              style={{ ...getElementStyle(activePhaseConfig.guitar), zIndex: 2, objectFit: 'contain' }} 
            />

            {phase === 1 && (
              <div style={{ position: 'relative', zIndex: 10, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', height: '100%', width: '100%', pointerEvents: 'none' }}>
                <div style={{ textAlign: 'center', opacity: 0.6, letterSpacing: '0.25em', textTransform: 'uppercase', fontSize: '0.65rem', color: 'var(--color-ink)', fontWeight: 600 }}>
                  [ Click anywhere to open studio ]
                </div>
              </div>
            )}

            {phase === 2 && (
              <StudioWorkspace 
                activeTab={activeTab}
                setActiveTab={setActiveTab}
                onClose={() => setPhase(1)}
                navAnim={activePhaseConfig.navTabs}
                formAnim={activePhaseConfig.formCard}
                closeBtnAnim={activePhaseConfig.closeBtn}
              />
            )}
          </>
        )}
      </div>

      {/* Secret Obfuscated Calibrator Injection */}
      {sysDiagnostics && (
        <StudioCalibrator 
          config={animConfig}
          setConfig={setAnimConfig}
          phase={phase}
          setPhase={setPhase}
          onClose={() => setSysDiagnostics(false)}
        />
      )}
    </div>
  )
}