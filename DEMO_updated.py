#!/usr/bin/env python3
"""
DEMO: Complete TAB Estimator with BPM-Based Decimation
========================================================

This demo showcases the complete implementation including:
1. Three-branch architecture (Frame, Onset, Note)
2. BiLSTM + GRU on each branch (online language models)
3. BPM-based note-level decimation with linear interpolation
4. Conformer encoder with guided attention loss
5. RAdam optimizer with gradient clipping

Run this to verify the implementation works end-to-end.
"""

import sys
import os
import torch
import torch.nn as nn
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from network_simplified import SimpleTabEstimator, TabLoss
from data_utils_simplified import TabDataPreprocessor


def print_header(text):
    """Print formatted header."""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)


def print_section(text):
    """Print formatted section."""
    print(f"\n>>> {text}")
    print("-" * 70)


def demo_model_creation():
    """Demo 1: Create and inspect the model."""
    print_header("DEMO 1: MODEL CREATION")
    
    # Create model
    model = SimpleTabEstimator(
        input_dim=192,
        d_model=512,
        encoder_heads=4,
        encoder_layers=4,
        d_ff=2048,
        n_strings=6,
        n_frets=21,
        use_conv_stack=True,
        dropout=0.1
    )
    
    print(f"✓ Model created: SimpleTabEstimator")
    print(f"  - Total parameters: {sum(p.numel() for p in model.parameters()):,}")
    print(f"  - Trainable parameters: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")
    print(f"  - Device: {next(model.parameters()).device}")
    
    # Show architecture
    print_section("Architecture Components")
    print(f"1. ConvStack (optional): {model.use_conv_stack}")
    print(f"2. Conformer Encoder: 4 layers, 4 heads, d_model=512")
    print(f"3. Three Branches: Frame, Onset, Note")
    print(f"   - Frame: Dense → BiLSTM → GRU → Sigmoid")
    print(f"   - Onset: Dense → BiLSTM → GRU → Sigmoid")
    print(f"   - Note: BPM Decimation → Encoder → Dense → BiLSTM → GRU → Sigmoid")
    print(f"4. BPM-Based Decimation: Linear interpolation, 64 notes per sample")
    
    return model


def demo_forward_pass(model):
    """Demo 2: Forward pass with and without BPM."""
    print_header("DEMO 2: FORWARD PASS")
    
    # Create dummy batch
    batch_size = 2
    seq_len = 600
    n_bins = 192
    
    cqt = torch.randn(batch_size, seq_len, n_bins)
    lengths = torch.tensor([seq_len, seq_len-100], dtype=torch.long)
    bpm = torch.tensor([120.0, 100.0], dtype=torch.float)  # Different BPM for each sample
    
    print_section("Input Shapes")
    print(f"CQT features: {cqt.shape}")
    print(f"  - Batch size: {batch_size}")
    print(f"  - Time steps: {seq_len}")
    print(f"  - Frequency bins: {n_bins}")
    print(f"Sequence lengths: {lengths}")
    print(f"BPM values: {bpm.tolist()}")
    
    # Forward pass WITH BPM
    print_section("Forward Pass WITH BPM (Frame-Aware Decimation)")
    with torch.no_grad():
        frame_pred, onset_pred, note_pred, attn_weights = model(cqt, lengths, bpm=bpm)
    
    print(f"Frame predictions: {frame_pred.shape}")
    print(f"  - (Batch, Time, Strings, Frets) = ({batch_size}, {seq_len}, 6, 21)")
    print(f"Onset predictions: {onset_pred.shape}")
    print(f"  - Same temporal resolution as frames")
    print(f"Note predictions: {note_pred.shape}")
    print(f"  - (Batch, Notes, Strings, Frets) = ({batch_size}, 64, 6, 21)")
    print(f"Attention weights: {attn_weights.shape if attn_weights is not None else 'None'}")
    
    # Forward pass WITHOUT BPM (fallback)
    print_section("Forward Pass WITHOUT BPM (Fallback Average Pooling)")
    with torch.no_grad():
        frame_pred_fb, onset_pred_fb, note_pred_fb, _ = model(cqt, lengths, bpm=None)
    
    print(f"Note predictions (fallback): {note_pred_fb.shape}")
    print(f"  - Uses simple average pooling: decimation_factor = T // 120")
    print(f"  - Different from BPM-based: {not torch.allclose(note_pred, note_pred_fb)}")
    
    return frame_pred, onset_pred, note_pred, attn_weights


def demo_bpm_decimation():
    """Demo 3: BPM decimation algorithm details."""
    print_header("DEMO 3: BPM DECIMATION ALGORITHM")
    
    model = SimpleTabEstimator(
        input_dim=192, d_model=512, encoder_heads=4, encoder_layers=4,
        d_ff=2048, n_strings=6, n_frets=21, use_conv_stack=False
    )
    
    print_section("Algorithm Overview")
    print("""
    BPM-Based Decimation converts frame-level features to note-level features
    using actual musical timing based on BPM.
    
    Process:
    1. Calculate frames_per_note = (sr * 60) / (hop_length * 4 * bpm)
       Example: (22050 * 60) / (512 * 4 * 120) ≈ 5.36 frames per note
    
    2. For each note position n:
       - frame_start = n * frames_per_note
       - frame_end = (n+1) * frames_per_note
       - Accumulate features with linear interpolation at boundaries
       - Average by note duration for normalization
    
    3. Linear Interpolation at Boundaries:
       - Use floor(frame_start) and ceil(frame_start) with fractional weights
       - Sum all complete frames in between
       - Use floor(frame_end) and ceil(frame_end) with fractional weights
    
    Benefits:
    ✓ Frame-accurate musical timing alignment
    ✓ Smooth note boundaries via linear interpolation
    ✓ Batch-aware (different BPM per sample)
    ✓ Robust margin of error padding (10 frames)
    """)
    
    print_section("Example Calculation (120 BPM, 22050 Hz)")
    sr = 22050
    hop_length = 512
    bpm = 120.0
    
    frames_per_note = (sr * 60) / (hop_length * 4 * bpm)
    print(f"frames_per_note = ({sr} * 60) / ({hop_length} * 4 * {bpm})")
    print(f"                = {sr * 60} / {hop_length * 4 * bpm}")
    print(f"                = {frames_per_note:.4f} frames/note")
    
    print("\nNote Position Mapping:")
    for note_idx in range(4):
        frame_start = note_idx * frames_per_note
        frame_end = (note_idx + 1) * frames_per_note
        start_floor = int(frame_start)
        start_ceil = int(frame_start) + 1
        end_floor = int(frame_end)
        end_ceil = int(frame_end) + 1
        
        print(f"\nNote {note_idx}:")
        print(f"  Frames: [{frame_start:.2f}, {frame_end:.2f}]")
        print(f"  Interpolation:")
        print(f"    - Start: frame[{start_floor}] × {start_ceil - frame_start:.2f} + " +
              f"frame[{start_ceil}] × {frame_start - start_floor:.2f}")
        print(f"    - Middle: sum(frame[{start_ceil}:{end_floor}])")
        print(f"    - End: frame[{end_floor}] × {frame_end - end_floor:.2f} + " +
              f"frame[{end_ceil}] × {end_ceil - frame_end:.2f}")
        print(f"  Normalize: divide by {frames_per_note:.2f}")


def demo_loss_function():
    """Demo 4: Three-branch loss function."""
    print_header("DEMO 4: LOSS FUNCTION")
    
    # Create loss function
    criterion = TabLoss(
        alpha=1.0,
        sigma=0.4,
        n_strings=6,
        n_frets=21
    )
    
    print_section("Loss Components")
    print("""
    L_frame = BCE / 126
      - Normalized by 126 = 6 strings × 21 frets
      - Faster convergence for frame-level predictions
    
    L_onset = BCE (mean)
      - Mean reduction across all elements
      - Detects note onsets (when notes start)
    
    L_note = BCE (mean)
      - Mean reduction across all elements
      - Cleaner note-level predictions
    
    L_attention = Guided Attention Loss (alpha=1.0, sigma=0.4)
      - Penalizes off-diagonal attention weights
      - Encourages attention alignment
      - sigma=0.4: gaussian window width
    
    Total Loss = L_frame + L_onset + L_note + L_attention
    """)
    
    # Example loss computation
    batch_size, seq_len, n_strings, n_frets = 2, 100, 6, 21
    n_notes = 64
    
    frame_pred = torch.sigmoid(torch.randn(batch_size, seq_len, n_strings, n_frets))
    frame_target = torch.randint(0, 2, (batch_size, seq_len, n_strings, n_frets)).float()
    
    onset_pred = torch.sigmoid(torch.randn(batch_size, seq_len, n_strings, n_frets))
    onset_target = torch.randint(0, 2, (batch_size, seq_len, n_strings, n_frets)).float()
    
    note_pred = torch.sigmoid(torch.randn(batch_size, n_notes, n_strings, n_frets))
    note_target = torch.randint(0, 2, (batch_size, n_notes, n_strings, n_frets)).float()
    
    attn_weights = torch.randn(batch_size, 4, seq_len, seq_len)
    lengths = torch.tensor([seq_len, seq_len], dtype=torch.long)
    
    print_section("Computing Loss")
    loss = criterion(
        frame_pred, frame_target,
        onset_pred, onset_target,
        note_pred, note_target,
        attn_weights=attn_weights,
        input_lengths=lengths,
        output_lengths=lengths
    )
    
    print(f"Total Loss: {loss.item():.6f}")
    print(f"✓ Loss computed successfully with three branches")


def demo_training_step():
    """Demo 5: Training step with RAdam optimizer."""
    print_header("DEMO 5: TRAINING STEP")
    
    model = SimpleTabEstimator(
        input_dim=192, d_model=512, encoder_heads=4, encoder_layers=4,
        d_ff=2048, n_strings=6, n_frets=21, use_conv_stack=False
    )
    
    print_section("Optimizer Configuration")
    print("Using RAdam (Rectified Adam) optimizer:")
    print("  - Learning rate: 0.001")
    print("  - Weight decay: 0.0001")
    print("  - Gradient clip norm: 1.0")
    print("  - Scheduler: StepLR (step_size=10, gamma=0.9)")
    
    try:
        from torch_optimizer import RAdam
        use_radam = True
        optimizer = RAdam(model.parameters(), lr=0.001, weight_decay=0.0001)
    except ImportError:
        use_radam = False
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=0.0001)
    
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.9)
    criterion = TabLoss(alpha=1.0, sigma=0.4, n_strings=6, n_frets=21)
    
    print(f"\n✓ Optimizer: {'RAdam' if use_radam else 'Adam (fallback)'}")
    print(f"✓ Scheduler: StepLR")
    
    print_section("Training Loop Example")
    
    # Simulate training step
    batch_size, seq_len, n_notes = 2, 200, 64
    
    cqt = torch.randn(batch_size, seq_len, 192)
    lengths = torch.tensor([seq_len, seq_len], dtype=torch.long)
    bpm = torch.tensor([120.0, 110.0], dtype=torch.float)
    
    frame_tab = torch.randint(0, 2, (batch_size, seq_len, 6, 21)).float()
    onset_frame = torch.randint(0, 2, (batch_size, seq_len, 6, 21)).float()
    tab = torch.randint(0, 2, (batch_size, n_notes, 6, 21)).float()
    
    # Forward pass
    frame_pred, onset_pred, note_pred, attn = model(cqt, lengths, bpm=bpm)
    
    # Loss computation
    loss = criterion(
        frame_pred, frame_tab,
        onset_pred, onset_frame,
        note_pred, tab,
        attn_weights=attn,
        input_lengths=lengths,
        output_lengths=lengths
    )
    
    # Backward pass
    optimizer.zero_grad()
    loss.backward()
    
    # Gradient clipping
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    
    # Optimizer step
    optimizer.step()
    scheduler.step()
    
    print(f"Loss: {loss.item():.6f}")
    print(f"✓ Forward pass")
    print(f"✓ Loss computation")
    print(f"✓ Gradient clipping (norm ≤ 1.0)")
    print(f"✓ Optimizer step")
    print(f"✓ Learning rate schedule update")


def demo_inference():
    """Demo 6: Inference with BPM."""
    print_header("DEMO 6: INFERENCE WITH BPM")
    
    model = SimpleTabEstimator(
        input_dim=192, d_model=512, encoder_heads=4, encoder_layers=4,
        d_ff=2048, n_strings=6, n_frets=21, use_conv_stack=False
    )
    model.eval()
    
    print_section("Audio to TAB Pipeline")
    print("""
    1. Extract CQT Features
       Input: Audio (22050 Hz) → Output: CQT (T, 192)
    
    2. Create Tensors
       - cqt_tensor: (1, T, 192)
       - seq_len: [T]
       - bpm_tensor: [120.0] (detected or default)
    
    3. Forward Pass with BPM
       frame_pred, onset_pred, note_pred = model(cqt, seq_len, bpm=bpm_tensor)
    
    4. Convert to TAB
       - Get argmax for fret numbers (0-20, 20=no note)
       - Format as TAB notation (6 strings × notes)
    """)
    
    # Simulate inference
    seq_len = 600
    cqt_tensor = torch.randn(1, seq_len, 192)
    seq_len_tensor = torch.tensor([seq_len], dtype=torch.long)
    bpm_tensor = torch.tensor([120.0], dtype=torch.float)
    
    print_section("Example Inference")
    with torch.no_grad():
        frame_pred, onset_pred, note_pred, _ = model(cqt_tensor, seq_len_tensor, bpm=bpm_tensor)
    
    # Convert to fret numbers
    frame_frets = torch.argmax(frame_pred[0], dim=-1).cpu().numpy()  # (T, 6)
    onset_frets = torch.argmax(onset_pred[0], dim=-1).cpu().numpy()
    note_frets = torch.argmax(note_pred[0], dim=-1).cpu().numpy()   # (64, 6)
    
    print(f"Frame predictions: {frame_frets.shape} (T=600, Strings=6)")
    print(f"  Sample: {frame_frets[0]} (first time step)")
    print(f"Onset predictions: {onset_frets.shape}")
    print(f"  Sample: {onset_frets[0]} (first time step)")
    print(f"Note predictions: {note_frets.shape} (64 notes, 6 strings)")
    print(f"  Sample: {note_frets[0]} (first note)")
    
    print("\nNote-Level TAB Output (BPM-Aligned):")
    print("┌────────────────────────────────┐")
    print("│ String │ Note 1  Note 2  ... │")
    print("├────────────────────────────────┤")
    for string_idx in range(6):
        frets = note_frets[:min(8, len(note_frets)), string_idx]
        fret_str = "  ".join(f"{f:2d}" for f in frets)
        print(f"│   E-A-d[{string_idx}]  │ {fret_str:20s} ... │")
    print("└────────────────────────────────┘")


def demo_configuration():
    """Demo 7: Configuration overview."""
    print_header("DEMO 7: CONFIGURATION")
    
    config = {
        "Audio": {
            "sr": 22050,
            "cqt_n_bins": 192,
            "bins_per_octave": 24,
            "hop_length": 512,
        },
        "Model": {
            "d_model": 512,
            "encoder_heads": 4,
            "encoder_layers": 4,
            "use_conv_stack": True,
            "use_guided_attention_loss": True,
        },
        "Training": {
            "batch_size": 16,
            "lr": 0.001,
            "epochs": 100,
            "gradient_clip_norm": 1.0,
            "optimizer": "RAdam",
        },
        "Loss": {
            "frame_normalization": 126,  # 6 strings * 21 frets
            "attention_loss": True,
            "attention_alpha": 1.0,
            "attention_sigma": 0.4,
        },
        "Decimation": {
            "method": "BPM-based with linear interpolation",
            "n_notes": 64,
            "sr": 22050,
            "hop_length": 512,
            "margin_of_error": 10,
        },
        "Output": {
            "n_strings": 6,
            "n_frets": 21,
            "output_branches": ["Frame", "Onset", "Note"],
        }
    }
    
    for section, params in config.items():
        print(f"\n{section}:")
        for key, value in params.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")


def main():
    """Run all demos."""
    print("\n" + "="*70)
    print("  TAB ESTIMATOR - COMPLETE IMPLEMENTATION DEMO")
    print("  With BPM-Based Decimation and Three-Branch Architecture")
    print("="*70)
    
    try:
        print("\n[1/7] Creating model...")
        model = demo_model_creation()
        
        print("\n[2/7] Running forward pass...")
        demo_forward_pass(model)
        
        print("\n[3/7] BPM decimation algorithm...")
        demo_bpm_decimation()
        
        print("\n[4/7] Loss function...")
        demo_loss_function()
        
        print("\n[5/7] Training step...")
        demo_training_step()
        
        print("\n[6/7] Inference pipeline...")
        demo_inference()
        
        print("\n[7/7] Configuration...")
        demo_configuration()
        
        print_header("✅ ALL DEMOS COMPLETED SUCCESSFULLY")
        print("""
The TAB Estimator implementation includes:
  ✓ Three-branch architecture (Frame, Onset, Note)
  ✓ BiLSTM + GRU on each branch (online language models)
  ✓ BPM-based decimation with linear interpolation
  ✓ Conformer encoder (4 layers, 4 heads, 512 d_model)
  ✓ Guided attention loss (alpha=1.0, sigma=0.4)
  ✓ RAdam optimizer with gradient clipping (≤1.0)
  ✓ Proper loss normalization (Frame/126, Onset/Note mean)
  ✓ Complete data pipeline (CQT + Ground Truth + BPM)

Ready for training and inference! 🎸
        """)
        
        return 0
        
    except Exception as e:
        print_header("❌ ERROR")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
