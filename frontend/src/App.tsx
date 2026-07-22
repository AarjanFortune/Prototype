import { useState, useEffect } from 'react'
import StudioCalibrator, { AllElementsConfig, PRESET_CURVES } from './components/studio/StudioCalibrator'
import Phase2Workspace from './components/studio/Phase2Workspace'

type TabType = 'upload' | 'youtube' | 'live'

interface ElementConfig {
  x: number;      
  y: number;      
  scale: number;  
  rotate: number; 
  width: number;  
}

const DEFAULT_CONFIG: AllElementsConfig = {
  logo: { duration: 0.95, bezier: PRESET_CURVES['Figma Gentle'].bezier, presetName: 'Figma Gentle', entryType: 'slide-down', delay: 0 },
  guitar: { duration: 1.1, bezier: PRESET_CURVES['Slow-In Spring'].bezier, presetName: 'Slow-In Spring', entryType: 'scale-up', delay: 0.05 },
  leftBand: { duration: 0.85, bezier: PRESET_CURVES['Snappy Ease-Out'].bezier, presetName: 'Snappy Ease-Out', entryType: 'slide-right', delay: 0 },
  rightBand: { duration: 0.85, bezier: PRESET_CURVES['Snappy Ease-Out'].bezier, presetName: 'Snappy Ease-Out', entryType: 'slide-left', delay: 0 },
  navTabs: { duration: 0.75, bezier: PRESET_CURVES['Soft Overshoot'].bezier, presetName: 'Soft Overshoot', entryType: 'slide-up', delay: 0.15 },
  formCard: { duration: 0.9, bezier: PRESET_CURVES['Figma Gentle'].bezier, presetName: 'Figma Gentle', entryType: 'blur-in', delay: 0.25 },
  closeBtn: { duration: 0.6, bezier: PRESET_CURVES['Linear Motion'].bezier, presetName: 'Linear Motion', entryType: 'fade', delay: 0.3 }
}

export default function App() {
  const [inStudioMode, setInStudioMode] = useState(false)
  const [activeTab, setActiveTab] = useState<TabType>('upload')
  const [editorEnabled, setEditorEnabled] = useState(false)

  // Master per-element animation state
  const [animConfig, setAnimConfig] = useState<AllElementsConfig>(DEFAULT_CONFIG)

  // Calibrated Positions (Adjusted Phase 2 Logo to x: 6%, y: 8% to prevent overlap)
  const [p1Guitar] = useState<ElementConfig>({ x: 51, y: 51, scale: 1.35, rotate: 0, width: 70 })
  const [p1Logo] = useState<ElementConfig>({ x: 81, y: 32, scale: 1, rotate: 0, width: 180 })
  const [p1LeftBand] = useState<ElementConfig>({ x: 0, y: 38, scale: 1, rotate: 0, width: 31 })
  const [p1RightBand] = useState<ElementConfig>({ x: 0, y: 38, scale: 1, rotate: 0, width: 29 })

  const [p2Guitar] = useState<ElementConfig>({ x: 85, y: 52, scale: 0.95, rotate: -91, width: 51 })
  const [p2Logo] = useState<ElementConfig>({ x: 6, y: 8, scale: 0.8, rotate: 0, width: 140 }) 

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === 'd') {
        setEditorEnabled(prev => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const guitar = inStudioMode ? p2Guitar : p1Guitar
  const logo = inStudioMode ? p2Logo : p1Logo

  const getTransitionFor = (key: keyof AllElementsConfig) => {
    const { duration, bezier, delay } = animConfig[key]
    return `all ${duration}s cubic-bezier(${bezier.join(', ')}) ${delay}s`
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
    cursor: !inStudioMode && !editorEnabled ? 'pointer' : 'default'
  }

  const getLeftBandStyle = (): React.CSSProperties => ({
    position: 'absolute',
    top: `${p1LeftBand.y}%`,
    left: inStudioMode ? `-${p1LeftBand.width}%` : `${p1LeftBand.x}%`,
    width: `${p1LeftBand.width}%`,
    height: '170px',
    backgroundColor: '#ebeeef',
    borderTopRightRadius: '80px',
    borderBottomRightRadius: '80px',
    opacity: inStudioMode ? 0 : 0.85,
    zIndex: 1,
    pointerEvents: 'none',
    transition: getTransitionFor('leftBand')
  })

  const getRightBandStyle = (): React.CSSProperties => ({
    position: 'absolute',
    top: `${p1RightBand.y}%`,
    right: inStudioMode ? `-${p1RightBand.width}%` : `${p1RightBand.x}%`,
    width: `${p1RightBand.width}%`,
    height: '170px',
    backgroundColor: '#ebeeef',
    borderTopLeftRadius: '80px',
    borderBottomLeftRadius: '80px',
    opacity: inStudioMode ? 0 : 0.85,
    zIndex: 1,
    pointerEvents: 'none',
    transition: getTransitionFor('rightBand')
  })

  const getGuitarStyle = (): React.CSSProperties => ({
    position: 'absolute',
    top: `${guitar.y}%`,
    left: `${guitar.x}%`,
    transform: `translate(-50%, -50%) scale(${guitar.scale}) rotate(${guitar.rotate}deg)`,
    width: `${guitar.width}%`,
    maxHeight: inStudioMode ? '520px' : '400px',
    objectFit: 'contain',
    zIndex: 2,
    transformOrigin: 'center center',
    transition: getTransitionFor('guitar')
  })

  const getLogoStyle = (): React.CSSProperties => ({
    position: 'absolute',
    top: `${logo.y}%`,
    left: `${logo.x}%`,
    transform: `translate(-50%, -50%) scale(${logo.scale})`,
    width: `${logo.width}px`,
    height: 'auto',
    zIndex: 3,
    transition: getTransitionFor('logo')
  })

  return (
    <div className="app-viewport" style={{ position: 'relative' }}>
      
      <div 
        style={containerStyle} 
        onClick={() => !inStudioMode && !editorEnabled && setInStudioMode(true)}
      >
        {/* Accent Bands */}
        <div style={getLeftBandStyle()} />
        <div style={getRightBandStyle()} />

        {/* Clean SVG Logo Asset */}
        <img 
          src="/images/logo.svg" 
          alt="Guitarica Logo" 
          style={getLogoStyle()} 
        />

        {/* Guitar Showcase Asset */}
        <img src="/images/Guitarica.png" alt="Guitar" style={getGuitarStyle()} />

        {/* PHASE 1: Hero Setup Overlays */}
        {!inStudioMode && (
          <div style={{ position: 'relative', zIndex: 10, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%', width: '100%', pointerEvents: 'none' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, letterSpacing: '0.25em', textTransform: 'uppercase' }}>Studio Setup</span>
              <span style={{ fontSize: '0.7rem', letterSpacing: '0.15em', color: 'var(--color-muted)', textTransform: 'uppercase' }}>Reference 44</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', fontSize: '0.7rem', color: 'var(--color-muted)', letterSpacing: '0.05em' }}>
              <span>Single Viewport Frame</span>
              
              <div style={{ textAlign: 'center', opacity: 0.6, letterSpacing: '0.25em', textTransform: 'uppercase', fontSize: '0.65rem', color: 'var(--color-ink)', fontWeight: 600 }}>
                [ Click anywhere to open studio ]
              </div>

              <span>All rights reserved</span>
            </div>
          </div>
        )}

        {/* PHASE 2: Dynamic Animated Studio Workspace */}
        {inStudioMode && (
          <Phase2Workspace 
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            onClose={() => setInStudioMode(false)}
            config={animConfig}
          />
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

      {/* Draggable Glassmorphic Calibrator Drawer */}
      {editorEnabled && (
        <StudioCalibrator 
          config={animConfig}
          setConfig={setAnimConfig}
          inStudioMode={inStudioMode}
          setInStudioMode={setInStudioMode}
          onClose={() => setEditorEnabled(false)}
        />
      )}
    </div>
  )
}