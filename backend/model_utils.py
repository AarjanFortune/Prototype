"""Model loading and inference utilities

Implements the full TabEstimator architecture from Refactor-TabEstimator:
- ConvStack: Optional CNN preprocessing layer
- Main Encoder: Transformer or Conformer-like architecture
- Frame-level output heads
- Note-level encoder for refinement
- Tempo-aware decimation from frame-level to note-level (64 notes)
- Softmax per string for tablature predictions
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, Optional
from config import MODEL_CONFIG, N_STRINGS, NOT_PLAYED_IDX, GUITAR_TUNING, BATCH_SIZE


class ConvStack(nn.Module):
    """
    Convolutional feature extraction layer (optional preprocessing).
    
    Applies CNN to extract local features from spectrograms before
    feeding into the transformer/conformer encoder.
    
    Architecture:
        Input (batch, n_frames, n_bins)
        → Reshape to (batch, 1, n_bins, n_frames)
        → Conv2d layers with ReLU, BatchNorm, MaxPool, Dropout
        → Fully connected layer
        → Output (batch, n_frames, output_features)
    """
    
    def __init__(self, input_features: int, output_features: int = 512):
        """
        Initialize CNN stack.
        
        Args:
            input_features (int): Number of frequency bins (e.g., 192 for CQT)
            output_features (int): Output embedding dimension (e.g., 512)
        """
        super(ConvStack, self).__init__()
        
        # CNN layers: 3×3 kernels, stride=1, padding=1
        self.cnn = nn.Sequential(
            # Layer 0: 1 → output_features/16 channels
            nn.Conv2d(1, output_features // 16, (3, 3), padding=1),
            nn.BatchNorm2d(output_features // 16),
            nn.ReLU(),
            
            # Layer 1: Same channels, another conv
            nn.Conv2d(output_features // 16, output_features // 16, (3, 3), padding=1),
            nn.BatchNorm2d(output_features // 16),
            nn.ReLU(),
            
            # Reduce time dimension by 2×
            nn.MaxPool2d((1, 2)),
            nn.Dropout(0.25),
            
            # Layer 2: Increase channels
            nn.Conv2d(output_features // 16, output_features // 8, (3, 3), padding=1),
            nn.BatchNorm2d(output_features // 8),
            nn.ReLU(),
            
            # Reduce time dimension by 2× again (total 4× reduction)
            nn.MaxPool2d((1, 2)),
            nn.Dropout(0.25),
        )
        
        # Fully connected layer to project to output dimension
        # After 2 maxpool operations: time is reduced by 4, freq unchanged
        self.fc = nn.Sequential(
            nn.Linear(
                (output_features // 8) * input_features,
                output_features
            ),
            nn.Dropout(0.5)
        )
    
    def forward(self, X: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through CNN stack.
        
        Args:
            X (torch.Tensor): Input spectrogram
                Shape: (batch, time_frames, freq_bins)
                
        Returns:
            torch.Tensor: Extracted features
                Shape: (batch, time_frames // 4, output_features)
        """
        # CNN expects (batch, channels, freq, time)
        # Input shape: (batch, time, freq) → (batch, 1, freq, time)
        X = X.permute(0, 2, 1).unsqueeze(1)  # (batch, 1, freq, time)
        
        # Apply CNN
        y = self.cnn(X)  # (batch, channels, freq/4, time/4)
        
        # Transpose to (batch, time, channels, freq)
        y = y.permute(0, 3, 1, 2)
        
        # Flatten channels and freq: (batch, time, channels*freq)
        y = y.reshape(y.size(0), y.size(1), -1)
        
        # Apply fully connected layer: (batch, time, output_features)
        y = self.fc(y)
        
        return y


class ConformerBlock(nn.Module):
    """
    Conformer block: Self-Attention + Feed-Forward + Convolution.
    
    Based on "Conformer: Convolution-augmented Transformer for Speech Recognition"
    Combines multi-head self-attention with convolution for audio processing.
    """
    
    def __init__(self, d_model: int = 64, nhead: int = 1, d_ff: int = 256,
                 conv_kernel_size: int = 3, dropout: float = 0.1):
        super(ConformerBlock, self).__init__()
        
        # Pre-norm layer normalization
        self.norm1 = nn.LayerNorm(d_model)
        
        # Multi-head self-attention
        self.self_attn = nn.MultiheadAttention(
            d_model, nhead, dropout=dropout, batch_first=True
        )
        
        # Feed-forward network
        self.norm2 = nn.LayerNorm(d_model)
        self.ff = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout),
        )
        
        # Convolution module
        self.norm3 = nn.LayerNorm(d_model)
        self.conv = nn.Sequential(
            nn.Conv1d(d_model, d_model, conv_kernel_size, padding=conv_kernel_size//2),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x: torch.Tensor, src_key_padding_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass through Conformer block.
        
        Args:
            x: (batch, seq_len, d_model)
            src_key_padding_mask: (batch, seq_len) boolean mask
            
        Returns:
            (batch, seq_len, d_model)
        """
        # Self-attention block (with pre-norm)
        x_norm = self.norm1(x)
        attn_out, _ = self.self_attn(x_norm, x_norm, x_norm, 
                                      key_padding_mask=src_key_padding_mask)
        x = x + self.dropout(attn_out)
        
        # Feed-forward block (with pre-norm)
        x_norm = self.norm2(x)
        ff_out = self.ff(x_norm)
        x = x + self.dropout(ff_out)
        
        # Convolution block (with pre-norm)
        x_norm = self.norm3(x)
        # Conv expects (batch, d_model, seq_len)
        conv_out = self.conv(x_norm.permute(0, 2, 1)).permute(0, 2, 1)
        x = x + self.dropout(conv_out)
        
        return x


class TabEstimator(nn.Module):
    """
    Main neural network for guitar tab estimation.
    
    Architecture:
    - Optional ConvStack: Initial CNN feature extraction
    - Main Encoder: Conformer or Transformer layers
    - Frame-level output head: Predicts tab/F0 for each frame
    - Note-level encoder: Refines predictions after decimation to 64 notes
    - Tempo-aware decimation: Converts frame-level to note-level
    
    Outputs:
    - Frame-level predictions: (batch, n_frames, 6, 21) for tab mode
    - Note-level predictions: (batch, 64, 6, 21) for tab mode
    - Output lengths: (batch,) - valid frame counts
    """
    
    def __init__(self, config: Dict):
        super().__init__()
        self.config = config
        
        n_bins = config['n_bins']
        hop_length = config['hop_length']
        sr = config['sr']
        mode = config['mode']
        encoder_type = config['encoder_type']
        use_conv_stack = config.get('use_conv_stack', True)
        
        self.mode = mode
        self.hop_length = hop_length
        self.sr = sr
        self.encoder_output_size = 64
        self.n_encoder_ffn = 256
        self.conv_output_features = 512
        
        # Optional CNN preprocessing
        if use_conv_stack:
            self.conv_stack = ConvStack(n_bins, self.conv_output_features)
            encoder_input_size = self.conv_output_features
        else:
            self.conv_stack = None
            encoder_input_size = n_bins
        
        # Main encoder: Transformer-like or Conformer
        num_encoder_layers = config.get('encoder_layers', 2)
        num_encoder_heads = config.get('encoder_heads', 1)
        
        if encoder_type == "conformer":
            self.encoder_layers = nn.ModuleList([
                ConformerBlock(
                    d_model=self.encoder_output_size,
                    nhead=num_encoder_heads,
                    d_ff=self.n_encoder_ffn,
                    dropout=0.1
                ) for _ in range(num_encoder_layers)
            ])
        else:  # transformer
            self.encoder_layers = nn.ModuleList([
                nn.TransformerEncoderLayer(
                    d_model=self.encoder_output_size,
                    nhead=num_encoder_heads,
                    dim_feedforward=self.n_encoder_ffn,
                    batch_first=True,
                    dropout=0.1
                ) for _ in range(num_encoder_layers)
            ])
        
        # Linear projection to encoder dimension
        self.input_projection = nn.Linear(encoder_input_size, self.encoder_output_size)
        self.encoder_norm = nn.LayerNorm(self.encoder_output_size)
        
        # Frame-level output heads
        if mode == "F0":
            # 44 MIDI pitch classes
            self.frame_output_layer = nn.Sequential(
                nn.Linear(self.encoder_output_size, 44),
                nn.Sigmoid()
            )
        else:  # tab mode
            # 126 outputs (6 strings × 21 values)
            self.frame_output_layer = nn.Sequential(
                nn.Dropout(0.25),
                nn.Linear(self.encoder_output_size, 128),
                nn.ReLU(),
                nn.Dropout(0.5),
                nn.Linear(128, 126),
            )
            self.softmax_by_string = nn.Softmax(dim=3)
        
        # Note-level encoder (Conformer for refinement)
        self.note_encoder = ConformerBlock(
            d_model=self.encoder_output_size,
            nhead=num_encoder_heads,
            d_ff=self.n_encoder_ffn,
            dropout=0.1
        )
        
        # Note-level output heads
        if mode == "F0":
            self.note_output_layer = nn.Sequential(
                nn.Linear(self.encoder_output_size, 44),
                nn.Sigmoid()
            )
        else:  # tab mode
            self.note_output_layer = nn.Sequential(
                nn.Dropout(0.25),
                nn.Linear(self.encoder_output_size, 128),
                nn.ReLU(),
                nn.Dropout(0.5),
                nn.Linear(128, 126),
            )
    
    def forward(self, src_pad: torch.Tensor, src_len: torch.Tensor,
                note_len: torch.Tensor = None, bpm: torch.Tensor = None) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass through the model.
        
        Args:
            src_pad (torch.Tensor): Input features (padded)
                Shape: (batch, n_frames, n_bins)
            src_len (torch.Tensor): Actual frame lengths (before padding)
                Shape: (batch,)
            note_len (torch.Tensor): Actual note lengths
                Shape: (batch,)
            bpm (torch.Tensor): Tempo in BPM for decimation
                Shape: (batch,)
                
        Returns:
            Tuple of:
            - frame_pred: Frame-level predictions (batch, n_frames, outputs)
            - note_pred: Note-level predictions (batch, 64, outputs)
            - olens: Output lengths (batch,)
        """
        batch_size = src_pad.shape[0]
        
        # Optional CNN preprocessing
        if self.conv_stack is not None:
            encoder_in = self.conv_stack(src_pad)
            # Note: ConvStack reduces time dimension by ~4
            # Adjust src_len accordingly
            src_len = (src_len.float() / 4).int()
        else:
            encoder_in = src_pad
        
        # Project to encoder dimension
        encoder_in = self.input_projection(encoder_in)
        encoder_in = self.encoder_norm(encoder_in)
        
        # Create padding mask
        mask = self._get_sequence_mask(src_len, encoder_in.shape[1], encoder_in.device)
        
        # Main encoder: Apply all layers
        memory = encoder_in
        for layer in self.encoder_layers:
            memory = layer(memory, src_key_padding_mask=mask)
        
        olens = src_len
        
        # Decimate from frame-level to note-level (64 notes)
        with torch.no_grad():
            if bpm is not None:
                decimated_memory = self.notelevel_decimation(memory, bpm)
            else:
                # Simple interpolation to 64 notes
                decimated_memory = torch.zeros(
                    batch_size, 64, self.encoder_output_size
                ).to(memory.device)
                
                for n_batch in range(batch_size):
                    # Interpolate to 64 notes
                    valid_frames = memory[n_batch, :olens[n_batch], :]
                    if valid_frames.shape[0] > 1:
                        # Reshape for interpolation
                        valid_frames_t = valid_frames.T.unsqueeze(0)  # (1, features, frames)
                        decimated_frames = F.interpolate(valid_frames_t, size=64, mode='linear')[0]
                        decimated_memory[n_batch] = decimated_frames.T
        
        # Frame-level predictions
        frame_pred = self.frame_output_layer(memory)
        
        if self.mode == "tab":
            # Reshape to (batch, n_frames, 6, 21)
            frame_pred = frame_pred.reshape(batch_size, -1, N_STRINGS, 21)
            # Apply softmax per string
            frame_pred = self.softmax_by_string(frame_pred)
        
        # Note-level encoder and predictions
        note_memory = self.note_encoder(decimated_memory)
        note_pred = self.note_output_layer(note_memory)
        
        if self.mode == "tab":
            # Reshape to (batch, 64, 6, 21)
            note_pred = note_pred.reshape(batch_size, -1, N_STRINGS, 21)
            # Apply softmax per string
            note_pred = self.softmax_by_string(note_pred)
        
        return frame_pred, note_pred, olens
    
    def notelevel_decimation(self, memory: torch.Tensor, bpm: torch.Tensor) -> torch.Tensor:
        """
        Decimate frame-level embeddings to note-level using tempo-aware averaging.
        
        Algorithm:
        - Calculate frames per note based on SR, BPM, hop_length
        - For each of 64 notes, average frames covering that note's time range
        - Use weighted averaging at boundaries
        
        Args:
            memory (torch.Tensor): Frame-level embeddings (batch, n_frames, features)
            bpm (torch.Tensor): Tempo for each sample (batch,)
            
        Returns:
            torch.Tensor: Note-level embeddings (batch, 64, features)
        """
        batch_size = memory.shape[0]
        feature_size = self.encoder_output_size
        
        # Pad for boundary interpolation
        padded_memory = F.pad(memory, (0, 0, 0, 10))
        output = torch.zeros(batch_size, 64, feature_size).to(memory.device)
        
        for n_batch in range(batch_size):
            # frames_per_note = (sr * 60) / (hop_length * 4 * bpm)
            # (4 = number of beats per bar with 16th note resolution)
            frames_per_note = (self.sr * 60.0) / (self.hop_length * 4.0 * bpm[n_batch].float())
            
            # Average frames for each of 64 notes
            for n_note in range(64):
                frame_start = n_note * frames_per_note
                start_floor = int(torch.floor(frame_start))
                start_ceil = int(torch.ceil(frame_start))
                
                frame_end = (n_note + 1) * frames_per_note
                end_floor = int(torch.floor(frame_end))
                end_ceil = int(torch.ceil(frame_end))
                
                # Weighted boundary averaging
                sum_prob = padded_memory[n_batch, start_floor, :] * (start_ceil - frame_start)
                sum_prob = sum_prob + torch.sum(padded_memory[n_batch, start_ceil:end_floor, :], dim=0)
                sum_prob = sum_prob + padded_memory[n_batch, end_floor, :] * (frame_end - end_floor)
                
                # Normalize
                mean_prob = sum_prob / frames_per_note
                output[n_batch, n_note] = mean_prob
        
        return output
    
    def _get_sequence_mask(self, lengths: torch.Tensor, max_len: int,
                          device: torch.device) -> torch.Tensor:
        """Create padding mask for sequences."""
        batch_size = lengths.shape[0]
        mask = torch.arange(max_len, device=device).expand(
            batch_size, max_len
        ) >= lengths.unsqueeze(1)
        return mask


class ModelInference:
    """Inference wrapper for TabEstimator."""
    
    def __init__(self, model_path: Optional[str] = None, config: Dict = MODEL_CONFIG):
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Initialize model
        self.model = TabEstimator(config)
        self.model.to(self.device)
        self.model.eval()
        
        # Load checkpoint if provided
        if model_path and Path(model_path).exists():
            checkpoint = torch.load(model_path, map_location=self.device)
            if isinstance(checkpoint, dict) and 'model' in checkpoint:
                self.model.load_state_dict(checkpoint['model'])
            else:
                self.model.load_state_dict(checkpoint)
    
    @torch.no_grad()
    def predict(self, features: np.ndarray, tempo: float = 120.0) -> Dict:
        """
        Run inference on features.
        
        Args:
            features: (n_frames, n_bins) array
            tempo: BPM for the audio
            
        Returns:
            predictions: dict with tab and metadata
        """
        # Convert to tensor
        features_tensor = torch.from_numpy(features[np.newaxis, :, :]).float().to(self.device)
        lengths = torch.tensor([features.shape[0]], device=self.device)
        
        # Forward pass
        output, _, _ = self.model(features_tensor, lengths)
        
        if self.config['mode'] == 'tab':
            # Apply softmax and get predictions
            output = torch.softmax(output, dim=-1)  # (1, n_frames, 6, 21)
            tab_pred = torch.argmax(output, dim=-1)  # (1, n_frames, 6)
            tab_pred = tab_pred.cpu().numpy()[0]  # (n_frames, 6)
            
            # Convert to confidence scores
            confidence = torch.max(output, dim=-1)[0].cpu().numpy()[0]  # (n_frames, 6)
            
            # Post-process: remove "not played" predictions (index 20)
            tab_pred[tab_pred == NOT_PLAYED_IDX] = -1  # -1 = muted/not played
            
            return {
                "tab": tab_pred.tolist(),
                "confidence": confidence.tolist(),
                "mode": "tab",
                "n_frames": tab_pred.shape[0],
                "tempo": tempo,
            }
        else:
            # F0 mode
            output = torch.sigmoid(output)
            f0_pred = output.cpu().numpy()[0]  # (n_frames, 44)
            
            return {
                "f0": f0_pred.tolist(),
                "mode": "f0",
                "n_frames": f0_pred.shape[0],
                "tempo": tempo,
            }
    
    @torch.no_grad()
    def predict_chunk(self, features: np.ndarray, tempo: float = 120.0) -> Dict:
        """
        Run inference on a single chunk (for real-time processing).
        
        Args:
            features: (n_frames, n_bins) array - typically a short chunk
            tempo: BPM
            
        Returns:
            predictions for this chunk
        """
        return self.predict(features, tempo)


def tab_to_pitch(tab_pred: np.ndarray) -> np.ndarray:
    """
    Convert tablature predictions to MIDI pitch.
    
    Args:
        tab_pred: (n_frames, 6) with fret numbers (0-19 or -1 for not played)
        
    Returns:
        pitch: (n_frames, 6) with MIDI notes (-1 for not played)
    """
    pitch = np.zeros_like(tab_pred, dtype=np.int32)
    
    for string_idx in range(N_STRINGS):
        base_midi = GUITAR_TUNING[string_idx]
        frets = tab_pred[:, string_idx]
        
        # Convert frets to MIDI notes
        midi_notes = np.where(frets >= 0, base_midi + frets, -1)
        pitch[:, string_idx] = midi_notes
    
    return pitch


def format_tab_for_display(tab_pred: np.ndarray, chunk_size: int = 50) -> list:
    """
    Format tablature for display in chunks (for visualization).
    
    Args:
        tab_pred: (n_frames, 6) tablature
        chunk_size: frames per chunk
        
    Returns:
        list of tab chunks formatted as strings
    """
    n_frames = tab_pred.shape[0]
    string_names = ['E', 'A', 'D', 'G', 'B', 'e']
    tab_lines = [[] for _ in range(N_STRINGS)]
    
    for frame_idx in range(n_frames):
        frets = tab_pred[frame_idx]
        
        for string_idx in range(N_STRINGS):
            fret = int(frets[string_idx])
            if fret < 0:
                tab_lines[string_idx].append('-')
            else:
                tab_lines[string_idx].append(str(fret))
    
    # Format into chunks
    chunks = []
    for start in range(0, n_frames, chunk_size):
        chunk = []
        end = min(start + chunk_size, n_frames)
        
        for string_idx in range(N_STRINGS):
            line = string_names[string_idx] + '|' + ''.join(tab_lines[string_idx][start:end])
            chunk.append(line)
        
        chunks.append('\n'.join(chunk))
    
    return chunks


def tab_to_pianoroll(tab_pred: np.ndarray, n_pitches: int = 88) -> np.ndarray:
    """
    Convert tablature predictions to pianoroll representation.
    
    Pianoroll is a 2D array where:
    - X-axis: time frames
    - Y-axis: MIDI pitch numbers
    
    Args:
        tab_pred: (n_frames, 6) with fret numbers (0-19 or -1 for not played)
        n_pitches: number of pitch classes to include
        
    Returns:
        pianoroll: (n_pitches, n_frames) binary activation map
    """
    n_frames = tab_pred.shape[0]
    pianoroll = np.zeros((n_pitches, n_frames), dtype=np.float32)
    midi_pitches = tab_to_pitch(tab_pred)
    
    for frame_idx in range(n_frames):
        for string_idx in range(N_STRINGS):
            midi_note = int(midi_pitches[frame_idx, string_idx])
            if midi_note >= 0 and midi_note < n_pitches:
                pianoroll[midi_note, frame_idx] = 1.0
    
    return pianoroll


def format_pianoroll_for_display(tab_pred: np.ndarray, hop_length: int = 512, 
                                 sr: int = 22050) -> Dict:
    """
    Format pianoroll data for frontend visualization (note blocks).
    
    Args:
        tab_pred: (n_frames, 6) tablature
        hop_length: samples per frame
        sr: sample rate
        
    Returns:
        pianoroll_data: dict with notes and timing info
    """
    midi_pitches = tab_to_pitch(tab_pred)
    n_frames = tab_pred.shape[0]
    notes = []
    
    for string_idx in range(N_STRINGS):
        frets = tab_pred[:, string_idx]
        midi_vals = midi_pitches[:, string_idx]
        current_fret = None
        note_start = 0
        
        for frame_idx in range(n_frames):
            fret = frets[frame_idx]
            
            if fret >= 0:
                if current_fret != fret:
                    if current_fret is not None:
                        duration_sec = ((frame_idx - note_start) * hop_length) / sr
                        notes.append({
                            "midi": int(midi_vals[note_start]),
                            "string": string_idx,
                            "fret": int(current_fret),
                            "start_time": (note_start * hop_length) / sr,
                            "duration": duration_sec,
                        })
                    current_fret = fret
                    note_start = frame_idx
            else:
                if current_fret is not None:
                    duration_sec = ((frame_idx - note_start) * hop_length) / sr
                    notes.append({
                        "midi": int(midi_vals[note_start]),
                        "string": string_idx,
                        "fret": int(current_fret),
                        "start_time": (note_start * hop_length) / sr,
                        "duration": duration_sec,
                    })
                    current_fret = None
        
        if current_fret is not None:
            duration_sec = ((n_frames - note_start) * hop_length) / sr
            notes.append({
                "midi": int(midi_vals[note_start]),
                "string": string_idx,
                "fret": int(current_fret),
                "start_time": (note_start * hop_length) / sr,
                "duration": duration_sec,
            })
    
    return {"notes": notes, "total_duration": (n_frames * hop_length) / sr}
