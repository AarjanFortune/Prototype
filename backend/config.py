import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
UPLOADS_DIR = BASE_DIR / "uploads"
MODELS_DIR = BASE_DIR / "models"
TEMP_DIR = BASE_DIR / "temp"

# Ensure directories exist
UPLOADS_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Audio Processing
SAMPLE_RATE = 44100
HOP_LENGTH = 512
N_BINS = 192  # CQT bins (24 bins/octave)
FRAME_LENGTH = (HOP_LENGTH / SAMPLE_RATE) * 1000  # in milliseconds (~23 ms)
MAX_AUDIO_DURATION = 600  # 10 minutes max

# Model Configuration
MODEL_CONFIG = {
    "mode": "tab",  # tab or F0
    "encoder_type": "conformer",  # conformer or transformer
    "use_conv_stack": True,
    "use_custom_decimation_func": True,
    "n_bins": N_BINS,
    "hop_length": HOP_LENGTH,
    "sr": SAMPLE_RATE,
}

# Guitar Tuning (standard)
GUITAR_TUNING = {
    0: 40,   # E1 (MIDI 40)
    1: 45,   # A1 (MIDI 45)
    2: 50,   # D2 (MIDI 50)
    3: 55,   # G2 (MIDI 55)
    4: 59,   # B2 (MIDI 59)
    5: 64,   # E3 (MIDI 64)
}

# Tablature Settings
MAX_FRET = 21  # outputs for fret prediction
N_STRINGS = 6
NOT_PLAYED_IDX = 20

# Real-time Settings
CHUNK_DURATION = 1.0  # seconds per chunk for real-time processing
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)

# API Settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

# Processing
BATCH_SIZE = 1
DEFAULT_BPM = 120.0
