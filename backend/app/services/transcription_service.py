import io
import wave
from dataclasses import dataclass
from time import perf_counter

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)


class TranscriptionUnavailable(RuntimeError):
    pass


class InvalidAudio(ValueError):
    pass


@dataclass
class TranscriptionResult:
    text: str
    model: str
    latency_ms: int
    audio_persisted: bool = False


class TranscriptionService:
    def __init__(self, enabled: bool, api_key: str | None, model: str, timeout: float, max_audio_bytes: int) -> None:
        self.enabled = enabled
        self.model = model
        self.max_audio_bytes = max_audio_bytes
        self.client = AsyncOpenAI(api_key=api_key, timeout=timeout) if enabled and api_key else None

    @property
    def available(self) -> bool:
        return self.client is not None

    async def transcribe(self, audio: bytes) -> TranscriptionResult:
        self._validate_wav(audio)
        if not self.client:
            raise TranscriptionUnavailable("Speech transcription is not configured")
        started = perf_counter()
        try:
            response = await self.client.audio.transcriptions.create(
                model=self.model,
                file=("voice.wav", audio, "audio/wav"),
            )
        except AuthenticationError as exc:
            raise TranscriptionUnavailable("Speech transcription credentials were rejected") from exc
        except PermissionDeniedError as exc:
            raise TranscriptionUnavailable("This API project cannot use the transcription model") from exc
        except NotFoundError as exc:
            raise TranscriptionUnavailable("The configured transcription model is not available") from exc
        except RateLimitError as exc:
            code = getattr(exc, "code", None)
            message = "Speech transcription quota or billing is unavailable" if code == "insufficient_quota" else "Speech transcription is rate limited; try again shortly"
            raise TranscriptionUnavailable(message) from exc
        except BadRequestError as exc:
            raise TranscriptionUnavailable("The transcription provider rejected the audio request") from exc
        except (APIConnectionError, APITimeoutError) as exc:
            raise TranscriptionUnavailable("Speech transcription could not reach the provider") from exc
        except Exception as exc:
            raise TranscriptionUnavailable("Speech transcription is temporarily unavailable") from exc
        text = getattr(response, "text", "").strip()
        if not text:
            raise InvalidAudio("No speech could be transcribed; please record again")
        return TranscriptionResult(text=text, model=self.model, latency_ms=int((perf_counter() - started) * 1000))

    def _validate_wav(self, audio: bytes) -> None:
        if not audio or len(audio) > self.max_audio_bytes:
            raise InvalidAudio("Audio is empty or exceeds the configured size limit")
        try:
            with wave.open(io.BytesIO(audio), "rb") as recording:
                duration = recording.getnframes() / max(recording.getframerate(), 1)
                if recording.getnchannels() != 1 or recording.getsampwidth() != 2:
                    raise InvalidAudio("Audio must be mono 16-bit PCM WAV")
                if duration < 0.35:
                    raise InvalidAudio("Recording is too short to transcribe")
                if duration > 20.5:
                    raise InvalidAudio("Recording exceeds the 20-second limit")
        except (wave.Error, EOFError) as exc:
            raise InvalidAudio("Audio must be a valid PCM WAV recording") from exc
