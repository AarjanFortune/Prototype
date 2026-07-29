"""Shared transcription use cases."""
from pathlib import Path

from audio_utils import process_audio_file
from inference_pipeline import InferencePipeline


def transcribe_audio_file(
    file_path: str,
    feature_type: str,
    pipeline: InferencePipeline,
) -> dict:
    features, metadata = process_audio_file(file_path, feature_type)
    result = pipeline.transcribe(features, metadata["tempo"])
    return {**result, "metadata": metadata}


def audio_static_url(file_path: str) -> str:
    path = Path(file_path)
    temp_index = path.parts.index("temp") if "temp" in path.parts else -1
    if temp_index >= 0:
        relative = Path(*path.parts[temp_index + 1 :]).as_posix()
        return f"/audio/{relative}"
    return f"/audio/{path.name}"
