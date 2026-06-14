"""
Simplified training script for TAB estimation
- Clean training loop with high-performance GPU AMP optimization
- Validation
- Model checkpointing
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.tensorboard import SummaryWriter
import yaml
import os
import gc
import argparse
from tqdm import tqdm
import numpy as np
import glob
from pathlib import Path

from network_simplified import SimpleTabEstimator, TabLoss
from data_utils_simplified import get_data_loaders, TabDataPreprocessor
import warnings
warnings.filterwarnings('ignore')

# RAdam optimizer
try:
    from torch_optimizer import RAdam
except ImportError:
    print("Warning: torch_optimizer not installed, using Adam instead")
    RAdam = optim.Adam


class TabTrainer:
    """Trainer class for TAB estimation (Frame + Onset + Note branches)."""
    
    def __init__(self, config, device='cuda' if torch.cuda.is_available() else 'cpu'):
        self.config = config
        self.device = device
        
        print(f"Using device: {self.device}")
        if 'cuda' in str(self.device):
            print(f"GPU Name: {torch.cuda.get_device_name(0)}")
        
        # Model
        self.model = SimpleTabEstimator(config).to(device)
        
        # Loss
        self.criterion = TabLoss()
        
        # Optimizer - RAdam
        self.optimizer = RAdam(
            self.model.parameters(),
            lr=config['lr'],
            weight_decay=config.get('weight_decay', 0.0001)
        )
        
        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.StepLR(
            self.optimizer, step_size=10, gamma=0.9
        )
        
        # Gradient clipping norm
        self.gradient_clip_norm = config.get('gradient_clip_norm', 1.0)
        
        # Logging
        self.tb_writer = None
        self.best_val_loss = float('inf')
        self.start_epoch = 0
    
    def train_epoch(self, train_loader):
        """Train for one epoch using automatic mixed precision (AMP)."""
        self.model.train()
        total_loss = 0
        n_batches = 0
        
        # Initialize GradScaler for FP16 training on RTX 4050
        scaler = torch.cuda.amp.GradScaler(enabled=('cuda' in str(self.device)))
        
        pbar = tqdm(train_loader, desc='Training')
        for batch_idx, batch in enumerate(pbar):
            cqt, frame_tab, frame_onset, tab, onset, frame_lengths, note_lengths, tempos = batch
            
            # Non-blocking transfers pull data to GPU VRAM asynchronously
            cqt = cqt.to(self.device, non_blocking=True)
            frame_tab = frame_tab.to(self.device, non_blocking=True)
            frame_onset = frame_onset.to(self.device, non_blocking=True)
            tab = tab.to(self.device, non_blocking=True)
            onset = onset.to(self.device, non_blocking=True)
            frame_lengths = frame_lengths.to(self.device, non_blocking=True)
            note_lengths = note_lengths.to(self.device, non_blocking=True)
            
            # set_to_none=True safely saves modest amounts of memory over zero_grad()
            self.optimizer.zero_grad(set_to_none=True)
            
            # Forward pass with AMP autocast
            with torch.cuda.amp.autocast(enabled=('cuda' in str(self.device))):
                frame_pred, onset_pred, note_pred, attn_weights = self.model(cqt, frame_lengths, bpm=tempos)
                
                loss = self.criterion(
                    frame_pred, frame_tab,
                    onset_pred, frame_onset,
                    note_pred, tab,
                    attn_weights=attn_weights,
                    input_lengths=frame_lengths,
                    output_lengths=frame_lengths
                )
            
            # Backpropagation using loss scaling
            scaler.scale(loss).backward()
            
            # Unscale weights for safe gradient clipping
            scaler.unscale_(self.optimizer)
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.gradient_clip_norm)
            
            # Step optimizer and update scale factors
            scaler.step(self.optimizer)
            scaler.update()
            
            total_loss += loss.item()
            n_batches += 1
            
            pbar.set_postfix({'loss': f"{loss.item():.4f}"})
        
        # Force memory collection after epoch to prevent Windows RAM OOM crashes
        gc.collect()
        if 'cuda' in str(self.device):
            torch.cuda.empty_cache()
            
        return total_loss / max(n_batches, 1)
    
    def validate(self, val_loader):
        """Validate the model with mixed precision safety."""
        self.model.eval()
        total_loss = 0
        n_batches = 0
        
        pbar = tqdm(val_loader, desc='Validation')
        with torch.no_grad():
            for batch in pbar:
                cqt, frame_tab, frame_onset, tab, onset, frame_lengths, note_lengths, tempos = batch
                
                cqt = cqt.to(self.device, non_blocking=True)
                frame_tab = frame_tab.to(self.device, non_blocking=True)
                frame_onset = frame_onset.to(self.device, non_blocking=True)
                tab = tab.to(self.device, non_blocking=True)
                onset = onset.to(self.device, non_blocking=True)
                frame_lengths = frame_lengths.to(self.device, non_blocking=True)
                note_lengths = note_lengths.to(self.device, non_blocking=True)
                
                with torch.cuda.amp.autocast(enabled=('cuda' in str(self.device))):
                    frame_pred, onset_pred, note_pred, attn_weights = self.model(cqt, frame_lengths, bpm=tempos)
                    
                    loss = self.criterion(
                        frame_pred, frame_tab,
                        onset_pred, frame_onset,
                        note_pred, tab,
                        attn_weights=attn_weights,
                        input_lengths=frame_lengths,
                        output_lengths=frame_lengths
                    )
                
                total_loss += loss.item()
                n_batches += 1
                
                pbar.set_postfix({'loss': f"{loss.item():.4f}"})
        
        gc.collect()
        return total_loss / max(n_batches, 1)
    
    def train(self, train_loader, val_loader, num_epochs, model_dir='./models', tb_dir='./runs'):
        """Train the model."""
        os.makedirs(model_dir, exist_ok=True)
        os.makedirs(tb_dir, exist_ok=True)
        
        self.tb_writer = SummaryWriter(tb_dir)
        
        print(f"\nTraining for {num_epochs} epochs")
        print(f"Model will be saved to: {model_dir}")
        print(f"TensorBoard logs: {tb_dir}\n")
        
        for epoch in range(self.start_epoch, num_epochs):
            print(f"\nEpoch {epoch + 1}/{num_epochs}")
            
            # Train
            train_loss = self.train_epoch(train_loader)
            
            # Validate
            val_loss = self.validate(val_loader)
            
            # Update scheduler
            self.scheduler.step()
            
            # Log
            self.tb_writer.add_scalar('Loss/train', train_loss, epoch)
            self.tb_writer.add_scalar('Loss/val', val_loss, epoch)
            self.tb_writer.add_scalar('LR', self.optimizer.param_groups[0]['lr'], epoch)
            
            print(f"Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")
            
            # Save checkpoint
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                checkpoint_path = os.path.join(model_dir, 'best_model.pth')
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'best_val_loss': self.best_val_loss,
                    'config': self.config
                }, checkpoint_path)
                print(f"✓ Best model saved: {checkpoint_path}")
            
            # Save periodic checkpoint
            if (epoch + 1) % 10 == 0:
                periodic_path = os.path.join(model_dir, f'epoch_{epoch+1}.pth')
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'best_val_loss': self.best_val_loss,
                    'config': self.config
                }, periodic_path)
        
        self.tb_writer.close()
        print("\n✓ Training complete!")
    
    def load_checkpoint(self, checkpoint_path):
        """Load model from checkpoint."""
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.best_val_loss = checkpoint.get('best_val_loss', float('inf'))
        self.start_epoch = checkpoint.get('epoch', 0) + 1
        print(f"✓ Loaded checkpoint: {checkpoint_path}")


def main():
    parser = argparse.ArgumentParser(description='Train Tab Estimator')
    parser.add_argument('--config', type=str, default='config_simplified.yaml',
                      help='Path to config file')
    parser.add_argument('--data_dir', type=str, default='../data/npz',
                      help='Directory containing NPZ files')
    parser.add_argument('--model_dir', type=str, default='./models',
                      help='Directory to save models')
    parser.add_argument('--tb_dir', type=str, default='./runs',
                      help='Directory for TensorBoard logs')
    parser.add_argument('--num_epochs', type=int, default=None,
                      help='Number of epochs (overrides config)')
    parser.add_argument('--batch_size', type=int, default=None,
                      help='Batch size')
    parser.add_argument('--lr', type=float, default=None,
                      help='Learning rate (overrides config)')
    parser.add_argument('--resume', type=str, default=None,
                      help='Path to checkpoint to resume from')
    
    args = parser.parse_args()
    
    # Load config
    with open(args.config) as f:
        config = yaml.safe_load(f)
    
    # Override config with command line args
    if args.lr is not None:
        config['lr'] = args.lr
    if args.batch_size is not None:
        config['batch_size'] = args.batch_size
        
    num_epochs = args.num_epochs if args.num_epochs is not None else config.get('epoch', 100)
    
    print("\n" + "="*60)
    print("TAB ESTIMATOR - TRAINING (HIGH PERFORMANCE GPU MODE)")
    print("="*60)
    print("\nConfiguration:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    print("="*60 + "\n")
    
    # Check if NPZ files exist
    npz_files = glob.glob(os.path.join(args.data_dir, '*.npz'))
    if len(npz_files) == 0:
        print(f"❌ ERROR: No NPZ files found in {args.data_dir}")
        print("Please run preprocessing first to convert JAMS files to NPZ format")
        return
    
    print(f"Found {len(npz_files)} NPZ files in {args.data_dir}\n")
    
    # Get device
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    # Create trainer
    trainer = TabTrainer(config, device=device)
    
    # Load checkpoint if provided
    if args.resume:
        trainer.load_checkpoint(args.resume)
    
    # Get data loaders
    train_loader, val_loader = get_data_loaders(
        args.data_dir,
        batch_size=config['batch_size'],
        train_ratio=config.get('train_ratio', 0.8),
        num_workers=config.get('n_cores', 0)  # Safe multithreading setup
    )
    
    # Train
    trainer.train(
        train_loader, val_loader,
        num_epochs=num_epochs,
        model_dir=args.model_dir,
        tb_dir=args.tb_dir
    )


if __name__ == '__main__':
    main()