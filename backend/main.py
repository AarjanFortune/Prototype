"""FastAPI application for Guitarica transcription."""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import certifi
import numpy as np
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from audio_utils import extract_cqt_features
from config import (
    API_HOST,
    API_PORT,
    CHUNK_SIZE,
    CORS_ORIGINS,
    SAMPLE_RATE,
    TEMP_DIR,
    UPLOADS_DIR,
)
from inference_pipeline import create_inference_pipeline
from schemas import TranscriptionResponse, YouTubeTranscriptionRequest
from transcription_service import audio_static_url, transcribe_audio_file
from youtube_service import YouTubeUrlError, download_youtube_audio


os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

ALLOWED_UPLOAD_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac"}

app = FastAPI(
    title="Guitarica API",
    description="Guitar audio transcription API",
    version="1.0.0",
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

inference_pipeline = create_inference_pipeline()


@app.get("/health")
async def health_check() -> dict:
    return {
        "status": "ok",
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "model_loaded": True,
    }


@app.post("/api/transcribe/upload", response_model=TranscriptionResponse)
async def transcribe_upload(
    file: UploadFile = File(...),
    feature_type: str = "cqt",
) -> TranscriptionResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_UPLOAD_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Unsupported file format. Allowed: {allowed}")

    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(delete=False, suffix=suffix, dir=UPLOADS_DIR, prefix="upload_") as output:
            temp_path = Path(output.name)
            output.write(await file.read())

        result = transcribe_audio_file(str(temp_path), feature_type, inference_pipeline)
        return TranscriptionResponse(status="success", **result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


@app.post("/api/transcribe/youtube", response_model=TranscriptionResponse)
async def transcribe_youtube(request: YouTubeTranscriptionRequest) -> TranscriptionResponse:
    try:
        audio_file = download_youtube_audio(request.url)
        result = transcribe_audio_file(audio_file, request.feature_type, inference_pipeline)
        return TranscriptionResponse(
            status="success",
            audio_url=audio_static_url(audio_file),
            **result,
        )
    except YouTubeUrlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str) -> None:
        self.active_connections.pop(client_id, None)

    async def send_personal(self, client_id: str, data: dict) -> None:
        connection = self.active_connections.get(client_id)
        if connection:
            await connection.send_json(data)


manager = ConnectionManager()


@app.websocket("/ws/stream/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str) -> None:
    await manager.connect(websocket, client_id)
    audio_buffer: list[float] = []
    sample_count = 0

    try:
        while True:
            message = json.loads(await websocket.receive_text())

            if message.get("type") == "audio_chunk":
                audio_chunk = np.array(message.get("data", []), dtype=np.float32)
                if len(audio_chunk) == 0:
                    continue

                audio_buffer.extend(audio_chunk)
                sample_count += len(audio_chunk)

                if sample_count >= CHUNK_SIZE:
                    audio_array = np.array(audio_buffer[:CHUNK_SIZE], dtype=np.float32)
                    features = extract_cqt_features(audio_array, SAMPLE_RATE)
                    predictions = inference_pipeline.transcribe_chunk(features, message.get("tempo", 120.0))

                    await manager.send_personal(client_id, {
                        "type": "transcription",
                        "tab": predictions.get("tab", []),
                        "confidence": predictions.get("confidence", []),
                        "n_frames": predictions.get("n_frames", 0),
                    })

                    audio_buffer = audio_buffer[CHUNK_SIZE:]
                    sample_count -= CHUNK_SIZE

            elif message.get("type") == "finish":
                if audio_buffer:
                    audio_array = np.array(audio_buffer, dtype=np.float32)
                    features = extract_cqt_features(audio_array, SAMPLE_RATE)
                    predictions = inference_pipeline.transcribe_chunk(features, message.get("tempo", 120.0))

                    await manager.send_personal(client_id, {
                        "type": "transcription_final",
                        "tab": predictions.get("tab", []),
                        "confidence": predictions.get("confidence", []),
                        "n_frames": predictions.get("n_frames", 0),
                    })

                await manager.send_personal(client_id, {"type": "done"})
                break

            elif message.get("type") == "ping":
                await manager.send_personal(client_id, {"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as exc:
        await manager.send_personal(client_id, {"type": "error", "error": str(exc)})
        manager.disconnect(client_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=False)
