import React, { useState, useRef, useEffect } from 'react'

export interface SingleElementAnim {
  duration: number
  bezier: [number, number, number, number]
  presetName: string
  entryType: 'fade' | 'slide-up' | 'slide-down' | 'slide-left' | 'slide-right' | 'scale-up' | 'blur-in' | 'bounce'
  delay: number
}

export type ElementKey = 'logo' | 'guitar' | 'leftBand' | 'rightBand' | 'navTabs' | 'formCard' | 'closeBtn'

export type AllElementsConfig = Record<ElementKey, SingleElementAnim>

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
  inStudioMode: boolean
  setInStudioMode: (v: boolean) => void
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
  inStudioMode,
  setInStudioMode,
  onClose
}: CalibratorProps) {
  const [selectedElem, setSelectedElem] = useState<ElementKey>('logo')
  
  // Dragging state
  const [position, setPosition] = useState({ x: 30, y: 30 })
  const isDragging = useRef(false)
  const dragStart = useRef({ x: 0, y: 0 })

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

    const handleMouseUp = () => {
      isDragging.current = false
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [position])

  const currentAnim = config[selectedElem]

  const updateSelectedAnim = (fields: Partial<SingleElementAnim>) => {
    setConfig(prev => ({
      ...prev,
      [selectedElem]: {
        ...prev[selectedElem],
        ...fields
      }
    }))
  }

  const applyPresetToSelected = (name: string) => {
    const preset = PRESET_CURVES[name]
    if (preset) {
      updateSelectedAnim({
        presetName: name,
        bezier: preset.bezier,
        duration: preset.duration
      })
    }
  }

  const applyGlobalPreset = (name: string) => {
    const preset = PRESET_CURVES[name]
    if (!preset) return
    setConfig(prev => {
      const updated = { ...prev }
      ;(Object.keys(updated) as ElementKey[]).forEach(k => {
        updated[k] = { ...updated[k], presetName: name, bezier: preset.bezier, duration: preset.duration }
      })
      return updated
    })
  }

  return (
    <div style={{
      position: 'fixed',
      top: `${position.y}px`,
      left: `${position.x}px`,
      width: '380px',
      background: 'rgba(255, 255, 255, 0.72)',
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
      boxShadow: '0 20px 50px rgba(0, 0, 0, 0.12), inset 0 0 0 1px rgba(255, 255, 255, 0.5)'
    }}>
      {/* Draggable Header */}
      <div 
        onMouseDown={handleMouseDown}
        style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginBottom: '14px', borderBottom: '1px solid rgba(0, 0, 0, 0.08)',
          paddingBottom: '10px', cursor: 'grab', userSelect: 'none'
        }}
      >
        <span style={{ fontWeight: 700, letterSpacing: '0.05em', fontSize: '0.8rem' }}>Studio Motion Calibrator</span>
        <button 
          onClick={onClose} 
          style={{ background: 'rgba(0,0,0,0.06)', border: 'none', color: '#1d1d1f', borderRadius: '50%', width: '22px', height: '22px', cursor: 'pointer', fontWeight: 600 }}
        >
          ✕
        </button>
      </div>

      {/* Phase State Selector */}
      <div style={{ marginBottom: '16px', display: 'flex', gap: '8px' }}>
        <button 
          onClick={() => setInStudioMode(false)} 
          style={{ flex: 1, padding: '8px', background: !inStudioMode ? '#1d1d1f' : 'rgba(0,0,0,0.05)', color: !inStudioMode ? '#fff' : '#1d1d1f', border: 'none', fontWeight: 600, cursor: 'pointer', borderRadius: '8px', transition: 'all 0.2s' }}
        >
          Phase 1 View
        </button>
        <button 
          onClick={() => setInStudioMode(true)} 
          style={{ flex: 1, padding: '8px', background: inStudioMode ? '#1d1d1f' : 'rgba(0,0,0,0.05)', color: inStudioMode ? '#fff' : '#1d1d1f', border: 'none', fontWeight: 600, cursor: 'pointer', borderRadius: '8px', transition: 'all 0.2s' }}
        >
          Phase 2 Studio
        </button>
      </div>

      {/* Element Target Selector */}
      <div style={{ marginBottom: '16px' }}>
        <label style={{ display: 'block', fontWeight: 600, marginBottom: '6px', color: '#6e6e73' }}>Select Component to Calibrate:</label>
        <select 
          value={selectedElem}
          onChange={e => setSelectedElem(e.target.value as ElementKey)}
          style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid rgba(0,0,0,0.12)', background: 'rgba(255,255,255,0.8)', color: '#1d1d1f', fontWeight: 600, outline: 'none' }}
        >
          {Object.entries(ELEMENT_LABELS).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
      </div>

      {/* Preset Curves Grid */}
      <div style={{ marginBottom: '16px', background: 'rgba(0, 0, 0, 0.03)', padding: '12px', borderRadius: '10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <span style={{ fontWeight: 600, color: '#1d1d1f' }}>Motion Curve Preset (12)</span>
          <button 
            onClick={() => applyGlobalPreset(currentAnim.presetName)} 
            style={{ background: 'none', border: 'none', color: '#0066cc', cursor: 'pointer', fontSize: '0.65rem', textDecoration: 'underline' }}
          >
            Apply to All
          </button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px' }}>
          {Object.keys(PRESET_CURVES).map(name => (
            <button
              key={name}
              onClick={() => applyPresetToSelected(name)}
              style={{
                fontSize: '0.65rem', padding: '6px 4px', cursor: 'pointer',
                background: currentAnim.presetName === name ? '#1d1d1f' : 'rgba(255,255,255,0.7)',
                color: currentAnim.presetName === name ? '#fff' : '#1d1d1f',
                border: 'none', borderRadius: '6px', fontWeight: currentAnim.presetName === name ? 600 : 400,
                transition: 'all 0.15s'
              }}
            >
              {name}
            </button>
          ))}
        </div>
      </div>

      {/* Entry Transition Effect */}
      <div style={{ marginBottom: '16px', background: 'rgba(0, 0, 0, 0.03)', padding: '12px', borderRadius: '10px' }}>
        <label style={{ display: 'block', fontWeight: 600, marginBottom: '6px', color: '#1d1d1f' }}>Entrance Effect Type:</label>
        <select
          value={currentAnim.entryType}
          onChange={e => updateSelectedAnim({ entryType: e.target.value as any })}
          style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid rgba(0,0,0,0.12)', background: 'rgba(255,255,255,0.8)', color: '#1d1d1f', outline: 'none' }}
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
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span>Delay Offset:</span>
            <span style={{ fontWeight: 600, color: '#0066cc' }}>{currentAnim.delay}s</span>
          </div>
          <input
            type="range" min={0} max={1.5} step={0.05}
            value={currentAnim.delay}
            onChange={e => updateSelectedAnim({ delay: parseFloat(e.target.value) })}
            style={{ width: '100%', accentColor: '#1d1d1f' }}
          />
        </div>
      </div>

      {/* Granular Slider Controls */}
      <div style={{ background: 'rgba(0, 0, 0, 0.03)', padding: '12px', borderRadius: '10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
          <span>Duration:</span>
          <span style={{ fontWeight: 600, color: '#0066cc' }}>{currentAnim.duration}s</span>
        </div>
        <input
          type="range" min={0.1} max={3.0} step={0.05}
          value={currentAnim.duration}
          onChange={e => updateSelectedAnim({ duration: parseFloat(e.target.value), presetName: 'Custom' })}
          style={{ width: '100%', accentColor: '#1d1d1f', marginBottom: '10px' }}
        />

        <div style={{ color: '#6e6e73', fontSize: '0.65rem', marginBottom: '4px' }}>
          Cubic Bezier: ({currentAnim.bezier.join(', ')})
        </div>
        <div style={{ display: 'flex', gap: '4px' }}>
          {currentAnim.bezier.map((val, idx) => (
            <input
              key={idx} type="range" min={-0.5} max={2.0} step={0.05}
              value={val}
              onChange={e => {
                const nextBezier = [...currentAnim.bezier] as [number, number, number, number]
                nextBezier[idx] = parseFloat(e.target.value)
                updateSelectedAnim({ bezier: nextBezier, presetName: 'Custom' })
              }}
              style={{ width: '25%', accentColor: '#1d1d1f' }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}