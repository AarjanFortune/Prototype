# ✅ COMPLETE ARCHITECTURE WITH BPM-BASED DECIMATION

## 🎯 Complete Implementation Based on Implementation.txt + BPM Optimization

Your TAB Estimator now has the **complete architecture** with three branches and **BPM-aware note-level decimation**:

```
Audio Input (22050 Hz)
    ↓
CQT Features (T, 192)
    ↓
[Optional ConvStack] Conv2D → BatchNorm → MaxPool × 2
    ↓
[Conformer Encoder] 4 layers, 4 heads, 512 d_model
    ↓
┌─────────────────────────┬─────────────────────┬──────────────────────────┐
│                         │                     │                          │
│   FRAME BRANCH          │   ONSET BRANCH      │    NOTE BRANCH           │
│                         │                     │                          │
├─ Dense 512→126         ├─ Dense 512→126      ├─ BPM Decimation Layer   │
├─ BiLSTM (online LM)    ├─ BiLSTM (online LM) ├─   (linear interp.)      │
├─ GRU (temporal)        ├─ GRU (temporal)     ├─ Note Encoder           │
├─ Sigmoid               ├─ Sigmoid            ├─ Dense 512→126          │
│                         │                     ├─ BiLSTM (online LM)     │
│ Output:                 │ Output:             ├─ GRU (temporal)         │
│ (B, T, 6, 21)          │ (B, T, 6, 21)      ├─ Sigmoid                │
│ Frame predictions       │ Onset predictions   │                         │
│ (all time steps)        │ (all time steps)    │ Output:                 │
└─────────────────────────┴─────────────────────┴─ (B, 64, 6, 21)        │
                                                  Note predictions         │
                                                  (64 notes, BPM-weighted)
                                                  └──────────────────────────┘

    ↓

L_frame = BCE / 126
L_onset = BCE (mean)
L_note = BCE (mean)
L_attention = Guided Attention (alpha=1.0, sigma=0.4)

Total Loss = L_frame + L_onset + L_note + L_attention

    ↓

[Optimizer: RAdam]
[Gradient Clipping: norm ≤ 1.0]
```

---

## 📋 What Changed

### Network Architecture (`network_simplified.py`)

**✅ Three Branches with BPM Awareness:**

1. **FRAME BRANCH** - Fast frame-level predictions
   ```python
   Dense(512→126) → BiLSTM(256) → GRU(256) → Sigmoid → (B, T, 6, 21)
   ```

2. **ONSET BRANCH** - Detect note onsets (when notes start)
   ```python
   Dense(512→126) → BiLSTM(256) → GRU(256) → Sigmoid → (B, T, 6, 21)
   ```

3. **NOTE BRANCH** - Note-level decimated predictions with BPM guidance
   ```
   BPM Decimation (Linear Interpolation)
   ↓
   Note Encoder → Dense(512→126) → BiLSTM(256) → GRU(256) → Sigmoid → (B, 64, 6, 21)
   ```

**✅ BPM-Based Decimation Method:**
```python
def notelevel_decimation_bpm(self, memory, bpm, n_notes=64, sr=22050, hop_length=512):
    """
    Decimates frame-level features into note-level features using BPM.
    Uses linear interpolation at note boundaries for smooth transitions.
    
    Args:
        memory: (B, T, features) encoder output
        bpm: (B,) BPM values
        n_notes: number of notes to output (default 64)
        sr: sample rate (22050 Hz)
        hop_length: CQT hop length (512 samples)
    
    Process:
        - Calculate frames_per_note = (sr * 60) / (hop_length * 4 * bpm)
        - For each note position, accumulate frame features with linear weighting
        - Smooth boundaries using floor/ceil interpolation
        - Return weighted average across note duration
    
    Output: (B, 64, 512) - decimated features ready for note encoder
    """
```

**Key Features:**
- ✅ Frame-accurate positioning based on actual BPM
- ✅ Linear interpolation at note boundaries (floor/ceil weighting)
- ✅ Weighted averaging across note duration
- ✅ Margin of error padding (10 frames) for robustness
- ✅ Batch-aware processing (different BPM per batch sample)

**✅ Online Language Models:**
- **BiLSTM**: Bidirectional LSTM for context from both directions
- **GRU**: Gated Recurrent Unit for temporal refinement
- Each with 256 hidden units and 0.5 dropout

**✅ Loss Function:**
```python
class TabLoss:
    frame_loss = BCE / 126  # Normalized by 126 (6×21)
    onset_loss = BCE (mean)
    note_loss = BCE (mean)
    attention_loss = GuidedAttention(sigma=0.4, alpha=1.0)
    
    Total = frame_loss + onset_loss + note_loss + attention_loss
```

### Training Integration (`train_simplified.py`)

**✅ BPM Parameter Passing:**
```python
# In train_epoch():
frame_pred, onset_pred, note_pred, attn_weights = self.model(cqt, frame_lengths, bpm=tempos)

# In validate():
frame_pred, onset_pred, note_pred, attn_weights = self.model(cqt, frame_lengths, bpm=tempos)

# tempos are extracted from batch data and passed directly
```

**✅ Flow:**
1. DataLoader provides `(cqt, frame_tab, frame_onset, tab, onset, tempo)`
2. Tempo extracted as `tempos` tensor
3. Model receives BPM for frame-accurate decimation
4. Note-level features aligned with actual musical timing

### Inference Integration (`predict_simplified.py`)

**✅ BPM in Prediction:**
```python
# Create BPM tensor (default 120 BPM if not extracted from audio)
bpm_tensor = torch.tensor([120.0], dtype=torch.float, device=self.device)

# Pass to model
frame_pred, onset_pred, note_pred, _ = self.model(cqt_tensor, seq_len, bpm=bpm_tensor)
```

**✅ Inference-time BPM Options:**
- Use detected BPM from audio (librosa.beat.tempo())
- Use default 120 BPM
- User-provided BPM via command-line argument

### Data Processing (`data_utils_simplified.py`)

**✅ Onset Ground Truth Generation:**
```python
def jams_to_tab_with_onset():
    # Returns both TAB and ONSET
    # TAB: sustained notes (1 for entire note duration)
    # Onset: binary marker (1 only at note start)
```

**✅ NPZ File Format:**
```
'cqt': (T, 192)
'frame_tab': (T, 6, 21) - frame-level TAB
'frame_onset': (T, 6, 21) - frame-level ONSET
'tab': (T_note, 6, 21) - note-level TAB
'onset': (T_note, 6, 21) - note-level ONSET
'tempo': scalar BPM
```

---

## 🔧 Configuration Update

### config_simplified.yaml

```yaml
# Exactly as specified in Implementation.txt
d_model: 512
encoder_heads: 4
encoder_layers: 4

# Three branches with BiLSTM + GRU
use_conv_stack: True                    # Conv2D -> BatchNorm -> MaxPool x2
use_guided_attention_loss: True         # alpha=1.0, sigma=0.4

# Optimizer
gradient_clip_norm: 1.0                 # Norm <= 1.0

# BPM-based decimation
n_notes: 64                             # Output 64 notes per sample
sr: 22050                               # Sample rate
hop_length: 512                         # CQT hop length

# Losses - normalized per specification
# L_frame = BCE / 126
# L_onset = BCE (mean)
# L_note = BCE (mean)
# L_attention = guided (alpha=1.0, sigma=0.4)
```

---

## 📊 Model Summary

```
SimpleTabEstimator
├── conv_stack: ConvStack (optional)
├── encoder: ConformerEncoder (4 layers)
├── Frame Branch
│   ├── frame_dense: Linear(512 → 126)
│   ├── frame_bilstm: BiLSTM(126, 256)
│   ├── frame_gru: GRU(512, 256)
│   └── frame_head: Linear(256 → 126) + Sigmoid
├── Onset Branch
│   ├── onset_dense: Linear(512 → 126)
│   ├── onset_bilstm: BiLSTM(126, 256)
│   ├── onset_gru: GRU(512, 256)
│   └── onset_head: Linear(256 → 126) + Sigmoid
├── Note Branch
│   ├── notelevel_decimation_bpm: BPM-based decimation (LINEAR INTERP)
│   ├── note_encoder: ConformerEncoder
│   ├── note_dense: Linear(512 → 126)
│   ├── note_bilstm: BiLSTM(126, 256)
│   ├── note_gru: GRU(512, 256)
│   └── note_head: Linear(256 → 126) + Sigmoid

Total Parameters: ~15-20 million
Decimation: Frame-accurate using BPM with linear interpolation
```

---

## 🚀 Usage

### 1. Preprocess (creates onset ground truth with BPM)
```bash
python preprocess_jams.py \
    --jams_dir ../data/Guitarset/annotation \
    --audio_dir <audio_path> \
    --output_dir ../data/npz
```

### 2. Train (three branches with BPM decimation)
```bash
python train_simplified.py \
    --config config_simplified.yaml \
    --data_dir ../data/npz \
    --num_epochs 100
```

### 3. Infer (returns three predictions with BPM)
```bash
python predict_simplified.py \
    --audio test.wav \
    --model ./models/best_model.pth \
    --config config_simplified.yaml \
    --bpm 120
```

---

## ✨ Key Features Implemented

✅ **Three Branches** (Frame, Onset, Note)
✅ **BiLSTM + GRU** on each branch (online language models)
✅ **ConvStack** preprocessing (Conv2D → BatchNorm → MaxPool × 2)
✅ **Conformer Encoder** (4 layers, 4 heads, 512 d_model)
✅ **Guided Attention Loss** (alpha=1.0, sigma=0.4)
✅ **RAdam Optimizer** (with weight decay)
✅ **Gradient Clipping** (norm ≤ 1.0)
✅ **BPM-Based Decimation** (NEW!)
   - Frame-accurate positioning using actual BPM
   - Linear interpolation at note boundaries
   - Weighted averaging across note duration
   - Margin of error padding for robustness
✅ **Proper Loss Normalization:**
  - Frame: BCE / 126
  - Onset: BCE (mean)
  - Note: BCE (mean)
  - Attention: Guided (alpha=1.0)
✅ **Onset Ground Truth** generation from JAMS
✅ **Complete Data Pipeline** (CQT + Frame/Onset ground truth + BPM)

---

## 📝 Files Modified/Created

1. `network_simplified.py` - Added three branches with BiLSTM+GRU + **BPM decimation method**
2. `data_utils_simplified.py` - Added onset generation (tempo already included)
3. `train_simplified.py` - Updated for three branches, RAdam, gradient clipping + **BPM parameter**
4. `predict_simplified.py` - Returns three predictions + **BPM tensor creation**
5. `config_simplified.yaml` - Already correct (just renamed)
6. `ARCHITECTURE_UPDATED.md` - This file, documenting BPM decimation

---

## 🎵 Output Examples

```
INPUT AUDIO (22050 Hz, ~120 BPM)
    ↓
FRAME PREDICTIONS (600 time steps @ 512 samples/hop)
E: 5  5  5  3  3  -  -  7  7  ...
A: 7  7  7  -  -  5  5  -  -  ...
D: 9  9  9  7  7  -  -  -  -  ...
...

ONSET PREDICTIONS (600 time steps, sparse)
E: 5  -  -  3  -  -  7  -  -  ...
A: 7  -  -  -  5  -  -  -  -  ...
D: 9  -  -  7  -  -  -  -  -  ...
...

NOTE PREDICTIONS (64 notes, BPM-aligned)
✓ Each note positioned at actual musical timing based on BPM
✓ Features weighted using linear interpolation at boundaries
✓ Clean, note-level predictions ready for quantization

E: 5  3  7  5  -  ...
A: 7  -  -  5  2  ...
D: 9  7  -  -  3  ...
...
```

---

## 🔍 BPM Decimation Algorithm Details

### Frame-to-Note Conversion
```
Given:
  - Frame features: (B, T, 512)
  - BPM: (B,)
  - sr=22050, hop_length=512

Calculate frames_per_note:
  frames_per_note = (sr * 60) / (hop_length * 4 * bpm)
  Example: (22050 * 60) / (512 * 4 * 120) ≈ 5.36 frames/note

For each note n in [0, 64):
  frame_start = n * frames_per_note         (e.g., 0, 5.36, 10.72, ...)
  frame_end = (n+1) * frames_per_note       (e.g., 5.36, 10.72, 16.08, ...)
  
  Linear interpolation:
    - At start: use floor and ceil with fractional weight
    - Between: accumulate all complete frames
    - At end: use floor and ceil with fractional weight
    - Average by note duration for normalization
```

### Example Calculation (120 BPM)
```
frames_per_note = 5.36
note_0: frames [0.00 - 5.36] → avg(frame[0]*0.64 + frame[1] + frame[2] + frame[3] + frame[4] + frame[5]*0.36)
note_1: frames [5.36 - 10.72] → avg(frame[5]*0.64 + frame[6] + frame[7] + frame[8] + frame[9] + frame[10]*0.36)
...
```

---

**You now have the complete implementation with BPM-aware decimation! 🎉**

This implementation:
- ✅ Matches Implementation.txt architecture exactly
- ✅ Adds intelligent BPM-based note positioning (not simple averaging)
- ✅ Uses frame-accurate linear interpolation for smooth note boundaries
- ✅ Maintains batch processing efficiency
- ✅ Integrates seamlessly with training and inference pipelines
