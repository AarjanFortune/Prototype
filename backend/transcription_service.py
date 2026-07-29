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
    _align_pianoroll_timing(result, metadata["duration"])
    return {**result, "metadata": metadata}


def _align_pianoroll_timing(result: dict, audio_duration: float) -> None:
    pianoroll = result.get("pianoroll")
    if not isinstance(pianoroll, dict):
        return

    model_duration = float(pianoroll.get("total_duration") or 0)
    if model_duration <= 0 or audio_duration <= 0:
        return

    time_scale = audio_duration / model_duration
    for note in pianoroll.get("notes", []):
        note["start_time"] = float(note["start_time"]) * time_scale
        note["duration"] = float(note["duration"]) * time_scale
    pianoroll["total_duration"] = audio_duration


def audio_static_url(file_path: str) -> str:
    path = Path(file_path)
    temp_index = path.parts.index("temp") if "temp" in path.parts else -1
    if temp_index >= 0:
        relative = Path(*path.parts[temp_index + 1 :]).as_posix()
        return f"/audio/{relative}"
    return f"/audio/{path.name}"
