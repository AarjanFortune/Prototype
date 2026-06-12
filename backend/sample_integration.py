"""
Sample integration script showing how to connect with the trained model
from Refactor-TabEstimator and use it in the web app.

This is a reference implementation - use as a guide for setup.
"""

import torch
import numpy as np
from pathlib import Path
import sys

# Add paths
sys.path.insert(0, '/path/to/Refactor-TabEstimator/src')
sys.path.insert(0, './backend')

# Import from both projects
from config import MODEL_CONFIG, SAMPLE_RATE, GUITAR_TUNING
from model_utils import TabEstimator


def load_tabest_checkpoint(checkpoint_path: str) -> TabEstimator:
    """
    Load a TabEstimator checkpoint trained from Refactor-TabEstimator.
    
    Expected checkpoint structure:
    {
        'model': model_state_dict,
        'epoch': int,
        'loss': float,
        'config': dict
    }
    """
    checkpoint = torch.load(checkpoint_path, map_location='cpu')
    
    # Initialize model with training config if available
    if 'config' in checkpoint:
        config = checkpoint['config']
    else:
        config = MODEL_CONFIG
    
    model = TabEstimator(config)
    
    if 'model' in checkpoint:
        model.load_state_dict(checkpoint['model'])
    else:
        model.load_state_dict(checkpoint)
    
    return model.eval()


def load_refactor_tabest_model(checkpoint_path: str):
    """
    Load model directly from Refactor-TabEstimator.
    
    This assumes the repository structure and imports.
    """
    try:
        # Import from Refactor-TabEstimator
        sys.path.insert(0, '/path/to/Refactor-TabEstimator')
        from src.network import TabEstimator as RefactorTabEstimator
        
        checkpoint = torch.load(checkpoint_path, map_location='cpu')
        
        # Extract config if available
        if 'args' in checkpoint:
            args = checkpoint['args']
            model = RefactorTabEstimator(
                in_dim=args.in_dim,
                out_tab_dim=args.out_tab_dim,
                out_f0_dim=args.out_f0_dim,
                encoder_type=args.encoder_type,
            )
        else:
            # Use defaults from training
            model = RefactorTabEstimator(
                in_dim=192,
                out_tab_dim=6*21,
                out_f0_dim=44,
                encoder_type='conformer',
            )
        
        model.load_state_dict(checkpoint['model_state_dict'])
        return model.eval()
    
    except ImportError:
        print("Could not import from Refactor-TabEstimator")
        print("Make sure the path is correct")
        raise


def setup_model_integration():
    """
    Example setup to integrate model with the web app.
    
    Steps:
    1. Train model in Refactor-TabEstimator
    2. Copy checkpoint to backend/models/
    3. Run this function to verify
    4. Update backend/config.py with MODEL_PATH
    """
    
    model_path = "./backend/models/tabest_model.pth"
    
    if not Path(model_path).exists():
        print(f"Model not found at {model_path}")
        print("\nTo set up:")
        print("1. Train in Refactor-TabEstimator/")
        print("2. Copy checkpoint to backend/models/")
        print("3. Verify: python sample_integration.py")
        return
    
    print("Loading model...")
    model = load_tabest_checkpoint(model_path)
    
    print("✓ Model loaded successfully")
    print(f"  Device: {next(model.parameters()).device}")
    print(f"  Trainable params: {sum(p.numel() for p in model.parameters() if p.requires_grad)}")
    
    # Test inference
    print("\nTesting inference...")
    test_features = torch.randn(1, 100, 192)  # batch=1, frames=100, bins=192
    
    with torch.no_grad():
        output, lengths = model(test_features)
    
    print(f"✓ Inference successful")
    print(f"  Output shape: {output.shape}")
    print(f"  Expected: (1, 100, 6, 21)")


def integrate_with_amt_tools():
    """
    Example of using AMT-Tools features with the model.
    """
    try:
        from amt_tools.features import CQT
        from amt_tools.tools.utils import load_dict_npz
        
        print("AMT-Tools available!")
        
        # Example: Extract CQT features
        cqt = CQT(sr=SAMPLE_RATE, hop_length=512, n_bins=192)
        
        print(f"CQT extractor initialized")
        print(f"  Sample rate: {SAMPLE_RATE}")
        print(f"  Bins: 192")
        print(f"  Hop length: 512 samples")
        
    except ImportError:
        print("AMT-Tools not installed. Install with:")
        print("  pip install -e /path/to/amt-tools-master")


def setup_ensemble(model_paths: list) -> callable:
    """
    Create an ensemble predictor that averages multiple models.
    """
    models = [load_tabest_checkpoint(p) for p in model_paths]
    
    def ensemble_predict(features: np.ndarray, tempo: float = 120.0):
        """Ensemble prediction by averaging model outputs."""
        predictions = []
        confidences = []
        
        for model in models:
            features_tensor = torch.from_numpy(features[np.newaxis, :, :]).float()
            
            with torch.no_grad():
                output, _ = model(features_tensor)
                output_probs = torch.softmax(output, dim=-1)
                
                # Get argmax predictions
                tab_pred = torch.argmax(output_probs, dim=-1)[0].numpy()
                
                # Get max confidence per string
                conf = torch.max(output_probs, dim=-1)[0][0].numpy()
                
                predictions.append(tab_pred)
                confidences.append(conf)
        
        # Average predictions
        avg_tab = np.mean(predictions, axis=0)
        avg_conf = np.mean(confidences, axis=0)
        
        return {
            'tab': avg_tab.astype(np.int32),
            'confidence': avg_conf,
            'n_models': len(models),
        }
    
    return ensemble_predict


if __name__ == "__main__":
    print("=== Guitar Transcription Model Integration ===\n")
    
    print("1. Setting up main model...")
    try:
        setup_model_integration()
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n2. Checking AMT-Tools...")
    try:
        integrate_with_amt_tools()
    except Exception as e:
        print(f"Note: {e}")
    
    print("\n=== Setup Complete ===")
    print("\nNext steps:")
    print("1. Train your model or download a checkpoint")
    print("2. Place it in backend/models/")
    print("3. Update backend/config.py with MODEL_PATH")
    print("4. Run: python -m uvicorn main:app --reload")
    print("5. Open: http://localhost:5173")
