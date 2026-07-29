"""Replaceable inference boundary for transcription workflows."""
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from config import HOP_LENGTH, MODEL_CONFIG, SAMPLE_RATE
from model_utils import (
    ModelInference,
    format_pianoroll_for_display,
    format_tab_for_display,
    tab_to_pitch,
)


class InferenceBackend(Protocol):
    def predict(self, features: np.ndarray, tempo: float = 120.0) -> dict:
        ...

    def predict_chunk(self, features: np.ndarray, tempo: float = 120.0) -> dict:
        ...


@dataclass
class InferencePipeline:
    """Model-agnostic transcription pipeline.

    The API and audio services call this wrapper instead of importing the model
    architecture directly. Replacing the model should require a new backend
    implementation plus a configuration change.
    """

    backend: InferenceBackend
    hop_length: int = HOP_LENGTH
    sample_rate: int = SAMPLE_RATE

    def transcribe(self, features: np.ndarray, tempo: float) -> dict:
        predictions = self.backend.predict(features, tempo)
        return self._format_predictions(predictions)

    def transcribe_chunk(self, features: np.ndarray, tempo: float) -> dict:
        return self.backend.predict_chunk(features, tempo)

    def _format_predictions(self, predictions: dict) -> dict:
        if "tab" not in predictions:
            return predictions

        tab_pred = np.array(predictions["tab"])
        return {
            "tab": format_tab_for_display(tab_pred),
            "pitch": tab_to_pitch(tab_pred).tolist(),
            "confidence": predictions.get("confidence", []),
            "pianoroll": format_pianoroll_for_display(
                tab_pred,
                hop_length=self.hop_length,
                sr=self.sample_rate,
            ),
        }


def create_inference_pipeline() -> InferencePipeline:
    return InferencePipeline(backend=ModelInference(config=MODEL_CONFIG))
