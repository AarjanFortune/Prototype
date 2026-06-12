# 🎸 Guitar Transcription Web App

A modern, full-stack web application for automatic guitar music transcription using AI. Convert audio to guitar tablature in real-time using a neural network model.

## ✨ Features

- **📁 Upload Audio Files**: Support for .mp3, .wav, .flac, .ogg, .m4a
- **🎬 YouTube Integration**: Transcribe directly from YouTube videos
- **🎙️ Live Real-time Streaming**: Generate tabs while playing live (via microphone)
- **📊 Multiple Feature Types**: CQT (Constant-Q Transform) and Mel-Spectrogram
- **🎯 High Accuracy**: Deep learning model based on TabEstimator (Conformer architecture)
- **💾 Instant Results**: Fast inference with GPU support

## 🏗️ Architecture

```
guitar-transcription-webapp/
├── backend/                 # FastAPI Python backend
│   ├── main.py             # FastAPI application
│   ├── model_utils.py      # Model inference wrapper
│   ├── audio_utils.py      # Audio processing utilities
│   ├── config.py           # Configuration settings
│   └── requirements.txt    # Python dependencies
│
└── frontend/               # React + TypeScript frontend
    ├── src/
    │   ├── App.tsx         # Main app component
    │   ├── components/     # React components
    │   │   ├── Header.tsx
    │   │   ├── Navigation.tsx
    │   │   ├── TabViewer.tsx
    │   │   ├── LoadingSpinner.tsx
    │   │   └── tabs/       # Tab-specific components
    │   │       ├── UploadTab.tsx
    │   │       ├── YouTubeTab.tsx
    │   │       └── LiveStreamTab.tsx
    │   └── main.tsx
    ├── vite.config.ts      # Vite configuration
    ├── package.json
    └── index.html
```

## 📋 Quick Start

### Prerequisites

- **Python 3.8+** with pip
- **Node.js 16+** with npm
- **FFmpeg** (for YouTube audio extraction)

### Installation

#### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

### Running the Application

#### Terminal 1: Start Backend

```bash
cd backend
source venv/bin/activate  # Activate virtual environment
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`

#### Terminal 2: Start Frontend

```bash
cd frontend
npm run dev
```

Frontend will be available at: `http://localhost:5173`

## 🚀 Usage

### 1. Upload Audio File
1. Navigate to "📁 Upload File" tab
2. Select your audio file (mp3, wav, etc.)
3. Choose feature type (CQT or Mel-Spectrogram)
4. Click "🎵 Transcribe"
5. View generated tablature

### 2. YouTube Transcription
1. Navigate to "🎬 YouTube Link" tab
2. Paste a YouTube URL
3. Click "🎬 Transcribe YouTube"
4. Wait for download and processing
5. View tablature results

### 3. Live Real-time Recording
1. Navigate to "🎙️ Live Stream" tab
2. Set your BPM (tempo)
3. Click "🔴 Start Recording"
4. Play guitar - tabs generate in real-time
5. Click "⏹️ Stop Recording" when done

## 🔧 Configuration

Edit `backend/config.py` to customize:

```python
# Audio Processing
SAMPLE_RATE = 22050              # Sample rate for audio
HOP_LENGTH = 512                 # Hop length for features
N_BINS = 192                     # CQT bins (24 per octave)
MAX_AUDIO_DURATION = 600         # Max 10 minutes

# Model
MODEL_CONFIG = {
    "mode": "tab",               # tab or F0
    "encoder_type": "conformer", # conformer or transformer
    "use_conv_stack": True,
    "n_bins": N_BINS,
}

# API
API_HOST = "0.0.0.0"
API_PORT = 8000
CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]
```

## 🔌 API Endpoints

### Health Check
```
GET /health
```

### Upload Transcription
```
POST /api/transcribe/upload
Content-Type: multipart/form-data

Parameters:
- file: Audio file
- feature_type: "cqt" or "mel" (default: "cqt")

Response:
{
  "status": "success",
  "tab": ["E|...", "A|...", ...],
  "confidence": [[...], ...],
  "metadata": {...}
}
```

### YouTube Transcription
```
POST /api/transcribe/youtube
Content-Type: application/json

Body:
{
  "url": "https://www.youtube.com/watch?v=...",
  "feature_type": "cqt"
}
```

### Real-time WebSocket
```
WebSocket: /ws/stream/{client_id}

Send audio chunks:
{
  "type": "audio_chunk",
  "data": [float32_samples],
  "tempo": 120.0
}

Receive transcriptions:
{
  "type": "transcription",
  "tab": [[fret_predictions]],
  "confidence": [[confidence_scores]],
  "n_frames": number
}
```

### Feature Extraction
```
POST /api/features/extract
Content-Type: multipart/form-data

Parameters:
- file: Audio file
- feature_type: "cqt" or "mel"

Response:
{
  "status": "success",
  "features": [[...]],
  "shape": [n_frames, n_bins],
  "tempo": 120.0
}
```

## 📊 Tablature Format

```
E|0-1-3-5-7-5-3-1-0-
A|3-5-7-5-3-1-0------
D|----5-7-5-3-1-0---
G|----------5-7-5-3-
B|-------------------
e|-------------------
```

- **Numbers** = Fret positions (0-19)
- **"-"** = Open string or muted
- **Strings**: Top to bottom = High E, B, G, D, A, Low E (standard tuning)

## 🎯 Model Details

### Architecture
- **Encoder**: Conformer (Convolution-Augmented Transformer)
- **Feature Input**: CQT (192 bins, 24 per octave) or Mel-Spectrogram
- **Output**: 6 strings × 21 fret outputs per frame
- **Sample Rate**: 22,050 Hz
- **Hop Length**: 512 samples (~23ms per frame)

### Inference
- Processes 22,050 Hz audio
- Extracts CQT features (192 bins)
- Runs through Conformer encoder
- Outputs frame-level tablature predictions
- Confidence scores for each string prediction

## 📦 Dependencies

### Backend
- FastAPI: Web framework
- PyTorch: Deep learning
- Librosa: Audio processing
- yt-dlp: YouTube downloading
- NumPy/SciPy: Numerical computing

### Frontend
- React 18: UI framework
- TypeScript: Type safety
- Axios: HTTP client
- Vite: Build tool

## 🐳 Docker (Optional)

Build and run with Docker:

```bash
# Build images
docker-compose build

# Start services
docker-compose up
```

Access at: `http://localhost:5173`

## 🔄 Leveraged Tools

This app integrates utilities from:
- **amt-tools-master**: Audio feature extraction (CQT, Mel, STFT, VQT)
- **Refactor-TabEstimator**: Neural network model for tab prediction

## 🐛 Troubleshooting

### "Failed to access microphone"
- Ensure browser has microphone permissions
- Check microphone is connected and working

### "CORS error"
- Verify backend is running on `http://localhost:8000`
- Check CORS_ORIGINS in `backend/config.py`

### "Transcription is slow"
- Use GPU (CUDA): Install PyTorch with CUDA support
- Use CQT features instead of Mel (faster)
- Reduce audio duration

### "YouTube download fails"
- Ensure FFmpeg is installed
- Check internet connection
- Some videos may be blocked/unavailable

## 📝 Development

### Adding Custom Features

1. **New Audio Feature Type**:
   - Add extraction function in `backend/audio_utils.py`
   - Update `process_audio_file()` function

2. **Custom Model**:
   - Modify `TabEstimator` class in `backend/model_utils.py`
   - Update model config in `backend/config.py`

3. **UI Enhancements**:
   - Add components in `frontend/src/components/`
   - Update styles with corresponding `.css` files

## 📄 License

MIT License - See repository for details

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📧 Support

For issues or questions:
- Check existing GitHub issues
- Create a new issue with details
- Include error messages and steps to reproduce

---

**Built with ❤️ for guitar enthusiasts and AI researchers**
