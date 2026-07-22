import { useState, useEffect } from 'react'
import Preloader from './components/studio/Preloader'
import StudioCalibrator, { AllElementsConfig, PRESET_CURVES, SingleElementAnim } from './components/studio/StudioCalibrator'
import StudioWorkspace from './components/studio/StudioWorkspace'

type TabType = 'upload' | 'youtube' | 'live'

const DEFAULT_CONFIG: AllElementsConfig = {
  phase1: {
    logo: { duration: 0.95, bezier: PRESET_CURVES['Figma Gentle'].bezier, presetName: 'Figma Gentle', entryType: 'slide-down', delay: 0, x: 81, y: 32, scale: 1.0, rotate: 0 },
    guitar: { duration: 1.1, bezier: PRESET_CURVES['Slow-In Spring'].bezier, presetName: 'Slow-In Spring', entryType: 'scale-up', delay: 0.05, x: 51, y: 51, scale: 1.35, rotate: 0 },
    leftBand: { duration: 0.85, bezier: PRESET_CURVES['Snappy Ease-Out'].bezier, presetName: 'Snappy Ease-Out', entryType: 'slide-right', delay: 0, x: 0, y: 38, scale: 1.0, rotate: 0 },
    rightBand: { duration: 0.85, bezier: PRESET_CURVES['Snappy Ease-Out'].bezier, presetName: 'Snappy Ease-Out', entryType: 'slide-left', delay: 0, x: 0, y: 38, scale: 1.0, rotate: 0 },
    navTabs: { duration: 0.75, bezier: PRESET_CURVES['Soft Overshoot'].bezier, presetName: 'Soft Overshoot', entryType: 'slide-up', delay: 0, x: 0, y: 0, scale: 1, rotate: 0 },
    formCard: { duration: 0.9, bezier: PRESET_CURVES['Figma Gentle'].bezier, presetName: 'Figma Gentle', entryType: 'blur-in', delay: 0, x: 0, y: 0, scale: 1, rotate: 0 },
    closeBtn: { duration: 0.6, bezier: PRESET_CURVES['Linear Motion'].bezier, presetName: 'Linear Motion', entryType: 'fade', delay: 0, x: 0, y: 0, scale: 1, rotate: 0 }
  },
  phase2: {
    logo: { duration: 0.95, bezier: PRESET_CURVES['Figma Gentle'].bezier, presetName: 'Figma Gentle', entryType: 'slide-down', delay: 0, x: 8, y: 8, scale: 0.85, rotate: 0 },
    guitar: { duration: 1.1, bezier: PRESET_CURVES['Slow-In Spring'].bezier, presetName: 'Slow-In Spring', entryType: 'scale-up', delay: 0.05, x: 85, y: 52, scale: 0.95, rotate: -91 },
    leftBand: { duration: 0.85, bezier: PRESET_CURVES['Snappy Ease-Out'].bezier, presetName: 'Snappy Ease-Out', entryType: 'slide-right', delay: 0, x: -35, y: 38, scale: 1.0, rotate: 0 },
    rightBand: { duration: 0.85, bezier: PRESET_CURVES['Snappy Ease-Out'].bezier, presetName: 'Snappy Ease-Out', entryType: 'slide-left', delay: 0, x: -35, y: 38, scale: 1.0, rotate: 0 },
    navTabs: { duration: 0.75, bezier: PRESET_CURVES['Soft Overshoot'].bezier, presetName: 'Soft Overshoot', entryType: 'slide-up', delay: 0.15, x: 0, y: 0, scale: 1, rotate: 0 },
    formCard: { duration: 0.9, bezier: PRESET_CURVES['Figma Gentle'].bezier, presetName: 'Figma Gentle', entryType: 'blur-in', delay: 0.25, x: 0, y: 0, scale: 1, rotate: 0 },
    closeBtn: { duration: 0.6, bezier: PRESET_CURVES['Linear Motion'].bezier, presetName: 'Linear Motion', entryType: 'fade', delay: 0.3, x: 0, y: 0, scale: 1, rotate: 0 }
  }
}

export default function App() {
  const [phase, setPhase] = useState<number>(0) // 0: Preloader, 1: Hero Setup, 2: Studio
  const [activeTab, setActiveTab] = useState<TabType>('upload')
  const [editorEnabled, setEditorEnabled] = useState(false)
  const [animConfig, setAnimConfig] = useState<AllElementsConfig>(DEFAULT_CONFIG)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === 'd') {
        setEditorEnabled(prev => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

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
    cursor: phase === 1 && !editorEnabled ? 'pointer' : 'default'
  }

  return (
    <div className="app-viewport" style={{ position: 'relative' }}>
      <div 
        style={containerStyle} 
        onClick={() => phase === 1 && !editorEnabled && setPhase(2)}
      >
        {/* PHASE 0: Preloader Drawing Sequence */}
        {phase === 0 && (
          <Preloader onComplete={() => setPhase(1)} />
        )}

        {/* PHASE 1 & 2: Main Layout */}
        {phase > 0 && (
          <>
            <div style={getElementStyle(activePhaseConfig.leftBand, true, false)} />
            <div style={getElementStyle(activePhaseConfig.rightBand, false, true)} />

            {/* Logo */}
            <img 
              src="/images/logo.svg" 
              alt="Guitarica Logo" 
              style={{ ...getElementStyle(activePhaseConfig.logo), width: '160px', zIndex: 3 }} 
            />

            {/* Guitar Showcase */}
            <img 
              src="/images/Guitarica.png" 
              alt="Guitar" 
              style={{ ...getElementStyle(activePhaseConfig.guitar), zIndex: 2, objectFit: 'contain' }} 
            />

            {/* Phase 1 Clean Overlay */}
            {phase === 1 && (
              <div style={{ position: 'relative', zIndex: 10, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', height: '100%', width: '100%', pointerEvents: 'none' }}>
                <div style={{ textAlign: 'center', opacity: 0.6, letterSpacing: '0.25em', textTransform: 'uppercase', fontSize: '0.65rem', color: 'var(--color-ink)', fontWeight: 600 }}>
                  [ Click anywhere to open studio ]
                </div>
              </div>
            )}

            {/* Phase 2 Studio Workspace */}
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

      {/* Control Calibrator Toggle */}
      <button 
        style={{
          position: 'fixed', bottom: '20px', left: '20px',
          zIndex: 10000, background: 'rgba(29, 29, 31, 0.85)',
          backdropFilter: 'blur(10px)', color: '#fff',
          border: '1px solid rgba(255,255,255,0.2)', borderRadius: '50px', padding: '10px 22px', 
          cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600, boxShadow: '0 8px 24px rgba(0,0,0,0.15)'
        }}
        onClick={() => setEditorEnabled(!editorEnabled)}
      >
        {editorEnabled ? 'Close Calibrator' : 'Open Controls [D]'}
      </button>

      {/* Glassmorphic Calibrator */}
      {editorEnabled && (
        <StudioCalibrator 
          config={animConfig}
          setConfig={setAnimConfig}
          phase={phase}
          setPhase={setPhase}
          onClose={() => setEditorEnabled(false)}
        />
      )}
    </div>
  )
}