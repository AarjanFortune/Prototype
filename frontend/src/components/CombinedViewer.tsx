import React, { useRef } from 'react';
import html2pdf from 'html2pdf.js';
import TabViewer from './TabViewer';
import { PianorollViewer } from './PianorollViewer';
import './CombinedViewer.css';

interface Note {
  midi: number;
  string: number;
  fret: number;
  start_time: number;
  duration: number;
}

interface PianorollData {
  notes: Note[];
  total_duration: number;
}

interface CombinedViewerProps {
  tabData: string[];
  confidenceData?: number[][];
  pianorollData?: PianorollData;
  metadata?: {
    duration?: number;
    tempo?: number;
    frames?: number;
  };
}

export const CombinedViewer: React.FC<CombinedViewerProps> = ({
  tabData,
  confidenceData,
  pianorollData,
  metadata,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  const handleExportPDF = async () => {
    if (!containerRef.current) return;

    try {
      const element = containerRef.current;
      const opt = {
        margin: 10,
        filename: 'guitar-transcription.pdf',
        image: { type: 'jpeg' as any, quality: 0.98 },
        html2canvas: { scale: 2 },
        jsPDF: { orientation: 'landscape' as any, unit: 'mm', format: 'a4' },
      };

      html2pdf().set(opt).from(element).save();
    } catch (error) {
      console.error('Failed to export PDF:', error);
      alert('Failed to export PDF. Check console for details.');
    }
  };

  const hasPianoroll = pianorollData && pianorollData.notes.length > 0;

  return (
    <div className="combined-viewer">
      <div className="combined-header">
        <h2>Guitar Transcription Results</h2>
        {metadata && (
          <div className="combined-metadata">
            {metadata.duration && (
              <span>Duration: {metadata.duration.toFixed(1)}s</span>
            )}
            {metadata.tempo && <span>Tempo: {metadata.tempo.toFixed(0)} BPM</span>}
            {metadata.frames && <span>Frames: {metadata.frames}</span>}
          </div>
        )}
        <button className="export-btn" onClick={handleExportPDF}>
          📥 Export as PDF
        </button>
      </div>

      <div
        ref={containerRef}
        className={`combined-content ${hasPianoroll ? 'with-pianoroll' : ''}`}
      >
        {hasPianoroll ? (
          <>
            <div className="pianoroll-section">
              <PianorollViewer
                notes={pianorollData.notes}
                totalDuration={pianorollData.total_duration}
              />
            </div>
            <div className="tab-section">
              <TabViewer tab={tabData} confidence={confidenceData || []} />
            </div>
          </>
        ) : (
          <div className="tab-section full-width">
            <TabViewer tab={tabData} confidence={confidenceData || []} />
          </div>
        )}
      </div>
    </div>
  );
};
