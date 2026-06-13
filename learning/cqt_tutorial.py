import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import os

def learn_cqt(audio_path, output_image_path):
    print(f"1. Loading audio file: {audio_path}...")
    # Load the audio file
    # sr=None preserves the original sample rate. By default, librosa resamples to 22050 Hz.
    y, sr = librosa.load(audio_path, sr=22050)
    print(f"   Audio loaded! Sample rate: {sr} Hz, Total samples: {len(y)}")
    
    print("\n2. Computing the Constant-Q Transform (CQT)...")
    # Parameters for CQT (similar to what config.yaml in Tab-estimator uses)
    hop_length = 512        # Number of samples between successive CQT columns
    n_bins = 192            # Total number of frequency bins (e.g., 6 octaves * 24 bins)
    bins_per_octave = 24    # Resolutions per octave (24 is quarter-tone resolution)
    
    # Compute the CQT
    # librosa.cqt returns complex numbers (magnitude + phase)
    C = librosa.cqt(y, sr=sr, hop_length=hop_length, 
                    n_bins=n_bins, bins_per_octave=bins_per_octave)
    
    # We only care about the magnitude (loudness), not the phase
    C_mag = np.abs(C)
    
    # Convert magnitude to decibels (log scale) for better visualization
    # Our ears hear loudness logarithmically!
    C_db = librosa.amplitude_to_db(C_mag, ref=np.max)
    
    print(f"   CQT computed! Output shape: {C_db.shape}")
    print(f"   - {C_db.shape[0]} frequency bins")
    print(f"   - {C_db.shape[1]} time frames")

    print(f"\n3. Generating visualization...")
    # Set up the plot
    plt.figure(figsize=(12, 6))
    
    # Use librosa's specshow to plot the spectrogram
    # y_axis='cqt_hz' formats the Y-axis as frequencies
    # x_axis='time' formats the X-axis as seconds
    librosa.display.specshow(C_db, sr=sr, hop_length=hop_length, 
                             x_axis='time', y_axis='cqt_hz', 
                             bins_per_octave=bins_per_octave)
    
    plt.colorbar(format='%+2.0f dB')
    plt.title('Constant-Q Transform (CQT) Spectrogram')
    plt.tight_layout()
    
    # Save the plot
    plt.savefig(output_image_path)
    print(f"   Saved visualization to {output_image_path}")
    plt.close()

if __name__ == "__main__":
    # Define paths based on the learning folder
    folder = "/Users/aarjan/Desktop/Tab-estimator-master/learning"
    audio_file = os.path.join(folder, "00_BN1-129-Eb_comp_mic.wav")
    output_image = os.path.join(folder, "cqt_tutorial_plot.png")
    
    if os.path.exists(audio_file):
        learn_cqt(audio_file, output_image)
    else:
        print(f"Error: Could not find audio file at {audio_file}")
