"""FastAPI application for Guitar Transcription Web App"""
import os
import ssl
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

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
    CORS_ORIGINS, API_HOST, API_PORT, UPLOADS_DIR, TEMP_DIR,
    SAMPLE_RATE, CHUNK_DURATION, CHUNK_SIZE, HOP_LENGTH
)
from audio_utils import (
    process_audio_file, download_youtube_audio, 
    load_audio, extract_cqt_features, estimate_tempo,
    log_terminal
)
from model_utils import ModelInference, tab_to_pitch, format_tab_for_display, format_pianoroll_for_display


app = FastAPI(
    title="Guitar Transcription API",
    description="Automatic guitar music transcription using neural networks",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/audio", StaticFiles(directory=str(TEMP_DIR)), name="audio")

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
    feature_type: str = "cqt"


class YouTubeTranscriptionRequest(BaseModel):
    url: str
    feature_type: str = "cqt"


class TranscriptionResponse(BaseModel):
    status: str
    tab: Optional[list] = None
    pitch: Optional[list] = None
    confidence: Optional[list] = None
    pianoroll: Optional[dict] = None
    metadata: Optional[dict] = None
    audio_url: Optional[str] = None
    error: Optional[str] = None


# ==================== Endpoints ====================

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "model_loaded": True,
    }


@app.post("/api/transcribe/upload", response_model=TranscriptionResponse)
async def transcribe_upload(
    file: UploadFile = File(...),
    feature_type: str = "cqt"
):
    file_path = None
    try:
        allowed_extensions = {'.mp3', '.wav', '.flac', '.ogg', '.m4a'}
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
            )
        
        file_path = UPLOADS_DIR / f"upload_{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        features, metadata = process_audio_file(str(file_path), feature_type)
        predictions = model_inference.predict(features, metadata['tempo'])
        
        tab_pred = np.array(predictions['tab'])
        pitch = tab_to_pitch(tab_pred)
        tab_display = format_tab_for_display(tab_pred)
        pianoroll_data = format_pianoroll_for_display(tab_pred, hop_length=HOP_LENGTH, sr=SAMPLE_RATE)
        
        return TranscriptionResponse(
            status="success",
            tab=tab_display,
            pitch=pitch.tolist(),
            confidence=predictions['confidence'],
            pianoroll=pianoroll_data,
            metadata=metadata
        )
    
    except Exception as e:
        return TranscriptionResponse(status="error", error=str(e))
    
    finally:
        if file_path and file_path.exists():
            file_path.unlink()


@app.post("/api/transcribe/youtube", response_model=TranscriptionResponse)
async def transcribe_youtube(request: YouTubeTranscriptionRequest):
    try:
        audio_file = download_youtube_audio(request.url)
        
        features, metadata = process_audio_file(audio_file, request.feature_type)
        predictions = model_inference.predict(features, metadata['tempo'])
        
        tab_pred = np.array(predictions['tab'])
        pitch = tab_to_pitch(tab_pred)
        tab_display = format_tab_for_display(tab_pred)
        pianoroll_data = format_pianoroll_for_display(tab_pred, hop_length=HOP_LENGTH, sr=SAMPLE_RATE)

        filename = Path(audio_file).name
        audio_url = f"http://localhost:8000/audio/{filename}"
        
        return TranscriptionResponse(
            status="success",
            tab=tab_display,
            pitch=pitch.tolist(),
            confidence=predictions['confidence'],
            pianoroll=pianoroll_data,
            metadata=metadata,
            audio_url=audio_url
        )
    
    except Exception as e:
        return TranscriptionResponse(status="error", error=str(e))


# ==================== WebSocket Endpoint ====================

class ConnectionManager:
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
    await manager.connect(websocket, client_id)
    audio_buffer = []
    sample_count = 0
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "audio_chunk":
                audio_chunk = np.array(message.get("data", []), dtype=np.float32)
                tempo = message.get("tempo", 120.0)
                
                if len(audio_chunk) == 0:
                    continue
                
                audio_buffer.extend(audio_chunk)
                sample_count += len(audio_chunk)
                
                if sample_count >= CHUNK_SIZE:
                    audio_array = np.array(audio_buffer[:CHUNK_SIZE], dtype=np.float32)
                    features = extract_cqt_features(audio_array, SAMPLE_RATE)
                    predictions = model_inference.predict_chunk(features, tempo)
                    
                    await manager.send_personal(client_id, {
                        "type": "transcription",
                        "tab": predictions['tab'] if 'tab' in predictions else [],
                        "confidence": predictions.get('confidence', []),
                        "n_frames": predictions['n_frames'],
                    })
                    
                    audio_buffer = audio_buffer[CHUNK_SIZE:]
                    sample_count -= CHUNK_SIZE
            
            elif message.get("type") == "finish":
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
        await manager.send_personal(client_id, {"type": "error", "error": str(e)})
        manager.disconnect(client_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=False)