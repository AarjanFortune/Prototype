import React, { useState, useRef, useEffect } from 'react'

export interface SingleElementAnim {
  duration: number
  bezier: [number, number, number, number]
  presetName: string
  entryType: 'fade' | 'slide-up' | 'slide-down' | 'slide-left' | 'slide-right' | 'scale-up' | 'blur-in' | 'bounce'
  delay: number
  x: number
  y: number
  scale: number
  rotate: number
}

export type ElementKey = 'logo' | 'guitar' | 'leftBand' | 'rightBand' | 'navTabs' | 'formCard' | 'closeBtn'
export type PhaseKey = 'phase1' | 'phase2'
export type AllElementsConfig = Record<PhaseKey, Record<ElementKey, SingleElementAnim>>

export const PRESET_CURVES: Record<string, { bezier: [number, number, number, number]; duration: number }> = {
  'Figma Gentle': { bezier: [0.25, 1, 0.3, 1], duration: 0.95 },
  'Snappy Ease-Out': { bezier: [0.4, 0, 0.2, 1], duration: 0.65 },
  'Elastic Spring': { bezier: [0.68, -0.55, 0.265, 1.55], duration: 1.1 },
  'Anticipate Back': { bezier: [0.6, -0.28, 0.735, 0.045], duration: 0.85 },
  'Slow-In Spring': { bezier: [0.175, 0.885, 0.32, 1.275], duration: 1.1 },
  'Linear Motion': { bezier: [0, 0, 1, 1], duration: 1.0 },
  'Soft Overshoot': { bezier: [0.34, 1.56, 0.64, 1], duration: 0.8 },
  'Heavy Ease': { bezier: [0.77, 0, 0.175, 1], duration: 1.2 },
  'Quintic Smooth': { bezier: [0.83, 0, 0.17, 1], duration: 1.0 },
  'Bounce Impact': { bezier: [0.36, 0, 0.66, -0.56], duration: 0.75 },
  'Smooth Step': { bezier: [0.45, 0.05, 0.55, 0.95], duration: 0.9 },
  'Swift In-Out': { bezier: [0.11, 0, 0.5, 0.0], duration: 0.5 }
}

interface CalibratorProps {
  config: AllElementsConfig
  setConfig: React.Dispatch<React.SetStateAction<AllElementsConfig>>
  phase: number
  setPhase: (p: number) => void
  onClose: () => void
}

const ELEMENT_LABELS: Record<ElementKey, string> = {
  logo: 'Logo Asset',
  guitar: 'Guitar Body',
  leftBand: 'Left Accent Band',
  rightBand: 'Right Accent Band',
  navTabs: 'Navigation Tabs',
  formCard: 'Studio Input Form',
  closeBtn: 'Close Command Button'
}

export default function StudioCalibrator({
  config,
  setConfig,
  phase,
  setPhase,
  onClose
}: CalibratorProps) {
  const [selectedElem, setSelectedElem] = useState<ElementKey>('logo')
  const [copied, setCopied] = useState(false)
  
  const [position, setPosition] = useState({ x: 30, y: 30 })
  const isDragging = useRef(false)
  const dragStart = useRef({ x: 0, y: 0 })

  const currentPhaseKey: PhaseKey = phase === 2 ? 'phase2' : 'phase1'

  const handleMouseDown = (e: React.MouseEvent) => {
    isDragging.current = true
    dragStart.current = { x: e.clientX - position.x, y: e.clientY - position.y }
  }

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return
      setPosition({
        x: e.clientX - dragStart.current.x,
        y: e.clientY - dragStart.current.y
      })
    }
    const handleMouseUp = () => { isDragging.current = false }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [position])

  const currentAnim = config[currentPhaseKey][selectedElem]

  const updateSelected = (fields: Partial<SingleElementAnim>) => {
    setConfig(prev => ({
      ...prev,
      [currentPhaseKey]: {
        ...prev[currentPhaseKey],
        [selectedElem]: {
          ...prev[currentPhaseKey][selectedElem],
          ...fields
        }
      }
    }))
  }

  const applyPresetToSelected = (name: string) => {
    const preset = PRESET_CURVES[name]
    if (preset) {
      updateSelected({
        presetName: name,
        bezier: preset.bezier,
        duration: preset.duration
      })
    }
  }

  const copyParametersToClipboard = () => {
    const codeString = `const DEFAULT_CONFIG: AllElementsConfig = ${JSON.stringify(config, null, 2)}`
    navigator.clipboard.writeText(codeString)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div style={{
      position: 'fixed',
      top: `${position.y}px`,
      left: `${position.x}px`,
      width: '380px',
      background: 'rgba(255, 255, 255, 0.82)',
      backdropFilter: 'blur(20px) saturate(180%)',
      WebkitBackdropFilter: 'blur(20px) saturate(180%)',
      color: '#1d1d1f',
      borderRadius: '16px',
      padding: '20px',
      zIndex: 9999,
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      fontSize: '0.75rem',
      maxHeight: '85vh',
      overflowY: 'auto',
      border: '1px solid rgba(255, 255, 255, 0.8)',
      boxShadow: '0 20px 50px rgba(0, 0, 0, 0.12)'
    }}>
      <div 
        onMouseDown={handleMouseDown}
        style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginBottom: '14px', borderBottom: '1px solid rgba(0, 0, 0, 0.08)',
          paddingBottom: '10px', cursor: 'grab', userSelect: 'none'
        }}
      >
        <span style={{ fontWeight: 700, fontSize: '0.8rem' }}>Studio Motion Calibrator</span>
        <button 
          onClick={onClose} 
          style={{ background: 'rgba(0,0,0,0.06)', border: 'none', color: '#1d1d1f', borderRadius: '50%', width: '22px', height: '22px', cursor: 'pointer', fontWeight: 600 }}
        >
          ✕
        </button>
      </div>

      <button
        onClick={copyParametersToClipboard}
        style={{
          width: '100%', padding: '10px', marginBottom: '14px',
          background: copied ? '#34c759' : '#0066cc', color: '#fff',
          border: 'none', borderRadius: '8px', fontWeight: 600,
          cursor: 'pointer', transition: 'all 0.2s'
        }}
      >
        {copied ? 'Copied Config Code Parameters!' : 'Copy Config Code Parameters'}
      </button>

      <div style={{ marginBottom: '16px', display: 'flex', gap: '6px' }}>
        <button 
          onClick={() => setPhase(0)} 
          style={{ flex: 1, padding: '8px', background: phase === 0 ? '#1d1d1f' : 'rgba(0,0,0,0.05)', color: phase === 0 ? '#fff' : '#1d1d1f', border: 'none', fontWeight: 600, cursor: 'pointer', borderRadius: '8px' }}
        >
          Phase 0
        </button>
        <button 
          onClick={() => setPhase(1)} 
          style={{ flex: 1, padding: '8px', background: phase === 1 ? '#1d1d1f' : 'rgba(0,0,0,0.05)', color: phase === 1 ? '#fff' : '#1d1d1f', border: 'none', fontWeight: 600, cursor: 'pointer', borderRadius: '8px' }}
        >
          Phase 1
        </button>
        <button 
          onClick={() => setPhase(2)} 
          style={{ flex: 1, padding: '8px', background: phase === 2 ? '#1d1d1f' : 'rgba(0,0,0,0.05)', color: phase === 2 ? '#fff' : '#1d1d1f', border: 'none', fontWeight: 600, cursor: 'pointer', borderRadius: '8px' }}
        >
          Phase 2
        </button>
      </div>

      <div style={{ marginBottom: '14px' }}>
        <label style={{ display: 'block', fontWeight: 600, marginBottom: '6px', color: '#6e6e73' }}>
          Select Component [{currentPhaseKey.toUpperCase()}]:
        </label>
        <select 
          value={selectedElem}
          onChange={e => setSelectedElem(e.target.value as ElementKey)}
          style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid rgba(0,0,0,0.12)', background: 'rgba(255,255,255,0.9)', color: '#1d1d1f', fontWeight: 600, outline: 'none' }}
        >
          {Object.entries(ELEMENT_LABELS).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
      </div>

      <div style={{ marginBottom: '14px', background: 'rgba(0, 0, 0, 0.03)', padding: '12px', borderRadius: '10px' }}>
        <div style={{ fontWeight: 600, marginBottom: '8px' }}>Real-Time Position & Scale</div>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>X Pos:</span><b>{currentAnim.x}%</b></div>
            <input type="range" min={-50} max={150} value={currentAnim.x} onChange={e => updateSelected({ x: parseFloat(e.target.value) })} style={{ width: '100%', accentColor: '#1d1d1f' }} />
          </div>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Y Pos:</span><b>{currentAnim.y}%</b></div>
            <input type="range" min={-50} max={150} value={currentAnim.y} onChange={e => updateSelected({ y: parseFloat(e.target.value) })} style={{ width: '100%', accentColor: '#1d1d1f' }} />
          </div>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Scale:</span><b>{currentAnim.scale}</b></div>
            <input type="range" min={0.1} max={3.0} step={0.05} value={currentAnim.scale} onChange={e => updateSelected({ scale: parseFloat(e.target.value) })} style={{ width: '100%', accentColor: '#1d1d1f' }} />
          </div>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Rotate:</span><b>{currentAnim.rotate}°</b></div>
            <input type="range" min={-180} max={180} value={currentAnim.rotate} onChange={e => updateSelected({ rotate: parseFloat(e.target.value) })} style={{ width: '100%', accentColor: '#1d1d1f' }} />
          </div>
        </div>
      </div>

      <div style={{ marginBottom: '14px', background: 'rgba(0, 0, 0, 0.03)', padding: '12px', borderRadius: '10px' }}>
        <div style={{ fontWeight: 600, marginBottom: '8px' }}>Motion Preset (12)</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px' }}>
          {Object.keys(PRESET_CURVES).map(name => (
            <button
              key={name}
              onClick={() => applyPresetToSelected(name)}
              style={{
                fontSize: '0.65rem', padding: '6px 4px', cursor: 'pointer',
                background: currentAnim.presetName === name ? '#1d1d1f' : 'rgba(255,255,255,0.7)',
                color: currentAnim.presetName === name ? '#fff' : '#1d1d1f',
                border: 'none', borderRadius: '6px', fontWeight: currentAnim.presetName === name ? 600 : 400
              }}
            >
              {name}
            </button>
          ))}
        </div>
      </div>

      <div style={{ background: 'rgba(0, 0, 0, 0.03)', padding: '12px', borderRadius: '10px' }}>
        <label style={{ display: 'block', fontWeight: 600, marginBottom: '6px' }}>Entrance Effect:</label>
        <select
          value={currentAnim.entryType}
          onChange={e => updateSelected({ entryType: e.target.value as any })}
          style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid rgba(0,0,0,0.12)', background: 'rgba(255,255,255,0.9)', color: '#1d1d1f', outline: 'none' }}
        >
          <option value="fade">Fade In</option>
          <option value="slide-up">Slide Up</option>
          <option value="slide-down">Slide Down</option>
          <option value="slide-left">Slide Left</option>
          <option value="slide-right">Slide Right</option>
          <option value="scale-up">Scale Zoom</option>
          <option value="blur-in">Blur In Reveal</option>
          <option value="bounce">Spring Bounce</option>
        </select>

        <div style={{ marginTop: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>Delay Offset:</span><b>{currentAnim.delay}s</b>
          </div>
          <input
            type="range" min={0} max={1.5} step={0.05}
            value={currentAnim.delay}
            onChange={e => updateSelected({ delay: parseFloat(e.target.value) })}
            style={{ width: '100%', accentColor: '#1d1d1f' }}
          />
        </div>
      </div>
    </div>
  )
}