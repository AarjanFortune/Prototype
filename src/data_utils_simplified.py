"""
Data preprocessing and loading for TAB estimation
- Extract features from audio files (CQT)
- Create ground truth TAB from JAMS files
- Generate NPZ files for training
"""

import numpy as np
import librosa
import jams
import pretty_midi
import os
import glob
from pathlib import Path
from scipy.io import wavfile
import torch
from torch.utils.data import Dataset, DataLoader
import math


class TabDataPreprocessor:
    """Convert JAMS annotations to TAB format."""
    
    @staticmethod
    def jams_to_tab_with_onset(jam_file, tempo=120, note_resolution=16):
        """Convert JAMS file to TAB + Onset representation."""
        jam = jams.load(jam_file)
        
        # Get note annotations
        note_annos = jam.search(namespace='note_midi')
        if len(note_annos) == 0:
            note_annos = jam.search(namespace='pitch_midi')
        
        if len(note_annos) == 0:
            raise ValueError(f"No note annotations found in {jam_file}")
        
        # Calculate note duration
        note_dur = 60 / tempo / note_resolution * 4  # Duration of one 16th note
        
        # Find end time and create TAB array
        end_time = jam.file_metadata.duration if jam.file_metadata.duration else 10.0
        n_notes = int(math.ceil(end_time / note_dur))
        
        # Initialize TAB and Onset: (n_notes, 6 strings, 21 frets)
        tab = np.zeros((n_notes, 6, 21), dtype=np.float32)
        onset = np.zeros((n_notes, 6, 21), dtype=np.float32)
        
        tab[:, :, 20] = 1.0  # Initialize all as "no note"
        onset[:, :, 20] = 1.0  # Initialize all as "no onset"
        
        # String MIDI pitches (standard tuning)
        string_base_pitches = [40, 45, 50, 55, 59, 64]  # E, A, D, G, B, e
        
        # Fill in notes
        for string_idx, note_anno in enumerate(note_annos):
            if string_idx >= 6:
                break
            
            for note in note_anno:
                pitch = int(round(note.value))
                start_time = note.time
                duration = note.duration
                
                # Calculate fret number (relative to string open pitch)
                fret = pitch - string_base_pitches[string_idx]
                
                # Only include valid frets (0-19)
                if 0 <= fret <= 19:
                    # Find which notes this spans
                    start_note_idx = int(round(start_time / note_dur))
                    end_note_idx = int(round((start_time + duration) / note_dur))
                    
                    for note_idx in range(start_note_idx, end_note_idx):
                        if note_idx < n_notes:
                            tab[note_idx, string_idx, fret] = 1.0
                            tab[note_idx, string_idx, 20] = 0.0  # Clear "no note"
                            
                            # Mark onset only at the start
                            if note_idx == start_note_idx:
                                onset[note_idx, string_idx, fret] = 1.0
                                onset[note_idx, string_idx, 20] = 0.0
        
        return tab, onset
    
    @staticmethod
    def extract_cqt(audio_path, sr=22050, n_bins=192, bins_per_octave=24, hop_length=512):
        """Extract CQT features from audio."""
        # Load audio
        y, sr_orig = librosa.load(audio_path, sr=sr, mono=True)
        
        # Normalize
        y = librosa.util.normalize(y)
        
        # Extract CQT
        cqt = np.abs(librosa.cqt(
            y, sr=sr, n_bins=n_bins, bins_per_octave=bins_per_octave, 
            hop_length=hop_length
        ))
        
        # Transpose to (T, freq_bins)
        cqt = cqt.T.astype(np.float32)
        
        return cqt
    
    @staticmethod
    def process_audio_jams_pair(audio_path, jams_path, output_npz_path, 
                               sr=22050, n_bins=192, bins_per_octave=24, 
                               hop_length=512, note_resolution=16):
        """Process audio-JAMS pair and save as NPZ with onset data."""
        # Extract CQT
        cqt = TabDataPreprocessor.extract_cqt(
            audio_path, sr=sr, n_bins=n_bins, 
            bins_per_octave=bins_per_octave, hop_length=hop_length
        )
        
        # Get tempo from filename (format: *-BPM-*)
        try:
            tempo = int(jams_path.split('-')[1])
        except:
            tempo = 120
        
        # Convert JAMS to TAB + Onset
        tab, onset = TabDataPreprocessor.jams_to_tab_with_onset(
            jams_path, tempo=tempo, note_resolution=note_resolution
        )
        
        # Create frame-level TAB and Onset by repeating note-level
        frames_per_note = int((sr * 60) / (hop_length * 4 * tempo))
        frame_tab = np.repeat(tab, frames_per_note, axis=0)
        frame_onset = np.repeat(onset, frames_per_note, axis=0)
        
        # Trim or pad to match CQT length
        if frame_tab.shape[0] > cqt.shape[0]:
            frame_tab = frame_tab[:cqt.shape[0]]
            frame_onset = frame_onset[:cqt.shape[0]]
        elif frame_tab.shape[0] < cqt.shape[0]:
            pad_len = cqt.shape[0] - frame_tab.shape[0]
            frame_tab = np.pad(frame_tab, ((0, pad_len), (0, 0), (0, 0)))
            frame_onset = np.pad(frame_onset, ((0, pad_len), (0, 0), (0, 0)))
        
        # Save NPZ
        os.makedirs(os.path.dirname(output_npz_path), exist_ok=True)
        np.savez(
            output_npz_path,
            cqt=cqt,
            frame_tab=frame_tab,
            frame_onset=frame_onset,
            tab=tab,
            onset=onset,
            tempo=tempo
        )
        
        print(f"Saved: {output_npz_path}")
        print(f"  CQT shape: {cqt.shape}, Frame TAB shape: {frame_tab.shape}, Note TAB shape: {tab.shape}")


class TabDataset(Dataset):
    """PyTorch Dataset for TAB estimation with Frame + Onset + Note branches."""
    
    def __init__(self, npz_file_list, use_cqt=True):
        self.npz_file_list = npz_file_list
        self.use_cqt = use_cqt
    
    def __len__(self):
        return len(self.npz_file_list)
    
    def __getitem__(self, idx):
        npz_file = np.load(self.npz_file_list[idx])
        
        cqt = npz_file['cqt'].astype(np.float32)
        frame_tab = npz_file['frame_tab'].astype(np.float32)
        frame_onset = npz_file.get('frame_onset', frame_tab).astype(np.float32)
        tab = npz_file['tab'].astype(np.float32)
        onset = npz_file.get('onset', tab).astype(np.float32)
        tempo = float(npz_file['tempo'])
        
        return cqt, frame_tab, frame_onset, tab, onset, tempo


def pad_collate_tab(batch):
    """Custom collate function for padding variable length sequences."""
    cqts, frame_tabs, frame_onsets, tabs, onsets, tempos = zip(*batch)
    
    batch_size = len(batch)
    max_frame_len = max(x.shape[0] for x in cqts)
    max_note_len = max(x.shape[0] for x in tabs)
    
    cqt_padded = np.zeros((batch_size, max_frame_len, 192), dtype=np.float32)
    frame_tab_padded = np.zeros((batch_size, max_frame_len, 6, 21), dtype=np.float32)
    frame_onset_padded = np.zeros((batch_size, max_frame_len, 6, 21), dtype=np.float32)
    tab_padded = np.zeros((batch_size, max_note_len, 6, 21), dtype=np.float32)
    onset_padded = np.zeros((batch_size, max_note_len, 6, 21), dtype=np.float32)
    
    frame_lengths = np.zeros(batch_size, dtype=np.int32)
    note_lengths = np.zeros(batch_size, dtype=np.int32)
    
    for b in range(batch_size):
        frame_len = cqts[b].shape[0]
        note_len = tabs[b].shape[0]
        
        cqt_padded[b, :frame_len] = cqts[b]
        frame_tab_padded[b, :frame_len] = frame_tabs[b]
        frame_onset_padded[b, :frame_len] = frame_onsets[b]
        tab_padded[b, :note_len] = tabs[b]
        onset_padded[b, :note_len] = onsets[b]
        
        frame_lengths[b] = frame_len
        note_lengths[b] = note_len
    
    return (torch.from_numpy(cqt_padded).float(),
            torch.from_numpy(frame_tab_padded).float(),
            torch.from_numpy(frame_onset_padded).float(),
            torch.from_numpy(tab_padded).float(),
            torch.from_numpy(onset_padded).float(),
            torch.from_numpy(frame_lengths).long(),
            torch.from_numpy(note_lengths).long(),
            torch.from_numpy(np.array(tempos)).float())


def get_data_loaders(npz_dir, batch_size=16, train_ratio=0.8, num_workers=0):
    """Create train and validation data loaders with page-locked pin_memory."""
    npz_files = sorted(glob.glob(os.path.join(npz_dir, '*.npz')))
    
    if len(npz_files) == 0:
        raise ValueError(f"No NPZ files found in {npz_dir}")
    
    n_train = int(len(npz_files) * train_ratio)
    train_files = npz_files[:n_train]
    val_files = npz_files[n_train:]
    
    train_dataset = TabDataset(train_files)
    val_dataset = TabDataset(val_files)
    
    # Check if GPU is present to configure fast asynchronous streaming
    use_pin = torch.cuda.is_available()
    
    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, collate_fn=pad_collate_tab,
        pin_memory=use_pin
    )
    
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, collate_fn=pad_collate_tab,
        pin_memory=use_pin
    )
    
    print(f"Train samples: {len(train_files)}, Val samples: {len(val_files)}")
    
    return train_loader, val_loader