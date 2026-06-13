"""
Data preprocessing script
Convert JAMS annotations to NPZ format for training
"""

import argparse
import os
import glob
import yaml
from pathlib import Path
from tqdm import tqdm
from multiprocessing import Pool
from functools import partial

from data_utils_simplified import TabDataPreprocessor


def process_single_file(args_tuple):
    """Process a single JAMS-audio pair."""
    jam_path, audio_path, output_dir, config = args_tuple
    
    try:
        output_filename = os.path.basename(jam_path).replace('.jams', '.npz')
        output_path = os.path.join(output_dir, output_filename)
        
        TabDataPreprocessor.process_audio_jams_pair(
            audio_path=audio_path,
            jams_path=jam_path,
            output_npz_path=output_path,
            sr=config['down_sampling_rate'],
            n_bins=config['cqt_n_bins'],
            bins_per_octave=config['bins_per_octave'],
            hop_length=config['hop_length'],
            note_resolution=config['note_resolution']
        )
        return True, None
    except Exception as e:
        return False, str(e)


def preprocess_guitarset(jams_dir, audio_dir, output_dir, config_path, n_cores=4):
    """
    Preprocess GuitarSet JAMS annotations.
    
    Args:
        jams_dir: directory containing JAMS files
        audio_dir: directory containing audio files
        output_dir: where to save NPZ files
        config_path: path to config YAML
        n_cores: number of processes
    """
    # Load config
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all JAMS files
    jams_files = sorted(glob.glob(os.path.join(jams_dir, '*.jams')))
    
    print(f"Found {len(jams_files)} JAMS files")
    
    if len(jams_files) == 0:
        print(f"❌ No JAMS files found in {jams_dir}")
        return
    
    # Match with audio files
    print("Matching JAMS with audio files...")
    
    process_args = []
    successful = 0
    skipped = 0
    
    for jam_path in jams_files:
        # Construct audio path
        # GuitarSet convention: annotation file name -> audio file name
        jam_basename = os.path.basename(jam_path).replace('_comp.jams', '_mic.wav').replace('_solo.jams', '_mic.wav')
        audio_path = os.path.join(audio_dir, jam_basename)
        
        if not os.path.exists(audio_path):
            print(f"⚠ Audio not found for {jam_path}: {audio_path}")
            skipped += 1
            continue
        
        process_args.append((jam_path, audio_path, output_dir, config))
        successful += 1
    
    print(f"Will process {successful} files ({skipped} skipped)\n")
    
    if len(process_args) == 0:
        print("❌ No matching JAMS-audio pairs found")
        return
    
    # Process files
    print("Processing JAMS files...")
    with Pool(n_cores) as pool:
        results = list(tqdm(
            pool.imap_unordered(process_single_file, process_args),
            total=len(process_args)
        ))
    
    # Summary
    successful_count = sum(1 for success, _ in results if success)
    failed_count = len(results) - successful_count
    
    print(f"\n{'='*60}")
    print(f"Processing complete!")
    print(f"  Successful: {successful_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Output directory: {output_dir}")
    print(f"{'='*60}\n")
    
    if failed_count > 0:
        print("Failed files:")
        for i, (success, error) in enumerate(results):
            if not success:
                print(f"  {i}: {error}")


def main():
    parser = argparse.ArgumentParser(description='Preprocess GuitarSet data')
    parser.add_argument('--jams_dir', type=str, required=True,
                      help='Directory containing JAMS annotation files')
    parser.add_argument('--audio_dir', type=str, required=True,
                      help='Directory containing audio files')
    parser.add_argument('--output_dir', type=str, default='../data/npz',
                      help='Output directory for NPZ files')
    parser.add_argument('--config', type=str, default='config_simplified.yaml',
                      help='Path to config file')
    parser.add_argument('--n_cores', type=int, default=4,
                      help='Number of processes for parallel processing')
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("DATA PREPROCESSING - JAMS to NPZ")
    print("="*60)
    print(f"\nSettings:")
    print(f"  JAMS directory: {args.jams_dir}")
    print(f"  Audio directory: {args.audio_dir}")
    print(f"  Output directory: {args.output_dir}")
    print(f"  Config file: {args.config}")
    print(f"  Cores: {args.n_cores}")
    print("="*60 + "\n")
    
    # Check directories
    if not os.path.exists(args.jams_dir):
        print(f"❌ ERROR: JAMS directory not found: {args.jams_dir}")
        return
    
    if not os.path.exists(args.audio_dir):
        print(f"❌ ERROR: Audio directory not found: {args.audio_dir}")
        return
    
    if not os.path.exists(args.config):
        print(f"❌ ERROR: Config file not found: {args.config}")
        return
    
    # Run preprocessing
    preprocess_guitarset(
        jams_dir=args.jams_dir,
        audio_dir=args.audio_dir,
        output_dir=args.output_dir,
        config_path=args.config,
        n_cores=args.n_cores
    )


if __name__ == '__main__':
    main()
