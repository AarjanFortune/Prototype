"""
Simplified inference script for TAB estimation
- Load trained model
- Make predictions on audio files
- Output TAB notation
"""

import torch
import torch.nn as nn
import numpy as np
import yaml
import argparse
import os
from pathlib import Path
import librosa

from network_simplified import SimpleTabEstimator
from data_utils_simplified import TabDataPreprocessor


class TabPredictor:
    """Make predictions with trained TAB estimator model."""
    
    def __init__(self, config_path, model_path, device='cuda' if torch.cuda.is_available() else 'cpu'):
        """
        Initialize predictor.
        
        Args:
            config_path: path to config YAML
            model_path: path to trained model checkpoint
            device: torch device
        """
        self.device = device
        
        # Load config
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        # Load model
        self.model = SimpleTabEstimator(self.config).to(device)
        
        checkpoint = torch.load(model_path, map_location=device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        
        print(f"✓ Loaded model from {model_path}")
    
    def predict_audio(self, audio_path):
        """
        Make TAB prediction on audio file.
        
        Args:
            audio_path: path to audio file
        
        Returns:
            frame_tab_pred: (T, 6, 21) frame-level predictions
            onset_tab_pred: (T, 6, 21) onset-level predictions
            note_tab_pred: (T_note, 6, 21) note-level predictions
            cqt: (T, 192) input features
        """
        # Extract features
        cqt = TabDataPreprocessor.extract_cqt(
            audio_path,
            sr=self.config['down_sampling_rate'],
            n_bins=self.config['cqt_n_bins'],
            bins_per_octave=self.config['bins_per_octave'],
            hop_length=self.config['hop_length']
        )
        
        # Convert to tensor
        cqt_tensor = torch.from_numpy(cqt).unsqueeze(0).float().to(self.device)  # (1, T, 192)
        
        # Get sequence length
        seq_len = torch.tensor([cqt.shape[0]], dtype=torch.long, device=self.device)
        
        # Predict with BPM
        bpm_tensor = torch.tensor([120.0], dtype=torch.float, device=self.device)
        with torch.no_grad():
            frame_pred, onset_pred, note_pred, _ = self.model(cqt_tensor, seq_len, bpm=bpm_tensor)
        
        # Convert to numpy
        frame_tab_pred = frame_pred[0].cpu().numpy()  # (T, 6, 21)
        onset_tab_pred = onset_pred[0].cpu().numpy()  # (T, 6, 21)
        note_tab_pred = note_pred[0].cpu().numpy()  # (T_note, 6, 21)
        
        return frame_tab_pred, onset_tab_pred, note_tab_pred, cqt
    
    def get_tab_notation(self, tab_pred, threshold=0.5):
        """
        Convert TAB predictions to TAB notation.
        
        Args:
            tab_pred: (T, 6, 21) TAB predictions
            threshold: confidence threshold (0-1)
        
        Returns:
            tab_notation: (T, 6) - fret numbers (20 = no note)
        """
        # For each position and string, find the fret with highest confidence
        fret_numbers = np.argmax(tab_pred[:, :, :20], axis=2)  # Argmax over frets 0-19
        
        # Set confidence threshold - if max confidence < threshold, mark as "no note" (20)
        max_confidence = np.max(tab_pred[:, :, :20], axis=2)
        fret_numbers[max_confidence < threshold] = 20
        
        return fret_numbers.astype(np.int32)
    
    def print_tab_notation(self, tab_notation, title="TAB NOTATION", bpm=120, note_resolution=16):
        """
        Print TAB notation in human-readable format.
        
        Args:
            tab_notation: (T, 6) - fret numbers
            title: title to print
            bpm: tempo in beats per minute
            note_resolution: notes per beat
        """
        # String names
        string_names = ['E', 'A', 'D', 'G', 'B', 'e']
        
        # Calculate note duration in frames
        sr = self.config['down_sampling_rate']
        hop_length = self.config['hop_length']
        note_dur_sec = 60 / bpm / note_resolution * 4
        note_dur_frames = int((note_dur_sec * sr) / hop_length)
        
        print("\n" + "="*60)
        print(title)
        print("="*60)
        
        # Downsample to note level (approximately)
        note_level_tab = tab_notation[::note_dur_frames] if note_dur_frames > 0 else tab_notation
        
        # Print in standard TAB format (6 lines, one per string)
        for string_idx in range(6):
            line = string_names[string_idx] + ": "
            for fret in note_level_tab[:, string_idx]:
                if fret == 20:
                    line += "- "
                else:
                    line += f"{fret:2d} "
            print(line)
        
        print("="*60 + "\n")
    
    def save_predictions(self, tab_notation, output_path):
        """
        Save TAB notation to file.
        
        Args:
            tab_notation: (T, 6) - fret numbers
            output_path: where to save
        """
        np.save(output_path, tab_notation)
        print(f"✓ Saved predictions to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Predict TAB from audio')
    parser.add_argument('--audio', type=str, required=True,
                      help='Path to audio file')
    parser.add_argument('--model', type=str, required=True,
                      help='Path to trained model checkpoint')
    parser.add_argument('--config', type=str, default='config_simplified.yaml',
                      help='Path to config file')
    parser.add_argument('--bpm', type=int, default=120,
                      help='Tempo in BPM (for display)')
    parser.add_argument('--threshold', type=float, default=0.5,
                      help='Confidence threshold for predictions (0-1)')
    parser.add_argument('--output', type=str, default=None,
                      help='Where to save predictions (NPY file)')
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("TAB ESTIMATOR - INFERENCE")
    print("Three Branches: Frame, Onset, Note")
    print("="*60 + "\n")
    
    # Check files exist
    if not os.path.exists(args.audio):
        print(f"❌ ERROR: Audio file not found: {args.audio}")
        return
    
    if not os.path.exists(args.model):
        print(f"❌ ERROR: Model file not found: {args.model}")
        return
    
    if not os.path.exists(args.config):
        print(f"❌ ERROR: Config file not found: {args.config}")
        return
    
    # Get device
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Using device: {device}\n")
    
    # Create predictor
    predictor = TabPredictor(args.config, args.model, device=device)
    
    # Make prediction
    print(f"Predicting TAB for: {args.audio}")
    frame_pred, onset_pred, note_pred, cqt = predictor.predict_audio(args.audio)
    
    # Get TAB notation
    print(f"Frame predictions shape: {frame_pred.shape}")
    print(f"Onset predictions shape: {onset_pred.shape}")
    print(f"Note predictions shape: {note_pred.shape}")
    
    # Use note-level predictions for notation
    frame_tab_notation = predictor.get_tab_notation(frame_pred, threshold=args.threshold)
    onset_tab_notation = predictor.get_tab_notation(onset_pred, threshold=args.threshold)
    note_tab_notation = predictor.get_tab_notation(note_pred, threshold=args.threshold)
    
    # Print all three branches
    predictor.print_tab_notation(frame_tab_notation, title="FRAME-LEVEL TAB", bpm=args.bpm)
    predictor.print_tab_notation(onset_tab_notation, title="ONSET-LEVEL TAB", bpm=args.bpm)
    predictor.print_tab_notation(note_tab_notation, title="NOTE-LEVEL TAB", bpm=args.bpm)
    
    # Save if requested
    if args.output:
        os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else '.', exist_ok=True)
        
        # Save all three predictions
        output_base = args.output.replace('.npy', '')
        predictor.save_predictions(frame_tab_notation, f"{output_base}_frame.npy")
        predictor.save_predictions(onset_tab_notation, f"{output_base}_onset.npy")
        predictor.save_predictions(note_tab_notation, f"{output_base}_note.npy")
    
    print("✓ Inference complete!")


if __name__ == '__main__':
    main()
