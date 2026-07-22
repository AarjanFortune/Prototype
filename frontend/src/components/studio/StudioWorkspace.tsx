import React from 'react'
import UploadTab from '../tabs/UploadTab'
import YouTubeTab from '../tabs/YouTubeTab'
import LiveStreamTab from '../tabs/LiveStreamTab'
import { SingleElementAnim } from './StudioCalibrator'

type TabType = 'upload' | 'youtube' | 'live'

interface WorkspaceProps {
  activeTab: TabType
  setActiveTab: (tab: TabType) => void
  onClose: () => void
  navAnim: SingleElementAnim
  formAnim: SingleElementAnim
  closeBtnAnim: SingleElementAnim
}

export default function StudioWorkspace({
  activeTab,
  setActiveTab,
  onClose,
  navAnim,
  formAnim,
  closeBtnAnim
}: WorkspaceProps) {
  const getStyleFor = (anim: SingleElementAnim): React.CSSProperties => {
    const cubic = `cubic-bezier(${anim.bezier.join(', ')})`
    return {
      animation: `anim-${anim.entryType} ${anim.duration}s ${cubic} ${anim.delay}s both`
    }
  }

  return (
    <div style={{ position: 'relative', zIndex: 5, display: 'flex', flexDirection: 'column', height: '100%', width: '100%' }}>
      <style>{`
        @keyframes anim-fade { from { opacity: 0; } to { opacity: 1; } }
        @keyframes anim-slide-up { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes anim-slide-down { from { opacity: 0; transform: translateY(-30px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes anim-slide-left { from { opacity: 0; transform: translateX(40px); } to { opacity: 1; transform: translateX(0); } }
        @keyframes anim-slide-right { from { opacity: 0; transform: translateX(-40px); } to { opacity: 1; transform: translateX(0); } }
        @keyframes anim-scale-up { from { opacity: 0; transform: scale(0.88); } to { opacity: 1; transform: scale(1); } }
        @keyframes anim-blur-in { from { opacity: 0; filter: blur(12px); } to { opacity: 1; filter: blur(0px); } }
        @keyframes anim-bounce {
          0% { opacity: 0; transform: translateY(35px); }
          70% { transform: translateY(-6px); }
          100% { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Header Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginLeft: '160px' }}>
          <div style={{ display: 'flex', gap: '28px', ...getStyleFor(navAnim) }}>
            {(['upload', 'youtube', 'live'] as TabType[]).map((tab) => (
              <button
                key={tab}
                onClick={(e) => { e.stopPropagation(); setActiveTab(tab); }}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '0.75rem',
                  fontWeight: activeTab === tab ? 600 : 400,
                  textTransform: 'uppercase',
                  letterSpacing: '0.15em',
                  color: activeTab === tab ? 'var(--color-ink)' : 'var(--color-muted)',
                  cursor: 'pointer',
                  paddingBottom: '4px',
                  borderBottom: activeTab === tab ? '2px solid var(--color-ink)' : '2px solid transparent',
                  transition: 'color 0.2s, border-color 0.2s'
                }}
              >
                {tab === 'upload' && 'Upload File'}
                {tab === 'youtube' && 'YouTube Link'}
                {tab === 'live' && 'Live Stream'}
              </button>
            ))}
          </div>
        </div>

        <button 
          onClick={(e) => { e.stopPropagation(); onClose(); }}
          style={{ ...getStyleFor(closeBtnAnim), background: 'none', border: 'none', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.15em', color: 'var(--color-muted)', cursor: 'pointer', fontWeight: 500 }}
        >
          Close Studio
        </button>
      </div>

      {/* Form Content */}
      <div style={{ display: 'flex', flex: 1, width: '100%', minHeight: 0, marginTop: '56px' }}>
        <div style={{ ...getStyleFor(formAnim), flex: '0 0 45%', display: 'flex', flexDirection: 'column', justifyContent: 'flex-start', paddingTop: '10px' }}>
          <div style={{ width: '100%' }} onClick={(e) => e.stopPropagation()}>
            {activeTab === 'upload' && <UploadTab />}
            {activeTab === 'youtube' && <YouTubeTab />}
            {activeTab === 'live' && <LiveStreamTab />}
          </div>
        </div>
        <div style={{ flex: '0 0 55%', pointerEvents: 'none' }} />
      </div>
    </div>
    import React from 'react'
import UploadTab from '../tabs/UploadTab'
import YouTubeTab from '../tabs/YouTubeTab'
import LiveStreamTab from '../tabs/LiveStreamTab'
import { SingleElementAnim } from './StudioCalibrator'

type TabType = 'upload' | 'youtube' | 'live'

interface WorkspaceProps {
  activeTab: TabType
  setActiveTab: (tab: TabType) => void
  onClose: () => void
  navAnim: SingleElementAnim
  formAnim: SingleElementAnim
  closeBtnAnim: SingleElementAnim
}

export default function StudioWorkspace({
  activeTab,
  setActiveTab,
  onClose,
  navAnim,
  formAnim,
  closeBtnAnim
}: WorkspaceProps) {
  const getStyleFor = (anim: SingleElementAnim): React.CSSProperties => {
    const cubic = `cubic-bezier(${anim.bezier.join(', ')})`
    return {
      animation: `anim-${anim.entryType} ${anim.duration}s ${cubic} ${anim.delay}s both`
    }
  }

  return (
    <div style={{ position: 'relative', zIndex: 5, display: 'flex', flexDirection: 'column', height: '100%', width: '100%' }}>
      <style>{`
        @keyframes anim-fade { from { opacity: 0; } to { opacity: 1; } }
        @keyframes anim-slide-up { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes anim-slide-down { from { opacity: 0; transform: translateY(-30px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes anim-slide-left { from { opacity: 0; transform: translateX(40px); } to { opacity: 1; transform: translateX(0); } }
        @keyframes anim-slide-right { from { opacity: 0; transform: translateX(-40px); } to { opacity: 1; transform: translateX(0); } }
        @keyframes anim-scale-up { from { opacity: 0; transform: scale(0.88); } to { opacity: 1; transform: scale(1); } }
        @keyframes anim-blur-in { from { opacity: 0; filter: blur(12px); } to { opacity: 1; filter: blur(0px); } }
        @keyframes anim-bounce {
          0% { opacity: 0; transform: translateY(35px); }
          70% { transform: translateY(-6px); }
          100% { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Header Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginLeft: '160px' }}>
          <div style={{ display: 'flex', gap: '28px', ...getStyleFor(navAnim) }}>
            {(['upload', 'youtube', 'live'] as TabType[]).map((tab) => (
              <button
                key={tab}
                onClick={(e) => { e.stopPropagation(); setActiveTab(tab); }}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '0.75rem',
                  fontWeight: activeTab === tab ? 600 : 400,
                  textTransform: 'uppercase',
                  letterSpacing: '0.15em',
                  color: activeTab === tab ? 'var(--color-ink)' : 'var(--color-muted)',
                  cursor: 'pointer',
                  paddingBottom: '4px',
                  borderBottom: activeTab === tab ? '2px solid var(--color-ink)' : '2px solid transparent',
                  transition: 'color 0.2s, border-color 0.2s'
                }}
              >
                {tab === 'upload' && 'Upload File'}
                {tab === 'youtube' && 'YouTube Link'}
                {tab === 'live' && 'Live Stream'}
              </button>
            ))}
          </div>
        </div>

        <button 
          onClick={(e) => { e.stopPropagation(); onClose(); }}
          style={{ ...getStyleFor(closeBtnAnim), background: 'none', border: 'none', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.15em', color: 'var(--color-muted)', cursor: 'pointer', fontWeight: 500 }}
        >
          Close Studio
        </button>
      </div>

      {/* Form Content */}
      <div style={{ display: 'flex', flex: 1, width: '100%', minHeight: 0, marginTop: '56px' }}>
        <div style={{ ...getStyleFor(formAnim), flex: '0 0 45%', display: 'flex', flexDirection: 'column', justifyContent: 'flex-start', paddingTop: '10px' }}>
          <div style={{ width: '100%' }} onClick={(e) => e.stopPropagation()}>
            {activeTab === 'upload' && <UploadTab />}
            {activeTab === 'youtube' && <YouTubeTab />}
            {activeTab === 'live' && <LiveStreamTab />}
          </div>
        </div>
        <div style={{ flex: '0 0 55%', pointerEvents: 'none' }} />
      </div>
    </div>
  )
  
}

  
}
