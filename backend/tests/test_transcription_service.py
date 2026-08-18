import io
import wave

import pytest

from app.services.transcription_service import InvalidAudio, TranscriptionService, TranscriptionUnavailable


def wav_bytes(seconds: float = 0.5, sample_rate: int = 16_000) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as recording:
        recording.setnchannels(1)
        recording.setsampwidth(2)
        recording.setframerate(sample_rate)
        recording.writeframes(b"\x00\x00" * int(seconds * sample_rate))
    return output.getvalue()


@pytest.mark.asyncio
async def test_transcription_validates_audio_before_provider_use() -> None:
    service = TranscriptionService(False, None, "gpt-transcribe", 10, 1_000_000)
    with pytest.raises(InvalidAudio, match="valid PCM WAV"):
        await service.transcribe(b"not a wav")
    with pytest.raises(InvalidAudio, match="too short"):
        await service.transcribe(wav_bytes(0.1))
    with pytest.raises(TranscriptionUnavailable):
        await service.transcribe(wav_bytes())


@pytest.mark.asyncio
async def test_transcription_returns_text_without_persisting_audio() -> None:
    service = TranscriptionService(False, None, "gpt-transcribe", 10, 1_000_000)

    class Response:
        text = "Please move the deadline to Friday."

    class Transcriptions:
        async def create(self, **kwargs):
            assert kwargs["file"][0] == "voice.wav"
            return Response()

    class Audio:
        transcriptions = Transcriptions()

    class Client:
        audio = Audio()

    service.client = Client()
    result = await service.transcribe(wav_bytes())
    assert result.text == "Please move the deadline to Friday."
    assert result.audio_persisted is False
