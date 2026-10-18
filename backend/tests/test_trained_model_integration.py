"""Live packaged-model smoke; model outputs are not an accuracy evaluation."""

import base64
import io
import json
import math
import struct
import wave
from pathlib import Path
from uuid import uuid4

import pytest

from app.core.config import REPOSITORY_ROOT, Settings
from app.models.domain import Difficulty, Session
from app.repositories.memory import MemoryRepository
from app.services.conversation_service import ConversationService
from app.services.llm_service import TemplateResponseGenerator
from app.services.multimodal_service import MultimodalAffectService


class SerializedMemoryRepository(MemoryRepository):
    """Exercise the persisted JSON shape instead of retaining object references."""

    async def save_session(self, session: Session) -> Session:
        saved = await super().save_session(session)
        stored = Session.model_validate_json(saved.model_dump_json())
        self.sessions[stored.id] = stored
        return Session.model_validate_json(stored.model_dump_json())

    async def get_session(self, session_id, user_id):
        stored = await super().get_session(session_id, user_id)
        return Session.model_validate_json(stored.model_dump_json()) if stored else None


def _configured_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    # Deployment defaults are written relative to the backend working directory.
    return (REPOSITORY_ROOT / "backend" / path).resolve()


def _packaged_service() -> tuple[MultimodalAffectService, dict]:
    settings = Settings()
    text_model = _configured_path(settings.multimodal_text_model_dir)
    audio_model = _configured_path(settings.multimodal_audio_model_dir)
    config_path = _configured_path(settings.multimodal_config_path)
    missing = [
        name
        for name, value, path, expected_type in (
            ("MULTIMODAL_TEXT_MODEL_DIR", settings.multimodal_text_model_dir, text_model, "directory"),
            ("MULTIMODAL_AUDIO_MODEL_DIR", settings.multimodal_audio_model_dir, audio_model, "directory"),
            ("MULTIMODAL_CONFIG_PATH", settings.multimodal_config_path, config_path, "file"),
        )
        if not value.strip()
        or (expected_type == "directory" and not path.is_dir())
        or (expected_type == "file" and not path.is_file())
    ]
    if missing:
        pytest.skip("Packaged model smoke requires configured artifacts: " + ", ".join(missing))
    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    return (
        MultimodalAffectService(
            True,
            str(text_model),
            str(audio_model),
            str(config_path),
            device="cpu",
            low_confidence_threshold=settings.multimodal_low_confidence_threshold,
        ),
        config,
    )


def _deterministic_wav() -> bytes:
    """Return a valid non-participant probe, not an emotion-labelled sample."""
    sample_rate = 16_000
    frames = bytearray()
    for index in range(sample_rate):
        seconds = index / sample_rate
        sample = 0.12 * math.sin(2 * math.pi * 180 * seconds)
        sample += 0.06 * math.sin(2 * math.pi * 360 * seconds)
        frames.extend(struct.pack("<h", round(sample * 32767)))
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(frames)
    return output.getvalue()


@pytest.mark.trained_model_integration
@pytest.mark.asyncio
async def test_packaged_models_calibrate_store_and_reload_explanation() -> None:
    multimodal, config = _packaged_service()
    calibration_calls = 0
    apply_calibration = multimodal._apply_calibration

    def observed_calibration(text_logits, audio_logits):
        nonlocal calibration_calls
        calibration_calls += 1
        return apply_calibration(text_logits, audio_logits)

    multimodal._apply_calibration = observed_calibration
    repository = SerializedMemoryRepository()
    service = ConversationService(repository, generator=TemplateResponseGenerator())
    session = await service.create_session(uuid4())
    session, _, _ = await service.start_roleplay(
        session.id,
        session.user_id,
        "workload",
        Difficulty.INTERMEDIATE,
        pre_skipped=True,
        character_profile="cooperative",
    )
    encoded_audio = base64.b64encode(_deterministic_wav()).decode("ascii")
    request_id = uuid4()
    message = "I have too many tasks. Could we agree which one should come first?"

    _, _, saved = await service.chat(
        session.id,
        session.user_id,
        message,
        request_id=request_id,
        expected_version=session.version,
        audio_wav_base64=encoded_audio,
        adaptation_enabled=True,
        multimodal=multimodal,
    )

    assert multimodal.status == "ready"
    assert calibration_calls == 1
    assert multimodal.calibration == config["calibration"]
    persisted_json = repository.sessions[saved.id].model_dump_json()
    assert encoded_audio not in persisted_json

    # A fresh application service must project the saved explanation, not infer it again.
    reloaded = await ConversationService(
        repository, generator=TemplateResponseGenerator()
    ).get_session(saved.id, saved.user_id)
    explanation = reloaded.turns[-1].affect_decision
    assert explanation is not None
    assert reloaded.turns[-2].content == message
    assert explanation.request_id == request_id
    assert explanation.user_turn_id == reloaded.turns[-2].id
    assert explanation.assistant_turn_id == reloaded.turns[-1].id
    assert explanation.source == "trained_multimodal"
    assert explanation.audio_submitted is True
    assert explanation.audio_available is True
    assert explanation.prediction is not None
    assert explanation.prediction.model_version == multimodal.version
    for distribution in (
        explanation.prediction.text_distribution,
        explanation.prediction.audio_distribution,
        explanation.prediction.distribution,
    ):
        assert set(distribution) == set(config["labels"])
        assert sum(distribution.values()) == pytest.approx(1.0)
    assert explanation == reloaded.roleplay.decisions[-1].affect_decision
