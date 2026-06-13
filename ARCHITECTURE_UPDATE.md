# ✅ UPDATED ARCHITECTURE - THREE BRANCHES

## 🎯 Complete Implementation Based on Implementation.txt

Your TAB Estimator now has the **complete architecture** with three branches:

```
Audio Input (22050 Hz)
    ↓
CQT Features (T, 192)
    ↓
[Optional ConvStack] Conv2D → BatchNorm → MaxPool × 2
    ↓
[Conformer Encoder] 4 layers, 4 heads, 512 d_model
    ↓
┌─────────────────────────┬─────────────────────┬──────────────────────┐
│                         │                     │                      │
│   FRAME BRANCH          │   ONSET BRANCH      │    NOTE BRANCH       │
│                         │                     │                      │
├─ Dense 512→126         ├─ Dense 512→126      ├─ Note Encoder       │
├─ BiLSTM (online LM)    ├─ BiLSTM (online LM) ├─ Dense 512→126      │
├─ GRU (temporal)        ├─ GRU (temporal)     ├─ BiLSTM (online LM) │
├─ Sigmoid               ├─ Sigmoid            ├─ GRU (temporal)     │
│                         │                     ├─ Sigmoid            │
│ Output:                 │ Output:             │                     │
│ (B, T, 6, 21)          │ (B, T, 6, 21)      │ Output:             │
│ Frame predictions       │ Onset predictions   │ (B, ~120, 6, 21)    │
└─────────────────────────┴─────────────────────┴──────────────────────┘

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

**✅ Three Branches Added:**

1. **FRAME BRANCH** - Fast frame-level predictions
   ```python
   Dense(512→126) → BiLSTM(256) → GRU(256) → Sigmoid → (B, T, 6, 21)
   ```

2. **ONSET BRANCH** - Detect note onsets (when notes start)
   ```python
   Dense(512→126) → BiLSTM(256) → GRU(256) → Sigmoid → (B, T, 6, 21)
   ```

3. **NOTE BRANCH** - Note-level decimated predictions
   ```python
   Note Encoder → Dense(512→126) → BiLSTM(256) → GRU(256) → Sigmoid → (B, ~120, 6, 21)
   ```

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

### Training (`train_simplified.py`)

**✅ RAdam Optimizer:**
```python
from torch_optimizer import RAdam
optimizer = RAdam(lr=0.001, weight_decay=0.0001)
```

**✅ Gradient Clipping (norm ≤ 1.0):**
```python
torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
```

**✅ Three-Branch Loss:**
```python
loss = criterion(
    frame_pred, frame_tab,
    onset_pred, frame_onset,
    note_pred, tab,
    attn_weights=attn_weights,
    input_lengths=frame_lengths,
    output_lengths=frame_lengths
)
```

### Inference (`predict_simplified.py`)

**✅ Returns Three Predictions:**
```
frame_tab_notation: (T, 6) - Frame-level fret numbers
onset_tab_notation: (T, 6) - Onset-level fret numbers  
note_tab_notation: (T_note, 6) - Note-level fret numbers
```

**✅ Displays All Three:**
```
FRAME-LEVEL TAB
E: 5  3  - 7  ...
A: 7  - 5  -  ...
...

ONSET-LEVEL TAB
E: 5  - - 7  ...
A: 7  - - -  ...
...

NOTE-LEVEL TAB
E: 5  3  7  ...
A: 7  5  -  ...
...
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
└── Note Branch
    ├── note_encoder: ConformerEncoder
    ├── note_dense: Linear(512 → 126)
    ├── note_bilstm: BiLSTM(126, 256)
    ├── note_gru: GRU(512, 256)
    └── note_head: Linear(256 → 126) + Sigmoid

Total Parameters: ~15-20 million
```

---

## 🚀 Usage

### 1. Preprocess (creates onset ground truth)
```bash
python preprocess_jams.py \
    --jams_dir ../data/Guitarset/annotation \
    --audio_dir <audio_path> \
    --output_dir ../data/npz
```

### 2. Train (three branches)
```bash
python train_simplified.py \
    --config config_simplified.yaml \
    --data_dir ../data/npz \
    --num_epochs 100
```

### 3. Infer (returns three predictions)
```bash
python predict_simplified.py \
    --audio test.wav \
    --model ./models/best_model.pth \
    --config config_simplified.yaml
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
✅ **Proper Loss Normalization:**
  - Frame: BCE / 126
  - Onset: BCE (mean)
  - Note: BCE (mean)
  - Attention: Guided (alpha=1.0)
✅ **Onset Ground Truth** generation from JAMS
✅ **Complete Data Pipeline** (CQT + Frame/Onset ground truth)

---

## 📝 Files Modified

1. `network_simplified.py` - Added three branches with BiLSTM+GRU
2. `data_utils_simplified.py` - Added onset generation
3. `train_simplified.py` - Updated for three branches, RAdam, gradient clipping
4. `predict_simplified.py` - Returns three predictions
5. `config_simplified.yaml` - Already correct (just renamed)

---

## 🎵 Output Examples

```
INPUT AUDIO (22050 Hz)
    ↓
FRAME PREDICTIONS (600 time steps)
E: 5  5  5  3  3  -  -  7  7  ...
A: 7  7  7  -  -  5  5  -  -  ...
D: 9  9  9  7  7  -  -  -  -  ...
...

ONSET PREDICTIONS (600 time steps, sparse)
E: 5  -  -  3  -  -  7  -  -  ...
A: 7  -  -  -  5  -  -  -  -  ...
D: 9  -  -  7  -  -  -  -  -  ...
...

NOTE PREDICTIONS (~120 time steps, cleaner)
E: 5  3  7  5  -  ...
A: 7  -  -  5  2  ...
D: 9  7  -  -  3  ...
...
```

---

**You now have the complete implementation matching your Implementation.txt architecture! 🎉**
