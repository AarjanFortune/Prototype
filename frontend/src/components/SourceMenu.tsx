import { SourceType } from '../types/transcription'

interface SourceMenuProps {
  onSelect: (source: SourceType) => void
}

const SOURCES: Array<{ id: SourceType; label: string; detail: string }> = [
  { id: 'upload', label: 'Audio file', detail: 'Upload' },
  { id: 'youtube', label: 'YouTube', detail: 'Paste link' },
  { id: 'live', label: 'Live input', detail: 'Listen' },
]

export default function SourceMenu({ onSelect }: SourceMenuProps) {
  return (
    <section className="source-menu" aria-labelledby="source-menu-title">
      <div className="menu-copy">
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

      <div className="instrument-stage" aria-hidden="true">
        <img src="/images/Guitarica.png" alt="" />
      </div>
    </section>
  )
}
