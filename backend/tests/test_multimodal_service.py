import asyncio
import time
from uuid import uuid4

import pytest

from app.models.domain import ConversationTurn, Role, Session
from app.services.multimodal_service import (
    MultimodalAffectService,
    MultimodalInferenceUnavailable,
    confidence_level,
    format_context,
)


def test_context_uses_three_causal_turns_and_speaker_markers() -> None:
    session = Session(
        user_id=uuid4(),
        turns=[
            ConversationTurn(role=Role.USER, content="old"),
            ConversationTurn(role=Role.ASSISTANT, content="reply"),
            ConversationTurn(role=Role.USER, content="recent"),
            ConversationTurn(role=Role.ASSISTANT, content="prompt"),
        ],
    )

    assert format_context(session, "target") == (
        "[other speaker] reply\n"
        "[same speaker] recent\n"
        "[other speaker] prompt\n"
        "[target] target"
    )


@pytest.mark.asyncio
async def test_disabled_multimodal_service_fails_without_loading_ml_dependencies() -> None:
    service = MultimodalAffectService(False, "", "", "missing.json")

    with pytest.raises(MultimodalInferenceUnavailable):
        await service.analyze(Session(user_id=uuid4()), "hello", b"wav")


def test_confidence_presentation_levels_are_explicit() -> None:
    assert confidence_level(0.54, 0.55) == "low"
    assert confidence_level(0.55, 0.55) == "moderate"
    assert confidence_level(0.75, 0.55) == "high"
    with pytest.raises(ValueError):
        confidence_level(0.5, 1.0)


@pytest.mark.asyncio
async def test_multimodal_requests_are_serialized(tmp_path) -> None:
    text, audio, config = tmp_path / "text", tmp_path / "audio", tmp_path / "config.json"
    text.mkdir(); audio.mkdir(); config.write_text("{}")
    service = MultimodalAffectService(True, str(text), str(audio), str(config))
    active, maximum = 0, 0

    def analyze(context, payload, queue_ms=0):
        nonlocal active, maximum
        active += 1; maximum = max(maximum, active); time.sleep(0.03); active -= 1
        return {"queue_ms": queue_ms}

    service._analyze_sync = analyze
    session = Session(user_id=uuid4())
    results = await asyncio.gather(
        service.analyze(session, "one", b"wav"),
        service.analyze(session, "two", b"wav"),
    )
    assert maximum == 1
    assert results[1]["queue_ms"] > 0
