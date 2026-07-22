import React, { useRef } from 'react';
import html2pdf from 'html2pdf.js';
import TabViewer from './TabViewer';

interface CombinedViewerProps {
  tabData: string[];
  confidenceData?: number[][];
}

export const CombinedViewer: React.FC<CombinedViewerProps> = ({ tabData, confidenceData }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  const handleExport = () => {
    if (!containerRef.current) return;
    html2pdf().set({
      margin: 15,
      filename: 'guitar-tab.pdf',
      jsPDF: { orientation: 'landscape', format: 'a4' }
    }).from(containerRef.current).save();
  };

  const sectionStyle: React.CSSProperties = {
    width: '100%', display: 'flex', flexDirection: 'column', gap: '32px', textAlign: 'left'
  }

  const headerStyle: React.CSSProperties = {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    borderBottom: '1px solid var(--color-border)', paddingBottom: '16px'
  }

  const headingStyle: React.CSSProperties = {
    fontFamily: 'var(--font-serif)', fontSize: '1.4rem', fontWeight: 400
  }

  const exportBtnStyle: React.CSSProperties = {
    background: 'transparent', border: '1px solid var(--color-ink)', color: 'var(--color-ink)',
    padding: '8px 20px', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.1em',
    fontWeight: 600, cursor: 'pointer'
  }

  return (
    <div style={sectionStyle}>
      <div style={headerStyle}>
        <h3 style={headingStyle}>Generated Tablature</h3>
        <button style={exportBtnStyle} onClick={handleExport}>Save Document</button>
      </div>
      
      <div ref={containerRef} style={{ background: '#ffffff', padding: '24px 0' }}>
        <TabViewer tab={tabData} confidence={confidenceData || []} />
      </div>
    </div>
  );
};