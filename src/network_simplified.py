"""
TAB Estimator Model with Frame, Onset, and Note Detection
- Conformer encoder
- Optional ConvStack (Conv2D -> BatchNorm -> MaxPool x2)
- Three branches: Frame, Onset, Note (each with BiLSTM + GRU)
- TAB mode only (6 strings x 21 frets)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math


class GuidedAttentionLoss(nn.Module):
    """Guided attention loss (alpha=1.0, sigma=0.4) to encourage diagonal attention patterns."""
    
    def __init__(self, sigma=0.4, alpha=1.0):
        super().__init__()
        self.sigma = sigma
        self.alpha = alpha
    
    def forward(self, attention_weights, input_lengths, output_lengths):
        """
        Args:
            attention_weights: (B, heads, T_out, T_in) or (B, T_out, T_in)
            input_lengths: (B,)
            output_lengths: (B,)
        Returns:
            loss: scalar
        """
        # Handle both 3D and 4D attention weights
        if attention_weights.dim() == 4:
            # Average over heads: (B, heads, T_out, T_in) → (B, T_out, T_in)
            attention_weights = attention_weights.mean(dim=1)
        
        batch_size = attention_weights.shape[0]
        max_ilen = min(input_lengths.max().item(), attention_weights.shape[2])
        max_olen = min(output_lengths.max().item(), attention_weights.shape[1])
        
        # Create guided attention mask (penalize off-diagonal)
        guided_mask = torch.zeros(batch_size, max_olen, max_ilen, 
                                 device=attention_weights.device)
        
        for b in range(batch_size):
            ilen = min(input_lengths[b].item(), max_ilen)
            olen = min(output_lengths[b].item(), max_olen)
            
            for i in range(olen):
                for j in range(ilen):
                    # Diagonal penalty: attention should be concentrated on diagonal
                    ratio_i = i / max(olen, 1)
                    ratio_j = j / max(ilen, 1)
                    guided_mask[b, i, j] = 1.0 - torch.exp(
                        -((ratio_j - ratio_i) ** 2) / (2 * self.sigma ** 2)
                    )
        
        # Truncate attention weights to match mask
        attn_truncated = attention_weights[:, :max_olen, :max_ilen]
        
        # Apply mask and compute loss
        loss = (guided_mask * attn_truncated).mean()
        return self.alpha * loss


class TabLoss(nn.Module):
    """Combined loss for three branches: Frame, Onset, Note."""
    
    def __init__(self):
        super().__init__()
        self.guided_attention_loss = GuidedAttentionLoss(sigma=0.4, alpha=1.0)
        self.bce_loss = nn.BCELoss(reduction='mean')
    
    def forward(self, frame_pred, frame_gt, onset_pred, onset_gt, note_pred, note_gt, 
                attn_weights=None, input_lengths=None, output_lengths=None):
        """
        Args:
            frame_pred: (B, T_frame, 6, 21) frame predictions
            frame_gt: (B, T_frame, 6, 21) frame ground truth
            onset_pred: (B, T_frame, 6, 21) onset predictions
            onset_gt: (B, T_frame, 6, 21) onset ground truth
            note_pred: (B, T_note, 6, 21) note predictions
            note_gt: (B, T_note, 6, 21) note ground truth
            attn_weights: (B, heads, T, T) attention weights (optional)
            input_lengths: (B,) input sequence lengths
            output_lengths: (B,) output sequence lengths
        Returns:
            loss: scalar
        """
        # Frame loss - BCE normalized by 126 (6 strings × 21 frets)
        frame_loss = self.bce_loss(frame_pred, frame_gt)
        frame_loss = frame_loss / 126.0
        
        # Onset loss - BCE with mean reduction
        onset_loss = self.bce_loss(onset_pred, onset_gt)
        
        # Note loss - BCE with mean reduction
        note_loss = self.bce_loss(note_pred, note_gt)
        
        # Guided attention loss (penalize off-diagonal)
        attn_loss = 0
        if attn_weights is not None and input_lengths is not None and output_lengths is not None:
            attn_loss = self.guided_attention_loss(attn_weights, input_lengths, output_lengths)
        
        # Total loss
        total_loss = frame_loss + onset_loss + note_loss + attn_loss
        
        return total_loss


class ConvStack(nn.Module):
    """Conv2D -> BatchNorm -> MaxPool stack for feature extraction."""
    
    def __init__(self, input_freq_bins, output_dim):
        super().__init__()
        
        self.conv_block = nn.Sequential(
            # Conv2D layer: (B, 1, freq_bins, time_steps)
            nn.Conv2d(1, 32, kernel_size=(3, 3), padding=(1, 1)),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            
            # MaxPool (1, 2): reduce time dimension
            nn.MaxPool2d((1, 2)),
            nn.Dropout(0.25),
            
            # Conv2D layer
            nn.Conv2d(32, 64, kernel_size=(3, 3), padding=(1, 1)),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            
            # MaxPool (1, 2): reduce time dimension more
            nn.MaxPool2d((1, 2)),
            nn.Dropout(0.25),
        )
        
        # After 2 MaxPool2d with (1, 2), time dimension is reduced by 4x
        # Freq dimension stays the same due to padding
        self.fc = nn.Sequential(
            nn.Linear(64 * input_freq_bins, output_dim),
            nn.Dropout(0.5)
        )
    
    def forward(self, x):
        """
        Args:
            x: (B, T, freq_bins) input spectrogram
        Returns:
            y: (B, T//4, output_dim) processed features
        """
        # x: (B, T, freq_bins)
        x = x.unsqueeze(1)  # (B, 1, T, freq_bins)
        x = x.transpose(2, 3)  # (B, 1, freq_bins, T)
        
        x = self.conv_block(x)  # (B, 64, freq_bins, T//4)
        
        # Reshape for FC layer
        B, C, F, T = x.shape
        x = x.transpose(2, 3)  # (B, 64, T//4, freq_bins)
        x = x.reshape(B, T, -1)  # (B, T//4, 64*freq_bins)
        
        x = self.fc(x)  # (B, T//4, output_dim)
        return x


class PositionalEncoding(nn.Module):
    """Positional encoding for Transformer/Conformer."""
    
    def __init__(self, d_model, max_len=5000):
        super().__init__()
        
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * 
                            (-math.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        if d_model % 2 == 1:
            pe[:, 1::2] = torch.cos(position * div_term[:-1])
        else:
            pe[:, 1::2] = torch.cos(position * div_term)
        
        self.register_buffer('pe', pe)
    
    def forward(self, x):
        """
        Args:
            x: (B, T, d_model)
        Returns:
            x + positional encoding: (B, T, d_model)
        """
        return x + self.pe[:x.size(1)].unsqueeze(0)


class ConformerBlock(nn.Module):
    """Simplified Conformer block with self-attention and feed-forward networks."""
    
    def __init__(self, d_model, num_heads, d_ff, kernel_size=3, dropout=0.1):
        super().__init__()
        
        # Layer normalization
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.norm3 = nn.LayerNorm(d_model)
        
        # Multi-head self-attention
        self.mha = nn.MultiheadAttention(d_model, num_heads, dropout=dropout, batch_first=True)
        
        # Conv module (Conformer-specific)
        self.conv = nn.Sequential(
            nn.Conv1d(d_model, d_model, kernel_size, padding=kernel_size//2, groups=1),
            nn.BatchNorm1d(d_model),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
        # Feed-forward networks
        self.ff1 = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout)
        )
        
        self.ff2 = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout)
        )
    
    def forward(self, x, attention_mask=None):
        """
        Args:
            x: (B, T, d_model)
            attention_mask: (B, 1, 1, T) or None
        Returns:
            output: (B, T, d_model)
            attention_weights: (B, num_heads, T, T)
        """
        # Self-attention block
        x_norm = self.norm1(x)
        attn_out, attn_weights = self.mha(x_norm, x_norm, x_norm, 
                                          attn_mask=attention_mask, 
                                          average_attn_weights=False)
        x = x + attn_out
        
        # Conv block
        x_norm = self.norm2(x)
        x_t = x_norm.transpose(1, 2)  # (B, d_model, T)
        conv_out = self.conv(x_t)
        x = x + conv_out.transpose(1, 2)
        
        # Feed-forward block
        x_norm = self.norm3(x)
        ff_out = self.ff2(self.ff1(x_norm))
        x = x + ff_out
        
        return x, attn_weights


class ConformerEncoder(nn.Module):
    """Simplified Conformer encoder stack."""
    
    def __init__(self, input_dim, d_model, num_heads, d_ff, num_layers, 
                 kernel_size=3, dropout=0.1):
        super().__init__()
        
        # Input projection
        self.input_proj = nn.Linear(input_dim, d_model)
        
        # Positional encoding
        self.pos_encoding = PositionalEncoding(d_model)
        
        # Conformer blocks
        self.blocks = nn.ModuleList([
            ConformerBlock(d_model, num_heads, d_ff, kernel_size, dropout)
            for _ in range(num_layers)
        ])
        
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x, lengths=None):
        """
        Args:
            x: (B, T, input_dim)
            lengths: (B,) sequence lengths
        Returns:
            output: (B, T, d_model)
            attention_weights_all: list of (B, num_heads, T, T)
        """
        # Project input
        x = self.input_proj(x)
        x = self.pos_encoding(x)
        x = self.dropout(x)
        
        # Create attention mask if lengths provided
        attention_mask = None
        if lengths is not None:
            max_len = x.shape[1]
            attention_mask = torch.arange(max_len, device=x.device).unsqueeze(0) >= lengths.unsqueeze(1)
            attention_mask = attention_mask.unsqueeze(1).unsqueeze(1)
        
        # Apply Conformer blocks
        attention_weights_all = []
        for block in self.blocks:
            x, attn_weights = block(x, attention_mask)
            attention_weights_all.append(attn_weights)
        
        return x, attention_weights_all


class SimpleTabEstimator(nn.Module):
    """
    TAB Estimator with three branches:
    - Frame branch: BiLSTM + GRU
    - Onset branch: BiLSTM + GRU
    - Note branch: Note Encoder + BiLSTM + GRU
    """
    
    def __init__(self, config):
        super().__init__()
        
        self.config = config
        self.d_model = config['d_model']
        self.n_strings = config['n_strings']
        self.n_frets = config['n_frets']
        self.use_conv_stack = config['use_conv_stack']
        
        input_dim = config['cqt_n_bins']
        
        # Optional ConvStack
        if self.use_conv_stack:
            self.conv_stack = ConvStack(input_dim, self.d_model)
            encoder_input_dim = self.d_model
        else:
            encoder_input_dim = input_dim
        
        # Conformer encoder
        self.encoder = ConformerEncoder(
            input_dim=encoder_input_dim,
            d_model=self.d_model,
            num_heads=config['encoder_heads'],
            d_ff=self.d_model * 4,
            num_layers=config['encoder_layers'],
            kernel_size=3,
            dropout=0.1
        )
        
        # ===== FRAME BRANCH =====
        self.frame_dense = nn.Linear(self.d_model, self.n_strings * self.n_frets)
        self.frame_bilstm = nn.LSTM(
            input_size=self.n_strings * self.n_frets,
            hidden_size=256,
            num_layers=1,
            batch_first=True,
            bidirectional=True,
            dropout=0.5
        )
        self.frame_gru = nn.GRU(
            input_size=512,  # 256 * 2 (bidirectional)
            hidden_size=256,
            num_layers=1,
            batch_first=True,
            dropout=0.5
        )
        self.frame_head = nn.Sequential(
            nn.Linear(256, self.n_strings * self.n_frets),
            nn.Sigmoid()
        )
        
        # ===== ONSET BRANCH =====
        self.onset_dense = nn.Linear(self.d_model, self.n_strings * self.n_frets)
        self.onset_bilstm = nn.LSTM(
            input_size=self.n_strings * self.n_frets,
            hidden_size=256,
            num_layers=1,
            batch_first=True,
            bidirectional=True,
            dropout=0.5
        )
        self.onset_gru = nn.GRU(
            input_size=512,  # 256 * 2 (bidirectional)
            hidden_size=256,
            num_layers=1,
            batch_first=True,
            dropout=0.5
        )
        self.onset_head = nn.Sequential(
            nn.Linear(256, self.n_strings * self.n_frets),
            nn.Sigmoid()
        )
        
        # ===== NOTE BRANCH =====
        # Note encoder: decimation layer to ~120 notes
        self.note_encoder = ConformerEncoder(
            input_dim=self.d_model,
            d_model=self.d_model,
            num_heads=config['encoder_heads'],
            d_ff=self.d_model * 4,
            num_layers=config['encoder_layers'],
            kernel_size=3,
            dropout=0.1
        )
        
        self.note_dense = nn.Linear(self.d_model, self.n_strings * self.n_frets)
        self.note_bilstm = nn.LSTM(
            input_size=self.n_strings * self.n_frets,
            hidden_size=256,
            num_layers=1,
            batch_first=True,
            bidirectional=True,
            dropout=0.5
        )
        self.note_gru = nn.GRU(
            input_size=512,  # 256 * 2 (bidirectional)
            hidden_size=256,
            num_layers=1,
            batch_first=True,
            dropout=0.5
        )
        self.note_head = nn.Sequential(
            nn.Linear(256, self.n_strings * self.n_frets),
            nn.Sigmoid()
        )
    
    def forward(self, x, lengths=None, bpm=None):
        """
        Args:
            x: (B, T, n_bins) CQT spectrogram
            lengths: (B,) sequence lengths
            bpm: (B,) BPM values for BPM-based decimation
        Returns:
            frame_pred: (B, T, 6, 21)
            onset_pred: (B, T, 6, 21)
            note_pred: (B, T_note, 6, 21)
            attn_weights: attention weight tensor
        """
        batch_size = x.shape[0]
        
        # Apply ConvStack if enabled
        if self.use_conv_stack:
            x = self.conv_stack(x)
        
        # Conformer encoder
        encoder_out, attention_weights = self.encoder(x, lengths)
        frame_len = encoder_out.shape[1]
        
        # Get attention weights for loss (average over heads)
        attn_for_loss = attention_weights[0] if attention_weights else None
        
        # ===== FRAME BRANCH =====
        frame_logits = self.frame_dense(encoder_out)  # (B, T, 126)
        frame_lstm_out, _ = self.frame_bilstm(frame_logits)  # (B, T, 512)
        frame_gru_out, _ = self.frame_gru(frame_lstm_out)  # (B, T, 256)
        frame_out = self.frame_head(frame_gru_out)  # (B, T, 126)
        frame_pred = frame_out.view(batch_size, -1, self.n_strings, self.n_frets)
        
        # ===== ONSET BRANCH =====
        onset_logits = self.onset_dense(encoder_out)  # (B, T, 126)
        onset_lstm_out, _ = self.onset_bilstm(onset_logits)  # (B, T, 512)
        onset_gru_out, _ = self.onset_gru(onset_lstm_out)  # (B, T, 256)
        onset_out = self.onset_head(onset_gru_out)  # (B, T, 126)
        onset_pred = onset_out.view(batch_size, -1, self.n_strings, self.n_frets)
        
        # ===== NOTE BRANCH =====
        # BPM-based decimation with linear interpolation
        if bpm is not None:
            encoder_out_decimated = self.notelevel_decimation_bpm(encoder_out, bpm)
        else:
            # Fallback: simple average pooling to ~120 notes
            decimation_factor = max(1, frame_len // 120)
            
            if decimation_factor > 1:
                pad_len = (decimation_factor - frame_len % decimation_factor) % decimation_factor
                if pad_len > 0:
                    encoder_out_padded = F.pad(encoder_out, (0, 0, 0, pad_len))
                else:
                    encoder_out_padded = encoder_out
                
                B, T_padded, D = encoder_out_padded.shape
                encoder_out_decimated = encoder_out_padded.view(B, -1, decimation_factor, D).mean(dim=2)
            else:
                encoder_out_decimated = encoder_out
        
        # Note encoder
        note_encoder_out, _ = self.note_encoder(encoder_out_decimated, None)
        
        note_logits = self.note_dense(note_encoder_out)  # (B, T_note, 126)
        note_lstm_out, _ = self.note_bilstm(note_logits)  # (B, T_note, 512)
        note_gru_out, _ = self.note_gru(note_lstm_out)  # (B, T_note, 256)
        note_out = self.note_head(note_gru_out)  # (B, T_note, 126)
        note_pred = note_out.view(encoder_out_decimated.shape[0], -1, self.n_strings, self.n_frets)
        
        return frame_pred, onset_pred, note_pred, attn_for_loss
    
    def notelevel_decimation_bpm(self, memory, bpm, n_notes=64, sr=22050, hop_length=512):
        """
        BPM-based decimation using linear interpolation.
        Based on reference implementation from original codebase.
        
        Args:
            memory: (B, T, features) encoder output
            bpm: (B,) BPM values
            n_notes: number of note positions (default 64)
            sr: sample rate (default 22050)
            hop_length: hop length in samples (default 512)
        
        Returns:
            output: (B, n_notes, features) decimated features with linear interpolation
        """
        # memory: (batch, len, features)
        padded_memory = F.pad(memory, (0, 0, 0, 10))  # for margin of error
        batch_size = memory.shape[0]
        feature_size = memory.shape[2]
        output = torch.zeros(batch_size, n_notes, feature_size).to(memory.device)

        for n_batch in range(batch_size):
            frames_per_note = ((sr * 60) / (hop_length * 4 * bpm[n_batch])).float()
            
            for n_note in range(n_notes):
                frame_start = n_note * frames_per_note
                start_floor = torch.floor(frame_start).int().item()
                start_ceil = torch.ceil(frame_start).int().item()
                
                frame_end = (n_note + 1) * frames_per_note
                end_floor = torch.floor(frame_end).int().item()
                end_ceil = torch.ceil(frame_end).int().item()

                # Linear interpolation at start position
                sum_prob = padded_memory[n_batch, start_floor, :] * (start_ceil - frame_start)
                
                # Sum all complete frames in between
                if end_floor > start_ceil:
                    sum_prob = sum_prob + torch.sum(
                        padded_memory[n_batch, start_ceil:end_floor, :], dim=0)
                
                # Linear interpolation at end position
                sum_prob = sum_prob + padded_memory[n_batch, end_floor, :] * (frame_end - end_floor)
                
                # Average by note duration
                mean_prob = sum_prob / frames_per_note
                output[n_batch, n_note] = mean_prob

        return output
