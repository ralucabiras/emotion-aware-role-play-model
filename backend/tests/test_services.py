from datetime import timedelta

import pytest

from app.models.domain import Difficulty, EmotionState, RolePlayStatus, Session, User, utcnow
from app.repositories.memory import MemoryRepository
from app.services.auth_service import AuthenticationError, AuthService
from app.services.llm_service import OpenAIResponseGenerator
from app.services.roleplay_service import RolePlayService, observe


@pytest.mark.asyncio
async def test_passwords_tokens_rotation_and_expiry() -> None:
    repository = MemoryRepository()
    auth = AuthService(repository)
    user = await auth.register(" Mixed@Example.com ", "a-secure-password", True)
    assert user.email == "mixed@example.com"
    assert user.password_hash != "a-secure-password"
    assert auth.decode_access(auth.access_token(user.id)) == user.id
    token = await auth.refresh_token(user.id)
    rotated_user, replacement = await auth.rotate(token)
    assert rotated_user == user.id and replacement != token
    with pytest.raises(AuthenticationError):
        await auth.rotate(token)


@pytest.mark.asyncio
async def test_repository_ownership_expiry_and_cascade() -> None:
    repository = MemoryRepository()
    first = User(email="one@example.com", password_hash="x", consented_at=utcnow())
    second = User(email="two@example.com", password_hash="x", consented_at=utcnow())
    await repository.create_user(first)
    await repository.create_user(second)
    session = await repository.save_session(Session(user_id=first.id))
    assert await repository.get_session(session.id, second.id) is None
    session.expires_at = utcnow() - timedelta(seconds=1)
    assert await repository.get_session(session.id, first.id) is None
    await repository.delete_user(first.id)
    assert not [item for item in repository.sessions.values() if item.user_id == first.id]


def test_scenarios_difficulty_observations_and_completion() -> None:
    service = RolePlayService()
    for scenario_id in ("workload", "boundary", "relationship"):
        for difficulty in Difficulty:
            state, scenario = service.start(scenario_id, difficulty)
            assert scenario.id == scenario_id and state.difficulty_level == difficulty
    item = observe(1, "Sorry, sorry, I cannot do that because of my deadline", 0.4)
    assert item.excessive_apology and item.maintained_boundary and item.specific_detail
    state, _ = service.start("workload", Difficulty.BEGINNER)
    service.respond(state, "I need you to prioritise this deadline because it is this week", EmotionState())
    assert state.status == RolePlayStatus.COMPLETED
    feedback = service.feedback(state)
    assert feedback.metrics and all(metric.evidence_turns for metric in feedback.metrics[:2])


@pytest.mark.asyncio
async def test_openai_generator_offline_fallback_records_reason(monkeypatch) -> None:
    monkeypatch.setattr("app.services.llm_service.settings.openai_api_key", None)
    generator = OpenAIResponseGenerator()
    session = Session(user_id=User(email="x@example.com", password_hash="x", consented_at=utcnow()).id)
    text, metadata = await generator.generate(session, "Help me", "validation")
    assert text and metadata.source == "template" and metadata.fallback_reason == "missing_api_key"
