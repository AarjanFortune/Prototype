"""Audio processing utilities"""
import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
from typing import Tuple, Optional
import yt_dlp
from config import SAMPLE_RATE, MAX_AUDIO_DURATION, TEMP_DIR


def load_audio(file_path: str, sr: int = SAMPLE_RATE, mono: bool = True) -> Tuple[np.ndarray, int]:
    """Load audio file."""
    audio, sr = librosa.load(file_path, sr=sr, mono=mono)
    return audio, sr


def download_youtube_audio(url: str) -> str:
    """Download audio from YouTube URL."""
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': str(TEMP_DIR / '%(id)s'),
            'quiet': False,
            'no_warnings': False,
            'socket_timeout': 30,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_file = TEMP_DIR / f"{info['id']}.mp3"
            return str(audio_file)
    except Exception as e:
        raise ValueError(f"Failed to download YouTube video: {str(e)}")


def validate_audio_duration(audio: np.ndarray, sr: int) -> bool:
    """Check if audio duration is within limits."""
    duration = len(audio) / sr
    return duration <= MAX_AUDIO_DURATION


def extract_cqt_features(audio: np.ndarray, sr: int = SAMPLE_RATE, n_bins: int = 192, 
                         hop_length: int = 512) -> np.ndarray:
    """
    Extract Constant-Q Transform (CQT) features from audio.
    
    Returns:
        features: (n_frames, n_bins) array
    """
    # CQT: 24 bins per octave for guitar resolution (~82 Hz to 5 kHz)
    # n_bins = 192 with 24 bins/octave = 8 octaves (82 Hz to ~5 kHz)
    bins_per_octave = 24
    fmin = 82.41  # Low E string (E2)
    print("entered here")
    
    cqt = librosa.cqt(audio, sr=sr, hop_length=hop_length, 
                      fmin=fmin, n_bins=n_bins, bins_per_octave=bins_per_octave)
    print("if error generated")
    cqt_db = librosa.power_to_db(np.abs(cqt) ** 2, ref=np.max)
    
    # Normalize to [0, 1]
    cqt_normalized = (cqt_db - cqt_db.min()) / (cqt_db.max() - cqt_db.min() + 1e-8)
    
    return cqt_normalized.T  # (n_frames, n_bins)


def extract_mel_features(audio: np.ndarray, sr: int = SAMPLE_RATE, 
                        hop_length: int = 512, n_mels: int = 128) -> np.ndarray:
    """
    Extract Mel-spectrogram features from audio.
    
    Returns:
        features: (n_frames, n_mels) array
    """
    mel_spec = librosa.feature.melspectrogram(y=audio, sr=sr, n_mels=n_mels, 
                                              hop_length=hop_length)
    mel_db = librosa.power_to_db(mel_spec, ref=np.max)
    
    # Normalize to [0, 1]
    mel_normalized = (mel_db - mel_db.min()) / (mel_db.max() - mel_db.min() + 1e-8)
    
    return mel_normalized.T  # (n_frames, n_mels)


def estimate_tempo(audio: np.ndarray, sr: int = SAMPLE_RATE) -> float:
    """Estimate tempo (BPM) from audio."""
    try:
        onset_env = librosa.onset.onset_strength(y=audio, sr=sr)
        tempo = librosa.tempo(onset_env=onset_env, sr=sr)[0]
        return float(max(60, min(tempo, 200)))  # Clamp between 60-200 BPM
    except:
        return 120.0  # Default BPM


def process_audio_file(file_path: str, feature_type: str = "cqt") -> Tuple[np.ndarray, dict]:
    """
    Process audio file and extract features.
    
    Returns:
        features: (n_frames, n_bins) array
        metadata: dict with audio info
    """
    # Load audio
    audio, sr = load_audio(file_path)
    
    # Validate duration
    if not validate_audio_duration(audio, sr):
        raise ValueError(f"Audio duration exceeds {MAX_AUDIO_DURATION} seconds")
    
    # Extract features
    if feature_type.lower() == "cqt":
        features = extract_cqt_features(audio, sr)
    elif feature_type.lower() == "mel":
        features = extract_mel_features(audio, sr)
    else:
        raise ValueError(f"Unknown feature type: {feature_type}")
    
    # Estimate tempo
    tempo = estimate_tempo(audio, sr)
    
    metadata = {
        "duration": len(audio) / sr,
        "sample_rate": sr,
        "n_frames": features.shape[0],
        "tempo": tempo,
        "feature_type": feature_type,
    }
    
    return features, metadata


def save_audio_chunk(audio_chunk: np.ndarray, file_path: str, sr: int = SAMPLE_RATE):
    """Save audio chunk to file."""
    sf.write(file_path, audio_chunk, sr)


def get_chunk_from_audio(audio: np.ndarray, start_frame: int, chunk_frames: int) -> np.ndarray:
    """Extract a chunk from audio."""
    end_frame = min(start_frame + chunk_frames, len(audio))
    return audio[start_frame:end_frame]
