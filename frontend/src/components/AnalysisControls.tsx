import { FeatureType } from '../types/transcription'

interface AnalysisControlsProps {
  featureType: FeatureType
  onFeatureTypeChange: (featureType: FeatureType) => void
}

export default function AnalysisControls({
  featureType,
  onFeatureTypeChange,
}: AnalysisControlsProps) {
  return (
    <label className="field">
      <span className="field-label">Analysis engine</span>
      <select
        className="text-input"
        value={featureType}
        onChange={(event) => onFeatureTypeChange(event.target.value as FeatureType)}
      >
        <option value="cqt">Constant-Q pitch tracking</option>
        <option value="mel">Mel spectral analysis</option>
      </select>
    </label>
  )
}
