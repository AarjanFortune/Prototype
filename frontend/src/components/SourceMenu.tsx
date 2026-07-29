import { SourceType } from '../types/transcription'
import { VisualConfig, visualStyle } from '../visualConfig'

interface SourceMenuProps {
  onSelect: (source: SourceType) => void
  onGuitarClick: () => void
  visualConfig: VisualConfig
}

const SOURCES: Array<{ id: SourceType; label: string; detail: string }> = [
  { id: 'upload', label: 'Audio file', detail: 'Upload' },
  { id: 'youtube', label: 'YouTube', detail: 'Paste link' },
  { id: 'live', label: 'Live input', detail: 'Listen' },
]

export default function SourceMenu({ onSelect, onGuitarClick, visualConfig }: SourceMenuProps) {
  return (
    <section className="source-menu" aria-labelledby="source-menu-title">
      <div className="menu-copy" style={visualStyle(visualConfig.menuContent)}>
        <p>Transcription studio</p>
        <h1 id="source-menu-title">Choose source</h1>

        <nav className="menu-options" aria-label="Choose audio source">
          {SOURCES.map((source, index) => (
            <button key={source.id} type="button" onClick={() => onSelect(source.id)}>
              <span className="menu-number">0{index + 1}</span>
              <span className="menu-label">{source.label}</span>
              <span className="menu-detail">{source.detail}</span>
            </button>
          ))}
        </nav>
      </div>

      <button
        type="button"
        className="instrument-stage"
        style={visualStyle(visualConfig.menuGuitar)}
        onClick={onGuitarClick}
        aria-label="Play Guitarica sound"
      >
        <img src="/images/Guitarica.png" alt="" />
      </button>
    </section>
  )
}
