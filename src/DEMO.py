"""
Quick demonstration script showing the complete workflow
"""

import os
import sys

def demo():
    print("\n" + "="*70)
    print("TAB ESTIMATOR - SIMPLIFIED WORKFLOW DEMO")
    print("="*70 + "\n")
    
    print("This demo shows the complete workflow:\n")
    print("1. DATA PREPROCESSING (JAMS → NPZ)")
    print("2. MODEL TRAINING")
    print("3. INFERENCE ON NEW AUDIO\n")
    
    print("="*70)
    print("STEP 1: PREPROCESS DATA")
    print("="*70)
    
    preprocess_cmd = """
python preprocess_jams.py \\
    --jams_dir ../data/Guitarset/annotation \\
    --audio_dir <path_to_guitarset_audio> \\
    --output_dir ../data/npz \\
    --config config_simplified.yaml \\
    --n_cores 4
"""
    
    print("\nRun this command to preprocess JAMS files to NPZ format:")
    print(preprocess_cmd)
    
    print("\nWhat happens:")
    print("  • Reads JAMS annotation files from data/Guitarset/annotation/")
    print("  • Loads corresponding audio files")
    print("  • Extracts CQT features (192 bins)")
    print("  • Converts TAB annotations to numeric format")
    print("  • Saves as NPZ files in ../data/npz/")
    print("  • Creates frame-level and note-level targets\n")
    
    print("="*70)
    print("STEP 2: TRAIN MODEL")
    print("="*70)
    
    train_cmd = """
python train_simplified.py \\
    --config config_simplified.yaml \\
    --data_dir ../data/npz \\
    --model_dir ./models \\
    --tb_dir ./runs \\
    --batch_size 16 \\
    --num_epochs 100
"""
    
    print("\nRun this command to train the model:")
    print(train_cmd)
    
    print("\nWhat happens:")
    print("  • Loads NPZ files from ../data/npz/")
    print("  • Splits into train/val (80/20 by default)")
    print("  • Creates SimpleTabEstimator model with Conformer encoder")
    print("  • Trains for 100 epochs with Adam optimizer")
    print("  • Saves best model to ./models/best_model.pth")
    print("  • Logs to TensorBoard (tensorboard --logdir ./runs)\n")
    
    print("="*70)
    print("STEP 3: INFERENCE")
    print("="*70)
    
    infer_cmd = """
python predict_simplified.py \\
    --audio <path_to_audio.wav> \\
    --model ./models/best_model.pth \\
    --config config_simplified.yaml \\
    --bpm 120 \\
    --threshold 0.5 \\
    --output predictions.npy
"""
    
    print("\nRun this command to make predictions on new audio:")
    print(infer_cmd)
    
    print("\nWhat happens:")
    print("  • Loads trained model from ./models/best_model.pth")
    print("  • Extracts CQT from input audio")
    print("  • Makes frame-level and note-level predictions")
    print("  • Converts predictions to TAB notation")
    print("  • Displays results in human-readable format")
    print("  • Saves predictions to predictions.npy (optional)\n")
    
    print("="*70)
    print("KEY FILES")
    print("="*70)
    
    files_info = {
        "config_simplified.yaml": "Model and training configuration",
        "network_simplified.py": "Model architecture (Conformer + Heads)",
        "data_utils_simplified.py": "Data loading and preprocessing",
        "preprocess_jams.py": "JAMS to NPZ conversion",
        "train_simplified.py": "Training script",
        "predict_simplified.py": "Inference script",
    }
    
    print()
    for filename, description in files_info.items():
        print(f"  • {filename:<30} - {description}")
    
    print("\n" + "="*70)
    print("CUSTOMIZATION TIPS")
    print("="*70)
    
    tips = [
        ("Adjust hyperparameters", "Edit config_simplified.yaml"),
        ("Modify model architecture", "Edit network_simplified.py (ConformerBlock, SimpleTabEstimator)"),
        ("Add data augmentation", "Edit data_utils_simplified.py (TabDataset.__getitem__)"),
        ("Change loss function", "Edit network_simplified.py (TabLoss)"),
        ("Use CPU instead of GPU", "Pass --device cpu to training scripts"),
        ("Resume training", "Use --resume <checkpoint> in train_simplified.py"),
    ]
    
    print()
    for tip, how in tips:
        print(f"  • {tip:<30} → {how}")
    
    print("\n" + "="*70)
    print("QUICK REFERENCE - CONFIG PARAMETERS")
    print("="*70)
    
    params = {
        "d_model": "Model dimension (512 is good, try 256 or 1024)",
        "encoder_heads": "Number of attention heads (4-8 is typical)",
        "encoder_layers": "Depth of encoder (2-8 layers)",
        "batch_size": "Training batch size (16-32 typical)",
        "lr": "Learning rate (0.0001 to 0.01 typical)",
        "use_conv_stack": "Enable Conv preprocessing (True/False)",
        "use_guided_attention_loss": "Enable attention regularization (True/False)",
    }
    
    print()
    for param, description in params.items():
        print(f"  • {param:<30} - {description}")
    
    print("\n" + "="*70)
    print("EXPECTED OUTPUT SHAPES")
    print("="*70)
    
    print("""
  Input:
    • CQT spectrogram: (B, T, 192)
      - B = batch size
      - T = time frames
      - 192 = CQT bins
  
  Output (if use_conv_stack=True):
    • After ConvStack: (B, T/4, 512) - time reduced by 4x
    • After Conformer: (B, T/4, 512)
    • Frame predictions: (B, T/4, 6, 21)
    • Note predictions: (B, ~64, 6, 21)
  
  TAB format:
    • (6, 21) = 6 strings × 21 classes
    • Classes 0-19 = fret numbers
    • Class 20 = "no note" (silence)
""")
    
    print("="*70)
    print("TROUBLESHOOTING")
    print("="*70)
    
    issues = {
        "CUDA out of memory": "Reduce batch_size or d_model in config",
        "Slow training": "Check if GPU is being used (nvidia-smi)",
        "Poor predictions": "Verify data preprocessing, try more epochs",
        "Can't find JAMS files": "Check path format: ../data/Guitarset/annotation",
        "Audio file not found": "Ensure --audio_dir path is correct",
    }
    
    print()
    for issue, solution in issues.items():
        print(f"  • {issue:<30} → {solution}")
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    
    print("""
  1. Follow STEP 1-3 above in order
  2. Monitor training with TensorBoard: tensorboard --logdir ./runs
  3. Experiment with different hyperparameters
  4. Consider adding post-processing to smooth predictions
  5. Evaluate on test set using appropriate metrics
  6. Deploy model for real-time inference
""")
    
    print("="*70 + "\n")


if __name__ == '__main__':
    demo()
