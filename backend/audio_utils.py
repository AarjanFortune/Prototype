"""Audio processing utilities."""
import numpy as np
import librosa
import soundfile as sf
from typing import Tuple
from config import SAMPLE_RATE, MAX_AUDIO_DURATION


def log_terminal(msg: str, is_error: bool = False):
    """Print directly to terminal standard output (no log files created)."""
    prefix = "\033[91m[AUDIO_UTILS ERROR]\033[0m" if is_error else "\033[92m[AUDIO_UTILS]\033[0m"
    print(f"{prefix} {msg}", flush=True)


def load_audio(file_path: str, sr: int = SAMPLE_RATE, mono: bool = True) -> Tuple[np.ndarray, int]:
    """Load audio file safely."""
    audio, sr = librosa.load(file_path, sr=sr, mono=mono)
    return audio, sr


def validate_audio_duration(audio: np.ndarray, sr: int) -> bool:
    """Check if audio duration is within limits."""
    duration = len(audio) / sr
    return duration <= MAX_AUDIO_DURATION


def extract_cqt_features(audio: np.ndarray, sr: int = SAMPLE_RATE, n_bins: int = 192, 
                         hop_length: int = 512) -> np.ndarray:
    """Extract Constant-Q Transform (CQT) features safely."""
    bins_per_octave = 24
    fmin = 82.41  # Low E string (E2)
    
    min_samples = hop_length * 4
    if len(audio) < min_samples:
        audio = np.pad(audio, (0, min_samples - len(audio)), mode='constant')

    cqt = librosa.cqt(audio, sr=sr, hop_length=hop_length, 
                      fmin=fmin, n_bins=n_bins, bins_per_octave=bins_per_octave)
    cqt_db = librosa.power_to_db(np.abs(cqt) ** 2, ref=np.max)
    
    cqt_normalized = (cqt_db - cqt_db.min()) / (cqt_db.max() - cqt_db.min() + 1e-8)
    return cqt_normalized.T


def extract_mel_features(audio: np.ndarray, sr: int = SAMPLE_RATE, 
                        hop_length: int = 512, n_mels: int = 128) -> np.ndarray:
    """Extract Mel-spectrogram features safely."""
    min_samples = hop_length * 4
    if len(audio) < min_samples:
        audio = np.pad(audio, (0, min_samples - len(audio)), mode='constant')

    mel_spec = librosa.feature.melspectrogram(y=audio, sr=sr, n_mels=n_mels, 
                                              hop_length=hop_length)
    mel_db = librosa.power_to_db(mel_spec, ref=np.max)
    
    mel_normalized = (mel_db - mel_db.min()) / (mel_db.max() - mel_db.min() + 1e-8)
    return mel_normalized.T


def estimate_tempo(audio: np.ndarray, sr: int = SAMPLE_RATE) -> float:
    """Estimate tempo (BPM) from audio."""
    try:
        onset_env = librosa.onset.onset_strength(y=audio, sr=sr)
        tempo = librosa.tempo(onset_env=onset_env, sr=sr)[0]
        return float(max(60, min(tempo, 200)))
    except Exception:
        return 120.0


def process_audio_file(file_path: str, feature_type: str = "cqt") -> Tuple[np.ndarray, dict]:
    """Process audio file and extract features."""
    audio, sr = load_audio(file_path)
    
    if not validate_audio_duration(audio, sr):
        raise ValueError(f"Audio duration exceeds {MAX_AUDIO_DURATION} seconds")
    
    if feature_type.lower() == "cqt":
        features = extract_cqt_features(audio, sr)
    elif feature_type.lower() == "mel":
        features = extract_mel_features(audio, sr)
    else:
        raise ValueError(f"Unknown feature type: {feature_type}")
    
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
    sf.write(file_path, audio_chunk, sr)


def get_chunk_from_audio(audio: np.ndarray, start_frame: int, chunk_frames: int) -> np.ndarray:
    end_frame = min(start_frame + chunk_frames, len(audio))
    return audio[start_frame:end_frame]
