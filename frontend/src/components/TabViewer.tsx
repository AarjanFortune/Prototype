import { useState } from 'react'
import './TabViewer.css'

interface TabViewerProps {
  tab: string[]
  confidence: number[][]
}

export default function TabViewer({ tab, confidence }: TabViewerProps) {
  const [selectedChunk, setSelectedChunk] = useState(0)
  const [showConfidence, setShowConfidence] = useState(false)

  if (!tab || tab.length === 0) {
    return <div className="tab-viewer-empty">No tablature data</div>
  }

  const currentTab = tab[selectedChunk]

  return (
    <div className="tab-viewer">
      <div className="tab-header">
        <h3>📋 Guitar Tablature</h3>
        <div className="tab-controls">
          <button
            className="toggle-button"
            onClick={() => setShowConfidence(!showConfidence)}
          >
            {showConfidence ? '📊 Hide Confidence' : '📊 Show Confidence'}
          </button>
        </div>
      </div>

      <div className="tab-display">
        <pre className="tab-content">{currentTab}</pre>
      </div>

      {tab.length > 1 && (
        <div className="chunk-navigation">
          <button
            onClick={() => setSelectedChunk(Math.max(0, selectedChunk - 1))}
            disabled={selectedChunk === 0}
            className="nav-button"
          >
            ← Previous
          </button>
          <span className="chunk-info">
            Chunk {selectedChunk + 1} of {tab.length}
          </span>
          <button
            onClick={() => setSelectedChunk(Math.min(tab.length - 1, selectedChunk + 1))}
            disabled={selectedChunk === tab.length - 1}
            className="nav-button"
          >
            Next →
          </button>
        </div>
      )}

      {showConfidence && confidence.length > 0 && (
        <div className="confidence-display">
          <h4>🎯 Prediction Confidence by String</h4>
          <div className="confidence-grid">
            {confidence[selectedChunk]?.map((conf, idx) => (
              <div key={idx} className="confidence-item">
                <span className="string-name">String {idx + 1}</span>
                <div className="confidence-bar">
                  <div
                    className="confidence-fill"
                    style={{ width: `${conf * 100}%` }}
                  />
                </div>
                <span className="confidence-value">{(conf * 100).toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="tab-info">
        <p>💡 <strong>Tab Legend:</strong> Numbers = fret positions, - = open string or muted</p>
        <p>🎸 <strong>String Order:</strong> Top to bottom = High E, B, G, D, A, Low E</p>
      </div>
    </div>
  )
}
