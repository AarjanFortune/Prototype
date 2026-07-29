"""API request and response schemas."""
from typing import Optional

from pydantic import BaseModel


class TranscriptionRequest(BaseModel):
    feature_type: str = "cqt"


class YouTubeTranscriptionRequest(TranscriptionRequest):
    url: str


class TranscriptionResponse(BaseModel):
    status: str
    tab: Optional[list] = None
    pitch: Optional[list] = None
    confidence: Optional[list] = None
    pianoroll: Optional[dict] = None
    metadata: Optional[dict] = None
    audio_url: Optional[str] = None
    error: Optional[str] = None
