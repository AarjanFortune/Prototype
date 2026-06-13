# 📊 BPM Parameter Flow in SimpleTabEstimator

## Overview: Where BPM is Passed and Used

```
┌─────────────────────────────────────────────────────────────────┐
│                      COMPLETE BPM FLOW                          │
└─────────────────────────────────────────────────────────────────┘

1. DATA LOADING (Batch)
   ↓
   data_utils_simplified.py: TabDataset.__getitem__()
   Returns: (cqt, frame_tab, frame_onset, tab, onset, tempo)
                                                           ↓
                                                        TEMPO

2. TRAINING LOOP
   ↓
   train_simplified.py: train_epoch()
   for batch_idx, batch in enumerate(dataloader):
       cqt, frame_lengths, frame_tab, frame_onset, tab, onset, tempos = batch
                                                                          ↓
                                                                       TEMPOS (tensor)

3. MODEL FORWARD PASS
   ↓
   network_simplified.py: SimpleTabEstimator.forward(x, lengths=None, bpm=None)
                                                                       ↓ bpm parameter
   
4. NOTE BRANCH DECIMATION
   ↓
   if bpm is not None:
       encoder_out_decimated = self.notelevel_decimation_bpm(encoder_out, bpm)
                                                                              ↓
   Uses frames_per_note = (sr * 60) / (hop_length * 4 * bpm[n_batch])

5. NOTE ENCODER + PREDICTIONS
   ↓
   (B, 64, 6, 21) - BPM-aligned predictions
```

---

## 🔍 Detailed Code Locations

### 1️⃣ FORWARD() METHOD SIGNATURE
**File:** `network_simplified.py` (Line ~427)

```python
def forward(self, x, lengths=None, bpm=None):
    """
    Args:
        x: (B, T, n_bins) CQT spectrogram
        lengths: (B,) sequence lengths
        bpm: (B,) BPM values for BPM-based decimation  ← BPM PARAMETER HERE
    Returns:
        frame_pred: (B, T, 6, 21)
        onset_pred: (B, T, 6, 21)
        note_pred: (B, T_note, 6, 21)
        attn_weights: attention weight tensor
    """
```

---

### 2️⃣ WHERE BPM IS USED - NOTE BRANCH
**File:** `network_simplified.py` (Line ~469)

```python
# ===== NOTE BRANCH =====
# BPM-based decimation with linear interpolation
if bpm is not None:
    # ✓ BPM USED HERE: Calls BPM-based decimation method
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
```

---

### 3️⃣ NOTELEVEL_DECIMATION_BPM() METHOD
**File:** `network_simplified.py` (Line ~505)

```python
def notelevel_decimation_bpm(self, memory, bpm, n_notes=64, sr=22050, hop_length=512):
    """
    BPM-based decimation using linear interpolation.
    
    Args:
        memory: (B, T, features) encoder output
        bpm: (B,) BPM values  ← BPM RECEIVED HERE
        n_notes: number of note positions (default 64)
        sr: sample rate (default 22050)
        hop_length: hop length in samples (default 512)
    """
    # memory: (batch, len, features)
    padded_memory = F.pad(memory, (0, 0, 0, 10))  # for margin of error
    batch_size = memory.shape[0]
    feature_size = memory.shape[2]
    output = torch.zeros(batch_size, n_notes, feature_size).to(memory.device)

    for n_batch in range(batch_size):
        # ✓ BPM USED HERE: Calculate frames per note based on actual BPM
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

    return output  # (B, 64, 512) - decimated features
```

---

### 4️⃣ WHERE BPM IS PASSED FROM - TRAINING
**File:** `train_simplified.py` (Line ~90)

```python
def train_epoch(self, dataloader):
    total_loss = 0.0
    
    for batch_idx, batch in enumerate(dataloader):
        # ✓ EXTRACT BPM FROM BATCH
        cqt, frame_lengths, frame_tab, frame_onset, tab, onset, tempos = batch
        #                                                              ↑ BPM values
        
        cqt = cqt.to(self.device)
        frame_tab = frame_tab.to(self.device)
        frame_onset = frame_onset.to(self.device)
        tab = tab.to(self.device)
        tempos = tempos.to(self.device)
        
        # Forward pass
        self.optimizer.zero_grad()
        
        # ✓ BPM PASSED HERE: Pass tempos to model
        frame_pred, onset_pred, note_pred, attn_weights = self.model(cqt, frame_lengths, bpm=tempos)
        #                                                                                      ↑ BPM parameter
        
        # Loss - three branches (frame, onset, note)
        loss = self.criterion(
            frame_pred, frame_tab,
            onset_pred, frame_onset,
            note_pred, tab,
            attn_weights=attn_weights,
            input_lengths=frame_lengths,
            output_lengths=frame_lengths
        )
```

---

### 5️⃣ VALIDATION PASS - ALSO USES BPM
**File:** `train_simplified.py` (Line ~142)

```python
def validate(self, dataloader):
    total_loss = 0.0
    self.model.eval()
    
    with torch.no_grad():
        for batch_idx, batch in enumerate(dataloader):
            # ✓ EXTRACT BPM FROM BATCH
            cqt, frame_lengths, frame_tab, frame_onset, tab, onset, tempos = batch
            #                                                             ↑ BPM values
            
            cqt = cqt.to(self.device)
            frame_tab = frame_tab.to(self.device)
            frame_onset = frame_onset.to(self.device)
            tab = tab.to(self.device)
            tempos = tempos.to(self.device)
            
            # Forward pass
            # ✓ BPM PASSED HERE: Pass tempos to model
            frame_pred, onset_pred, note_pred, attn_weights = self.model(cqt, frame_lengths, bpm=tempos)
            #                                                                                  ↑ BPM parameter
            
            # Loss computation
            loss = self.criterion(
                frame_pred, frame_tab,
                onset_pred, frame_onset,
                note_pred, tab,
                attn_weights=attn_weights,
                input_lengths=frame_lengths,
                output_lengths=frame_lengths
            )
```

---

### 6️⃣ INFERENCE - USES DEFAULT BPM
**File:** `predict_simplified.py` (Line ~75)

```python
def predict_audio(self, audio_path):
    """Predict TAB for a single audio file."""
    # Extract features
    cqt = TabDataPreprocessor.extract_cqt(...)
    
    # Convert to tensor
    cqt_tensor = torch.from_numpy(cqt).unsqueeze(0).float().to(self.device)
    
    # Get sequence length
    seq_len = torch.tensor([cqt.shape[0]], dtype=torch.long, device=self.device)
    
    # Predict with BPM
    # ✓ CREATE BPM TENSOR HERE
    bpm_tensor = torch.tensor([120.0], dtype=torch.float, device=self.device)
    #                                                        ↑ Default BPM (120)
    
    with torch.no_grad():
        # ✓ BPM PASSED HERE: Pass BPM tensor to model
        frame_pred, onset_pred, note_pred, _ = self.model(cqt_tensor, seq_len, bpm=bpm_tensor)
        #                                                                           ↑ BPM parameter
    
    # Convert to numpy
    frame_tab_pred = frame_pred[0].cpu().numpy()  # (T, 6, 21)
    onset_tab_pred = onset_pred[0].cpu().numpy()  # (T, 6, 21)
    note_tab_pred = note_pred[0].cpu().numpy()    # (64, 6, 21)
    
    return frame_tab_pred, onset_tab_pred, note_tab_pred, cqt
```

---

## 📋 Data Flow Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DATA SOURCE → USAGE                              │
└─────────────────────────────────────────────────────────────────────┘

TRAINING/VALIDATION:
    ↓
    data_utils_simplified.py
    ├─ TabDataset loads NPZ files
    └─ Returns: (cqt, frame_tab, frame_onset, tab, onset, tempo)
                                                              ↓
    train_simplified.py
    ├─ train_epoch() extracts: tempos = batch[6]
    ├─ validate() extracts: tempos = batch[6]
    └─ Both pass: model(..., bpm=tempos)
                               ↓
    network_simplified.py
    ├─ SimpleTabEstimator.forward(x, lengths, bpm=tempos)
    └─ Uses bpm in NOTE BRANCH:
       └─ self.notelevel_decimation_bpm(encoder_out, bpm)
          └─ frames_per_note = (sr * 60) / (hop_length * 4 * bpm[n_batch])

INFERENCE:
    ↓
    predict_simplified.py
    ├─ Creates: bpm_tensor = torch.tensor([120.0])
    └─ Passes: model(..., bpm=bpm_tensor)
                               ↓
    network_simplified.py
    ├─ SimpleTabEstimator.forward(x, lengths, bpm=bpm_tensor)
    └─ Uses bpm in NOTE BRANCH:
       └─ self.notelevel_decimation_bpm(encoder_out, bpm)
```

---

## 🎯 Key Takeaways

| Component | Location | Usage |
|-----------|----------|-------|
| **BPM Parameter Definition** | `network_simplified.py:427` | `def forward(self, x, lengths=None, bpm=None)` |
| **BPM Extraction (Training)** | `train_simplified.py:90` | `tempos = batch[6]` from dataloader |
| **BPM Extraction (Validation)** | `train_simplified.py:142` | `tempos = batch[6]` from dataloader |
| **BPM Creation (Inference)** | `predict_simplified.py:75` | `bpm_tensor = torch.tensor([120.0])` |
| **BPM Usage** | `network_simplified.py:469` | `if bpm is not None: encoder_out_decimated = self.notelevel_decimation_bpm(encoder_out, bpm)` |
| **Decimation Calculation** | `network_simplified.py:505-550` | `frames_per_note = (sr * 60) / (hop_length * 4 * bpm[n_batch])` |

---

## 🔗 Complete Call Stack

```
TRAINING:
┌─ train.py: dataloader batch
│  └─ Contains tempo value from NPZ file
├─ train_simplified.py: train_epoch()
│  ├─ Extracts: tempos = batch[6]
│  └─ Calls: model(cqt, frame_lengths, bpm=tempos)
│     └─ network_simplified.py: forward(x, lengths, bpm=tempos)
│        └─ Line 469: if bpm is not None:
│           └─ self.notelevel_decimation_bpm(encoder_out, bpm)
│              └─ Line 520: frames_per_note = (sr * 60) / (hop_length * 4 * bpm[n_batch])
│                 └─ Decimates to (B, 64, 512) note-level features

INFERENCE:
┌─ predict_simplified.py: predict_audio()
├─ Creates: bpm_tensor = torch.tensor([120.0])
└─ Calls: model(cqt_tensor, seq_len, bpm=bpm_tensor)
   └─ network_simplified.py: forward(x, lengths, bpm=bpm_tensor)
      └─ Same flow as training
```

---

## 💡 Important Notes

1. **BPM is Optional**: If `bpm=None`, falls back to simple average pooling (decimation_factor = frame_len // 120)
2. **Batch-Aware**: Different BPM for each sample in batch (`bpm[n_batch]`)
3. **Data Type**: BPM should be a tensor of floats: `torch.tensor([120.0], dtype=torch.float)`
4. **Training**: BPM comes from NPZ ground truth tempo
5. **Inference**: BPM can be detected from audio or set to default (120)
6. **Note Decimation**: Linear interpolation used for frame-accurate positioning
