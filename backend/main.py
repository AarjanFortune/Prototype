"""FastAPI application for Guitar Transcription Web App"""
import asyncio
import json
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import torch

from config import (
    CORS_ORIGINS, API_HOST, API_PORT, UPLOADS_DIR, 
    SAMPLE_RATE, CHUNK_DURATION, CHUNK_SIZE, HOP_LENGTH
)
from audio_utils import (
    process_audio_file, download_youtube_audio, 
    load_audio, extract_cqt_features, estimate_tempo
)
from model_utils import ModelInference, tab_to_pitch, format_tab_for_display, format_pianoroll_for_display


# Initialize FastAPI app
app = FastAPI(
    title="Guitar Transcription API",
    description="Automatic guitar music transcription using neural networks",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize model inference
model_inference = ModelInference(config={
    "mode": "tab",
    "encoder_type": "conformer",
    "use_conv_stack": True,
    "use_custom_decimation_func": True,
    "n_bins": 192,
    "hop_length": 512,
    "sr": SAMPLE_RATE,
})


# ==================== Request/Response Models ====================

class TranscriptionRequest(BaseModel):
    """Request model for transcription endpoint."""
    feature_type: str = "cqt"  # cqt or mel


class YouTubeTranscriptionRequest(BaseModel):
    """Request model for YouTube URL transcription."""
    url: str
    feature_type: str = "cqt"


class TranscriptionResponse(BaseModel):
    """Response model for transcription."""
    status: str
    tab: Optional[list] = None
    pitch: Optional[list] = None
    confidence: Optional[list] = None
    pianoroll: Optional[dict] = None
    metadata: Optional[dict] = None
    error: Optional[str] = None


# ==================== Health Check ====================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "model_loaded": True,
    }


# ==================== File Upload Endpoints ====================

@app.post("/api/transcribe/upload", response_model=TranscriptionResponse)
async def transcribe_upload(
    file: UploadFile = File(...),
    feature_type: str = "cqt"
):
    """
    Transcribe uploaded audio file.
    
    Supported formats: .mp3, .wav, .flac, .ogg
    """
    try:
        # Validate file type
        allowed_extensions = {'.mp3', '.wav', '.flac', '.ogg', '.m4a'}
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Save uploaded file
        file_path = UPLOADS_DIR / f"upload_{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Process and transcribe
        features, metadata = process_audio_file(str(file_path), feature_type)
        predictions = model_inference.predict(features, metadata['tempo'])
        
        # Convert to pitch
        tab_pred = np.array(predictions['tab'])
        pitch = tab_to_pitch(tab_pred)
        
        # Format for display
        tab_display = format_tab_for_display(tab_pred)
        
        # Generate pianoroll
        pianoroll_data = format_pianoroll_for_display(tab_pred, 
                                                      hop_length=HOP_LENGTH, 
                                                      sr=SAMPLE_RATE)
        
        return TranscriptionResponse(
            status="success",
            tab=tab_display,
            pitch=pitch.tolist(),
            confidence=predictions['confidence'],
            pianoroll=pianoroll_data,
            metadata=metadata
        )
    
    except Exception as e:
        return TranscriptionResponse(
            status="error",
            error=str(e)
        )
    
    finally:
        # Cleanup
        if file_path.exists():
            file_path.unlink()


@app.post("/api/transcribe/youtube", response_model=TranscriptionResponse)
async def transcribe_youtube(request: YouTubeTranscriptionRequest):
    """
    Transcribe audio from YouTube URL.
    
    Extracts audio, processes it, and returns tablature predictions.
    """
    audio_file = None
    try:
        # Download audio from YouTube
        audio_file = download_youtube_audio(request.url)
        
        # Process and transcribe
        features, metadata = process_audio_file(audio_file, request.feature_type)
        predictions = model_inference.predict(features, metadata['tempo'])
        
        # Convert to pitch
        tab_pred = np.array(predictions['tab'])
        pitch = tab_to_pitch(tab_pred)
        
        # Format for display
        tab_display = format_tab_for_display(tab_pred)
        
        # Generate pianoroll
        pianoroll_data = format_pianoroll_for_display(tab_pred, 
                                                      hop_length=HOP_LENGTH, 
                                                      sr=SAMPLE_RATE)
        
        return TranscriptionResponse(
            status="success",
            tab=tab_display,
            pitch=pitch.tolist(),
            confidence=predictions['confidence'],
            pianoroll=pianoroll_data,
            metadata=metadata
        )
    
    except Exception as e:
        return TranscriptionResponse(
            status="error",
            error=str(e)
        )
    
    finally:
        # Cleanup
        if audio_file and Path(audio_file).exists():
            Path(audio_file).unlink()


# ==================== WebSocket for Real-time Streaming ====================

class ConnectionManager:
    """Manages WebSocket connections for real-time transcription."""
    
    def __init__(self):
        self.active_connections: dict = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_personal(self, client_id: str, data: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(data)


manager = ConnectionManager()


@app.websocket("/ws/stream/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time audio streaming transcription.
    
    Protocol:
    - Client sends: {"type": "audio_chunk", "data": [audio_samples], "tempo": 120.0}
    - Server responds: {"type": "transcription", "tab": [...], "confidence": [...]}
    """
    await manager.connect(websocket, client_id)
    audio_buffer = []
    sample_count = 0
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "audio_chunk":
                # Get audio chunk
                audio_chunk = np.array(message.get("data", []), dtype=np.float32)
                tempo = message.get("tempo", 120.0)
                
                if len(audio_chunk) == 0:
                    continue
                
                # Buffer audio
                audio_buffer.extend(audio_chunk)
                sample_count += len(audio_chunk)
                
                # Process when we have enough samples for a chunk
                if sample_count >= CHUNK_SIZE:
                    # Convert to numpy array and extract features
                    audio_array = np.array(audio_buffer[:CHUNK_SIZE], dtype=np.float32)
                    features = extract_cqt_features(audio_array, SAMPLE_RATE)
                    
                    # Run inference
                    predictions = model_inference.predict_chunk(features, tempo)
                    
                    # Send predictions
                    await manager.send_personal(client_id, {
                        "type": "transcription",
                        "tab": predictions['tab'] if 'tab' in predictions else [],
                        "confidence": predictions.get('confidence', []),
                        "n_frames": predictions['n_frames'],
                    })
                    
                    # Remove processed samples
                    audio_buffer = audio_buffer[CHUNK_SIZE:]
                    sample_count -= CHUNK_SIZE
            
            elif message.get("type") == "finish":
                # Process remaining audio
                if audio_buffer:
                    audio_array = np.array(audio_buffer, dtype=np.float32)
                    features = extract_cqt_features(audio_array, SAMPLE_RATE)
                    predictions = model_inference.predict_chunk(features, message.get("tempo", 120.0))
                    
                    await manager.send_personal(client_id, {
                        "type": "transcription_final",
                        "tab": predictions['tab'] if 'tab' in predictions else [],
                        "confidence": predictions.get('confidence', []),
                        "n_frames": predictions['n_frames'],
                    })
                
                await manager.send_personal(client_id, {"type": "done"})
                break
            
            elif message.get("type") == "ping":
                await manager.send_personal(client_id, {"type": "pong"})
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        await manager.send_personal(client_id, {
            "type": "error",
            "error": str(e)
        })
        manager.disconnect(client_id)


# ==================== Features Endpoint ====================

@app.post("/api/features/extract")
async def extract_features(
    file: UploadFile = File(...),
    feature_type: str = "cqt"
):
    """Extract and return features for visualization."""
    try:
        # Save uploaded file
        file_path = UPLOADS_DIR / f"features_{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Load and extract features
        audio, sr = load_audio(str(file_path))
        
        if feature_type.lower() == "cqt":
            features = extract_cqt_features(audio, sr)
        else:
            from audio_utils import extract_mel_features
            features = extract_mel_features(audio, sr)
        
        tempo = estimate_tempo(audio, sr)
        
        return {
            "status": "success",
            "features": features.tolist(),
            "shape": features.shape,
            "tempo": tempo,
            "feature_type": feature_type,
        }
    
    except Exception as e:
        return {"status": "error", "error": str(e)}
    
    finally:
        if file_path.exists():
            file_path.unlink()


# ==================== Info Endpoints ====================

@app.get("/api/info")
async def get_info():
    """Get API and model information."""
    return {
        "app": "Guitar Transcription API",
        "version": "1.0.0",
        "model": "TabEstimator (Conformer-based)",
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "sample_rate": SAMPLE_RATE,
        "hop_length": 512,
        "n_bins": 192,
        "n_strings": 6,
        "supported_formats": ["mp3", "wav", "flac", "ogg", "m4a"],
        "features": {
            "upload": True,
            "youtube": True,
            "real_time_streaming": True,
            "feature_extraction": True,
        }
    }


# ==================== Main ====================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
        log_level="info"
    )
