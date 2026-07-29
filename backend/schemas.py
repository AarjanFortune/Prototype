"""API request and response schemas."""
from typing import Literal, Optional

from pydantic import BaseModel


class TranscriptionRequest(BaseModel):
    feature_type: str = "cqt"


class YouTubeTranscriptionRequest(TranscriptionRequest):
    url: str


class SourceMetadata(BaseModel):
    kind: Literal["upload", "youtube"]
    name: str
    size_bytes: int
    url: Optional[str] = None


class TranscriptionResponse(BaseModel):
    status: str
    source: Optional[SourceMetadata] = None
    tab: Optional[list] = None
    pitch: Optional[list] = None
    confidence: Optional[list] = None
    pianoroll: Optional[dict] = None
    metadata: Optional[dict] = None
    audio_url: Optional[str] = None
    error: Optional[str] = None
