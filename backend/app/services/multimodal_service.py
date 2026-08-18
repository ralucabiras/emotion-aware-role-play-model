import asyncio
import io
import json
import math
from pathlib import Path
from threading import Lock
from time import perf_counter

from app.models.domain import Role, Session


def format_context(session: Session, message: str) -> str:
    previous = session.turns[-3:]
    segments = [
        f"[{'same speaker' if turn.role == Role.USER else 'other speaker'}] {turn.content}"
        for turn in previous
    ]
    segments.append(f"[target] {message}")
    return "\n".join(segments)


class MultimodalInferenceUnavailable(RuntimeError):
    pass


def confidence_level(confidence: float, low_threshold: float) -> str:
    if not 0 < low_threshold < 1:
        raise ValueError("Low-confidence threshold must be between 0 and 1")
    return "low" if confidence < low_threshold else "moderate" if confidence < 0.75 else "high"


class MultimodalAffectService:
    version = "iemocap-benchmark4-final-v1"

    def __init__(
        self,
        enabled: bool,
        text_model_dir: str,
        audio_model_dir: str,
        config_path: str,
        device: str = "auto",
        max_audio_bytes: int = 5_000_000,
        low_confidence_threshold: float = 0.55,
    ) -> None:
        self.enabled = enabled
        self.text_model_dir = Path(text_model_dir) if text_model_dir else None
        self.audio_model_dir = Path(audio_model_dir) if audio_model_dir else None
        self.config_path = Path(config_path)
        self.device_name = device
        self.max_audio_bytes = max_audio_bytes
        confidence_level(0.5, low_confidence_threshold)
        self.low_confidence_threshold = low_confidence_threshold
        self._loaded = False
        self._lock = Lock()
        self._inference_lock = asyncio.Lock()
        self._status = "unloaded"

    @property
    def available(self) -> bool:
        return bool(
            self.enabled
            and self.text_model_dir
            and self.audio_model_dir
            and self.text_model_dir.is_dir()
            and self.audio_model_dir.is_dir()
            and self.config_path.is_file()
        )

    @property
    def status(self) -> str:
        return self._status if self.available else "unavailable"

    async def analyze(self, session: Session, message: str, audio: bytes) -> dict:
        if not self.available:
            raise MultimodalInferenceUnavailable("Multimodal inference is not configured")
        if not audio or len(audio) > self.max_audio_bytes:
            raise ValueError("Audio must be a non-empty WAV file within the configured size limit")
        queued = perf_counter()
        async with self._inference_lock:
            queue_ms = int((perf_counter() - queued) * 1000)
            return await asyncio.to_thread(
                self._analyze_sync, format_context(session, message), audio, queue_ms
            )

    def _load(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            self._status = "loading"
            try:
                import torch
                from transformers import (
                    AutoFeatureExtractor,
                    AutoModelForAudioClassification,
                    AutoModelForSequenceClassification,
                    AutoTokenizer,
                )

                self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
                self.labels = self.config["labels"]
                self.calibration = self.config["calibration"]
                self.device = torch.device(
                    "cuda" if self.device_name == "auto" and torch.cuda.is_available() else
                    "cpu" if self.device_name == "auto" else self.device_name
                )
                self.tokenizer = AutoTokenizer.from_pretrained(self.text_model_dir)
                self.text_model = AutoModelForSequenceClassification.from_pretrained(
                    self.text_model_dir
                ).to(self.device).eval()
                self.extractor = AutoFeatureExtractor.from_pretrained(self.audio_model_dir)
                self.audio_model = AutoModelForAudioClassification.from_pretrained(
                    self.audio_model_dir
                ).to(self.device).eval()
                self._loaded = True
                self._status = "ready"
            except Exception:
                self._status = "error"
                raise

    def _analyze_sync(self, context: str, audio: bytes, queue_ms: int = 0) -> dict:
        import numpy as np
        import soundfile as sf
        import torch
        from scipy.signal import resample_poly

        started = perf_counter()
        self._load()
        waveform, rate = sf.read(io.BytesIO(audio), dtype="float32", always_2d=False)
        if waveform.ndim != 1:
            waveform = waveform.mean(axis=1)
        duration = len(waveform) / rate if rate else 0
        if duration < 0.25 or duration > 35:
            raise ValueError("Audio duration must be between 0.25 and 35 seconds")
        target_rate = self.config["audio"]["sampling_rate"]
        if rate != target_rate:
            divisor = math.gcd(rate, target_rate)
            waveform = resample_poly(
                waveform, target_rate // divisor, rate // divisor
            ).astype(np.float32)
        maximum = round(
            self.config["audio"]["maximum_duration_seconds"] * target_rate
        )
        text_inputs = self.tokenizer(
            context,
            truncation=True,
            max_length=self.config["text"]["max_length"],
            return_tensors="pt",
        ).to(self.device)
        audio_inputs = self.extractor(
            waveform[:maximum], sampling_rate=target_rate, return_tensors="pt"
        )
        audio_inputs = {key: value.to(self.device) for key, value in audio_inputs.items()}
        with torch.inference_mode():
            text_logits = self.text_model(**text_inputs).logits.float()
            audio_logits = self.audio_model(**audio_inputs).logits.float()
            text_probabilities = torch.softmax(
                text_logits / self.calibration["text_temperature"], dim=-1
            )
            audio_probabilities = torch.softmax(
                audio_logits / self.calibration["audio_temperature"], dim=-1
            )
            fused = (
                self.calibration["text_weight"] * text_probabilities
                + self.calibration["audio_weight"] * audio_probabilities
            )
            probabilities = torch.softmax(
                torch.log(fused.clamp_min(1e-12))
                / self.calibration["fusion_temperature"],
                dim=-1,
            )[0].cpu().numpy()
        text_values = text_probabilities[0].cpu().numpy()
        audio_values = audio_probabilities[0].cpu().numpy()
        index = int(probabilities.argmax())
        text_index, audio_index = int(text_values.argmax()), int(audio_values.argmax())
        confidence = float(probabilities[index])
        return {
            "label": self.labels[index],
            "confidence": confidence,
            "distribution": {
                label: float(probabilities[position])
                for position, label in enumerate(self.labels)
            },
            "text_label": self.labels[text_index],
            "text_confidence": float(text_values[text_index]),
            "text_distribution": {
                label: float(text_values[position])
                for position, label in enumerate(self.labels)
            },
            "audio_label": self.labels[audio_index],
            "audio_confidence": float(audio_values[audio_index]),
            "audio_distribution": {
                label: float(audio_values[position])
                for position, label in enumerate(self.labels)
            },
            "modalities_agree": text_index == audio_index,
            "confidence_level": confidence_level(
                confidence, self.low_confidence_threshold
            ),
            "low_confidence_threshold": self.low_confidence_threshold,
            "model_version": self.version,
            "latency_ms": int((perf_counter() - started) * 1000),
            "queue_ms": queue_ms,
            "audio_persisted": False,
        }
