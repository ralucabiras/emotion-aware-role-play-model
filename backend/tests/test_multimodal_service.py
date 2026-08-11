from uuid import uuid4

import pytest

from app.models.domain import ConversationTurn, Role, Session
from app.services.multimodal_service import (
    MultimodalAffectService,
    MultimodalInferenceUnavailable,
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
