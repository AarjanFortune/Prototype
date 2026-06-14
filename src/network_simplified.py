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
    """Guided attention loss (alpha=1.0, sigma=0.4) optimized to run completely vectorized on the GPU."""
    
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
        if attention_weights.dim() == 4:
            attention_weights = attention_weights.mean(dim=1)
        
        device = attention_weights.device
        batch_size = attention_weights.shape[0]
        
        # Explicitly protect against device mismatches from CPU DataLoader inputs
        input_lengths = input_lengths.to(device)
        output_lengths = output_lengths.to(device)
        
        max_ilen = min(input_lengths.max().item(), attention_weights.shape[2])
        max_olen = min(output_lengths.max().item(), attention_weights.shape[1])
        
        # Create vectorized coordinate grids
        i_indices = torch.arange(max_olen, device=device).view(1, max_olen, 1).float()
        j_indices = torch.arange(max_ilen, device=device).view(1, 1, max_ilen).float()
        
        # Reshape lengths for broadcasting
        ilen_b = torch.clamp(input_lengths, max=max_ilen).view(batch_size, 1, 1).float()
        olen_b = torch.clamp(output_lengths, max=max_olen).view(batch_size, 1, 1).float()
        
        # Avoid division by zero
        ilen_b_div = torch.clamp(ilen_b, min=1.0)
        olen_b_div = torch.clamp(olen_b, min=1.0)
        
        ratio_i = i_indices / olen_b_div
        ratio_j = j_indices / ilen_b_div
        
        # Calculate full exponential mask matrix in parallel
        guided_mask = 1.0 - torch.exp(-((ratio_j - ratio_i) ** 2) / (2 * self.sigma ** 2))
        
        # Mask out elements that exceed the true sequence lengths for each batch item
        mask_i = torch.arange(max_olen, device=device).view(1, max_olen, 1) < olen_b.long()
        mask_j = torch.arange(max_ilen, device=device).view(1, 1, max_ilen) < ilen_b.long()
        valid_mask = mask_i & mask_j
        
        guided_mask = torch.where(valid_mask, guided_mask, torch.zeros_like(guided_mask))
        
        attn_truncated = attention_weights[:, :max_olen, :max_ilen]
        loss = (guided_mask * attn_truncated).mean()
        return self.alpha * loss


class TabLoss(nn.Module):
    """Combined loss for three branches: Frame, Onset, Note using BCEWithLogitsLoss."""
    
    def __init__(self):
        super().__init__()
        self.guided_attention_loss = GuidedAttentionLoss(sigma=0.4, alpha=1.0)
        self.bce_loss = nn.BCEWithLogitsLoss(reduction='mean')

    @staticmethod
    def _match_time_axis(target, target_len):
        """Resize labels along time when ConvStack changes frame resolution."""
        if target.shape[1] == target_len:
            return target

        bsz, _, n_strings, n_frets = target.shape
        target = target.permute(0, 2, 3, 1).reshape(bsz, n_strings * n_frets, -1)
        target = F.interpolate(target, size=target_len, mode='nearest')
        return target.reshape(bsz, n_strings, n_frets, target_len).permute(0, 3, 1, 2)
    
    def forward(self, frame_pred, frame_gt, onset_pred, onset_gt, note_pred, note_gt, 
                attn_weights=None, input_lengths=None, output_lengths=None):
        """
        Args:
            frame_pred: (B, T_frame, 6, 21) raw frame logits
            frame_gt: (B, T_frame, 6, 21) frame ground truth
            onset_pred: (B, T_frame, 6, 21) raw onset logits
            onset_gt: (B, T_frame, 6, 21) onset ground truth
            note_pred: (B, T_note, 6, 21) raw note logits
            note_gt: (B, T_note, 6, 21) note ground truth
            attn_weights: (B, heads, T, T) attention weights (optional)
            input_lengths: (B,) input sequence lengths
            output_lengths: (B,) output sequence lengths
        Returns:
            loss: scalar
        """
        frame_gt = self._match_time_axis(frame_gt, frame_pred.shape[1])
        onset_gt = self._match_time_axis(onset_gt, onset_pred.shape[1])
        note_gt = self._match_time_axis(note_gt, note_pred.shape[1])

        frame_loss = self.bce_loss(frame_pred, frame_gt)
        frame_loss = frame_loss / 126.0
        
        onset_loss = self.bce_loss(onset_pred, onset_gt)
        note_loss = self.bce_loss(note_pred, note_gt)
        
        attn_loss = 0
        if attn_weights is not None and input_lengths is not None and output_lengths is not None:
            attn_loss = self.guided_attention_loss(attn_weights, input_lengths, output_lengths)
        
        total_loss = frame_loss + onset_loss + note_loss + attn_loss
        return total_loss


class ConvStack(nn.Module):
    """Conv2D -> BatchNorm -> MaxPool stack for feature extraction."""
    
    def __init__(self, input_freq_bins, output_dim):
        super().__init__()
        
        self.conv_block = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=(3, 3), padding=(1, 1)),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d((1, 2)),
            nn.Dropout(0.25),
            
            nn.Conv2d(32, 64, kernel_size=(3, 3), padding=(1, 1)),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d((1, 2)),
            nn.Dropout(0.25),
        )
        
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
        x = x.unsqueeze(1)
        x = x.transpose(2, 3)
        
        x = self.conv_block(x)
        
        B, C, F, T = x.shape
        x = x.transpose(2, 3)
        x = x.reshape(B, T, -1)
        
        x = self.fc(x)
        return x


class PositionalEncoding(nn.Module):
    """Positional encoding for Transformer/Conformer."""
    
    def __init__(self, d_model, max_len=5000):
        super().__init__()
        
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        
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
        
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.norm3 = nn.LayerNorm(d_model)
        
        self.mha = nn.MultiheadAttention(d_model, num_heads, dropout=dropout, batch_first=True)
        
        self.conv = nn.Sequential(
            nn.Conv1d(d_model, d_model, kernel_size, padding=kernel_size//2, groups=1),
            nn.BatchNorm1d(d_model),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
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
    
    def forward(self, x, key_padding_mask=None):
        """
        Args:
            x: (B, T, d_model)
            key_padding_mask: (B, T) boolean mask or None
        Returns:
            output: (B, T, d_model)
            attention_weights: (B, num_heads, T, T)
        """
        x_norm = self.norm1(x)
        attn_out, attn_weights = self.mha(x_norm, x_norm, x_norm, 
                                          key_padding_mask=key_padding_mask,
                                          average_attn_weights=False)
        x = x + attn_out
        
        x_norm = self.norm2(x)
        x_t = x_norm.transpose(1, 2)
        conv_out = self.conv(x_t)
        x = x + conv_out.transpose(1, 2)
        
        x_norm = self.norm3(x)
        ff_out = self.ff2(self.ff1(x_norm))
        x = x + ff_out
        
        return x, attn_weights


class ConformerEncoder(nn.Module):
    """Simplified Conformer encoder stack."""
    
    def __init__(self, input_dim, d_model, num_heads, d_ff, num_layers, 
                 kernel_size=3, dropout=0.1):
        super().__init__()
        
        self.input_proj = nn.Linear(input_dim, d_model)
        self.pos_encoding = PositionalEncoding(d_model)
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
        x = self.input_proj(x)
        x = self.pos_encoding(x)
        x = self.dropout(x)
        
        key_padding_mask = None
        if lengths is not None:
            max_len = x.shape[1]
            key_padding_mask = torch.arange(max_len, device=x.device).unsqueeze(0) >= lengths.unsqueeze(1)
        
        attention_weights_all = []
        for block in self.blocks:
            x, attn_weights = block(x, key_padding_mask)
            attention_weights_all.append(attn_weights)
        
        return x, attention_weights_all


class SimpleTabEstimator(nn.Module):
    """
    TAB Estimator with three branches using BCEWithLogitsLoss configuration (no internal Sigmoid).
    """
    
    def __init__(self, config):
        super().__init__()
        
        self.config = config
        self.d_model = config['d_model']
        self.n_strings = config['n_strings']
        self.n_frets = config['n_frets']
        self.use_conv_stack = config['use_conv_stack']
        
        input_dim = config['cqt_n_bins']
        
        if self.use_conv_stack:
            self.conv_stack = ConvStack(input_dim, self.d_model)
            encoder_input_dim = self.d_model
        else:
            encoder_input_dim = input_dim
        
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
            input_size=512,
            hidden_size=256,
            num_layers=1,
            batch_first=True,
            dropout=0.5
        )
        self.frame_head = nn.Linear(256, self.n_strings * self.n_frets)
        
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
            input_size=512,
            hidden_size=256,
            num_layers=1,
            batch_first=True,
            dropout=0.5
        )
        self.onset_head = nn.Linear(256, self.n_strings * self.n_frets)
        
        # ===== NOTE BRANCH =====
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
            input_size=512,
            hidden_size=256,
            num_layers=1,
            batch_first=True,
            dropout=0.5
        )
        self.note_head = nn.Linear(256, self.n_strings * self.n_frets)
    
    def forward(self, x, lengths=None, bpm=None):
        """
        Args:
            x: (B, T, n_bins) CQT spectrogram
            lengths: (B,) sequence lengths
            bpm: (B,) BPM values for BPM-based decimation
        Returns:
            frame_pred: (B, T, 6, 21) raw logit tensors
            onset_pred: (B, T, 6, 21) raw logit tensors
            note_pred: (B, T_note, 6, 21) raw logit tensors
            attn_weights: attention weight tensor
        """
        batch_size = x.shape[0]
        
        if self.use_conv_stack:
            x = self.conv_stack(x)
            if lengths is not None:
                lengths = torch.clamp((lengths.float() / 4).ceil().long(), min=1, max=x.shape[1])
        
        encoder_out, attention_weights = self.encoder(x, lengths)
        frame_len = encoder_out.shape[1]
        
        attn_for_loss = attention_weights[0] if attention_weights else None
        
        # ===== FRAME BRANCH =====
        frame_logits = self.frame_dense(encoder_out)
        frame_lstm_out, _ = self.frame_bilstm(frame_logits)
        frame_gru_out, _ = self.frame_gru(frame_lstm_out)
        frame_out = self.frame_head(frame_gru_out)
        frame_pred = frame_out.view(batch_size, -1, self.n_strings, self.n_frets)
        
        # ===== ONSET BRANCH =====
        onset_logits = self.onset_dense(encoder_out)
        onset_lstm_out, _ = self.onset_bilstm(onset_logits)
        onset_gru_out, _ = self.onset_gru(onset_lstm_out)
        onset_out = self.onset_head(onset_gru_out)
        onset_pred = onset_out.view(batch_size, -1, self.n_strings, self.n_frets)
        
        # ===== NOTE BRANCH =====
        if bpm is not None:
            encoder_out_decimated = self.notelevel_decimation_bpm(encoder_out, bpm)
        else:
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
        
        note_encoder_out, _ = self.note_encoder(encoder_out_decimated, None)
        
        note_logits = self.note_dense(note_encoder_out)
        note_lstm_out, _ = self.note_bilstm(note_logits)
        note_gru_out, _ = self.note_gru(note_lstm_out)
        note_head_out = self.note_head(note_gru_out)
        note_pred = note_head_out.view(encoder_out_decimated.shape[0], -1, self.n_strings, self.n_frets)
        
        return frame_pred, onset_pred, note_pred, attn_for_loss
    
    def notelevel_decimation_bpm(self, memory, bpm, n_notes=64, sr=22050, hop_length=512):
        """
        BPM-based decimation using a fully vectorized piece-wise linear cumulative sum integral.
        Forces external inputs to target GPU device to fix pipeline device mismatches.
        """
        device = memory.device
        padded_memory = F.pad(memory, (0, 0, 0, 10))
        batch_size = memory.shape[0]
        feature_size = memory.shape[2]
        
        # Safely force external bpm inputs onto the current GPU execution context
        bpm = bpm.to(device)
        
        # Prepends a 0 tensor on the time dimension to calculate seamless continuous integrals
        zero_pad = torch.zeros(batch_size, 1, feature_size, device=device, dtype=memory.dtype)
        cumsum_input = torch.cat([zero_pad, padded_memory], dim=1)
        S = torch.cumsum(cumsum_input, dim=1)
        
        # Vectorized generation of note steps directly on GPU device
        frames_per_note = ((sr * 60) / (hop_length * 4 * bpm)).float().view(batch_size, 1)
        note_indices = torch.arange(n_notes, device=device).float().view(1, n_notes)
        
        frame_start = note_indices * frames_per_note     # (B, n_notes)
        frame_end = (note_indices + 1) * frames_per_note # (B, n_notes)
        
        max_idx = padded_memory.shape[1] - 1
        batch_indices = torch.arange(batch_size, device=device).view(batch_size, 1).expand(batch_size, n_notes)

        # Helper function to compute continuous integration from cumulative sums
        def evaluate_integral(t):
            k = torch.floor(t).long()
            k_clamped = torch.clamp(k, min=0, max=max_idx)
            
            S_k = S[batch_indices, k_clamped]
            x_k = padded_memory[batch_indices, k_clamped]
            
            dt = (t - k_clamped).unsqueeze(-1)
            return S_k + dt * x_k

        I_start = evaluate_integral(frame_start)
        I_end = evaluate_integral(frame_end)
        
        sum_prob = I_end - I_start
        mean_prob = sum_prob / frames_per_note.unsqueeze(-1)
        
        return mean_prob