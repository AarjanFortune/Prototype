import React, { useEffect, useRef, useState } from 'react';
import './PianorollViewer.css';

interface Note {
  midi: number;
  string: number;
  fret: number;
  start_time: number;
  duration: number;
}

interface PianorollViewerProps {
  notes: Note[];
  totalDuration: number;
}

const STRING_COLORS = [
  '#E74C3C', // String 0 (E) - red
  '#3498DB', // String 1 (A) - blue
  '#2ECC71', // String 2 (D) - green
  '#F39C12', // String 3 (G) - orange
  '#9B59B6', // String 4 (B) - purple
  '#1ABC9C', // String 5 (e) - teal
];

const MIDI_NOTE_NAMES = [
  'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'
];

const getMidiNoteName = (midi: number): string => {
  const noteName = MIDI_NOTE_NAMES[midi % 12];
  const octave = Math.floor(midi / 12) - 1;
  return `${noteName}${octave}`;
};

export const PianorollViewer: React.FC<PianorollViewerProps> = ({ notes, totalDuration }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  // Constants for rendering
  const PIANO_WIDTH = 80; // Width for piano labels
  const PIANO_HEIGHT = 20; // Height per pitch
  const TIME_SCALE = 50; // pixels per second
  const TOP_MARGIN = 40;
  const LEFT_MARGIN = PIANO_WIDTH;
  const BOTTOM_MARGIN = 40;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Calculate canvas dimensions
    const width = LEFT_MARGIN + Math.max(totalDuration * TIME_SCALE, 300) + 20;
    const height = TOP_MARGIN + 88 * PIANO_HEIGHT + BOTTOM_MARGIN; // 88 standard piano keys

    setDimensions({ width, height });
    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, width, height);

    // Draw grid and piano labels
    drawPianoLabels(ctx as CanvasRenderingContext2D);
    drawTimeAxis(ctx as CanvasRenderingContext2D);
    drawGridLines(ctx as CanvasRenderingContext2D);

    // Draw note blocks
    notes.forEach((note) => {
      drawNote(ctx as CanvasRenderingContext2D, note);
    });
  }, [notes, totalDuration]);

  const drawPianoLabels = (ctx: CanvasRenderingContext2D) => {
    ctx.fillStyle = '#888';
    ctx.font = '11px monospace';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';

    // Draw MIDI notes from C0 (0) to B8 (87)
    for (let midi = 0; midi < 88; midi++) {
      const y = TOP_MARGIN + (87 - midi) * PIANO_HEIGHT + PIANO_HEIGHT / 2;
      const label = getMidiNoteName(midi);
      ctx.fillText(label, PIANO_WIDTH - 8, y);

      // Draw separator line
      ctx.strokeStyle = '#333';
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(PIANO_WIDTH, y + PIANO_HEIGHT / 2);
      ctx.lineTo(dimensions.width, y + PIANO_HEIGHT / 2);
      ctx.stroke();
    }
  };

  const drawTimeAxis = (ctx: CanvasRenderingContext2D) => {
    ctx.fillStyle = '#888';
    ctx.font = '12px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';

    const maxTime = Math.ceil(totalDuration);
    for (let t = 0; t <= maxTime; t++) {
      const x = LEFT_MARGIN + t * TIME_SCALE;
      if (x > dimensions.width - 20) break;

      ctx.fillText(t.toString(), x, dimensions.height - BOTTOM_MARGIN + 10);

      // Draw tick mark
      ctx.strokeStyle = '#555';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, dimensions.height - BOTTOM_MARGIN);
      ctx.lineTo(x, dimensions.height - BOTTOM_MARGIN + 5);
      ctx.stroke();
    }

    // Draw "Time (s)" label
    ctx.fillText('Time (s)', dimensions.width / 2, dimensions.height - BOTTOM_MARGIN + 25);
  };

  const drawGridLines = (ctx: CanvasRenderingContext2D) => {
    ctx.strokeStyle = '#222';
    ctx.lineWidth = 0.5;

    // Vertical grid lines (every 0.5 seconds)
    for (let t = 0; t <= Math.ceil(totalDuration); t += 0.5) {
      const x = LEFT_MARGIN + t * TIME_SCALE;
      if (x > dimensions.width - 20) break;

      ctx.beginPath();
      ctx.moveTo(x, TOP_MARGIN);
      ctx.lineTo(x, dimensions.height - BOTTOM_MARGIN);
      ctx.stroke();
    }

    // Horizontal lines at octave boundaries
    for (let octave = 0; octave <= 8; octave++) {
      const midi = octave * 12; // C of that octave
      if (midi >= 88) break;

      const y = TOP_MARGIN + (87 - midi) * PIANO_HEIGHT;
      ctx.strokeStyle = '#333';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(PIANO_WIDTH, y);
      ctx.lineTo(dimensions.width, y);
      ctx.stroke();
    }
  };

  const drawNote = (ctx: CanvasRenderingContext2D, note: Note) => {
    if (note.duration <= 0) return;

    const x = LEFT_MARGIN + note.start_time * TIME_SCALE;
    const width = Math.max(note.duration * TIME_SCALE, 3); // Minimum width of 3px
    const y = TOP_MARGIN + (87 - note.midi) * PIANO_HEIGHT;
    const height = PIANO_HEIGHT - 2;

    // Set color based on string
    ctx.fillStyle = STRING_COLORS[note.string % 6];

    // Draw note rectangle
    ctx.fillRect(x, y, width, height);

    // Draw border
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 1;
    ctx.strokeRect(x, y, width, height);

    // Draw fret number if note is wide enough
    if (width > 25) {
      ctx.fillStyle = '#000';
      ctx.font = 'bold 10px monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(note.fret.toString(), x + width / 2, y + height / 2);
    }
  };

  return (
    <div className="pianoroll-container">
      <div className="pianoroll-header">
        <h3>Pianoroll Visualization</h3>
        <p className="pianoroll-info">
          Each colored block represents a note. Height = pitch, Width = duration, Color = string
        </p>
      </div>
      <canvas ref={canvasRef} className="pianoroll-canvas" />
    </div>
  );
};
