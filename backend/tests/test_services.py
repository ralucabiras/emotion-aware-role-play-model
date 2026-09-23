import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest

from app.core.config import settings
from app.models.domain import (
    Difficulty,
    EmotionState,
    FrozenStudyExport,
    RolePlayStatus,
    Session,
    StudyConsentRecord,
    StudyEligibilityRecord,
    StudyLifecycle,
    StudyRecord,
    SupportStrategy,
    User,
    utcnow,
)
from app.repositories.memory import MemoryRepository
from app.services.affect_service import RuleBasedCognitiveAnalyzer, RuleBasedEmotionAnalyzer
from app.services.auth_service import AuthenticationError, AuthService
from app.services.conversation_service import ConversationService
from app.services.eligibility import eligibility_version
from app.services.llm_service import OpenAIResponseGenerator, RolePlayWording, TemplateResponseGenerator
from app.services.roleplay_service import SCENARIOS, RolePlayService, observe
from app.services.strategy_service import ScoredStrategySelector


class CapturingEmailService:
    def __init__(self) -> None:
        self.token = ""
        self.reset_token = ""

    async def send_verification(self, recipient: str, preferred_name: str, token: str) -> None:
        self.token = token

    async def send_password_reset(self, recipient: str, preferred_name: str, token: str) -> None:
        self.reset_token = token


@pytest.mark.asyncio
async def test_passwords_tokens_rotation_and_expiry() -> None:
    repository = MemoryRepository()
    email = CapturingEmailService()
    auth = AuthService(repository, email)
    user = await auth.register(" Mixed@Example.com ", "a-secure-password", True)
    assert user.email == "mixed@example.com"
    assert user.password_hash != "a-secure-password"
    with pytest.raises(AuthenticationError):
        await auth.authenticate("mixed@example.com", "a-secure-password")
    await auth.verify_email(email.token)
    assert (await auth.verify_email(email.token)).id == user.id
    assert (await auth.authenticate("mixed@example.com", "a-secure-password")).id == user.id
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
    study_record = await repository.save_study_record(StudyRecord(
        user_id=first.id,
        participant_id=first.participant_id,
        session_id=session.id,
        consent_version="test-v1",
        enrolled_at=utcnow(),
        session_created_at=session.created_at,
        last_activity_at=utcnow(),
        retention_expires_at=utcnow() + timedelta(days=365),
    ))
    assert await repository.get_session(session.id, second.id) is None
    session.expires_at = utcnow() - timedelta(seconds=1)
    assert await repository.get_session(session.id, first.id) is None
    assert (await repository.list_study_records(first.id))[0].id == study_record.id
    await repository.delete_user(first.id)
    assert not [item for item in repository.sessions.values() if item.user_id == first.id]
    assert not await repository.list_study_records(first.id)


def test_scenarios_difficulty_observations_and_completion() -> None:
    service = RolePlayService()
    for scenario_id in ("workload", "boundary", "relationship", "colleague_feedback", "deadline", "household"):
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


def test_relationship_roleplay_progresses_and_feedback_is_scenario_specific() -> None:
    service = RolePlayService()
    state, _ = service.start("relationship", Difficulty.BEGINNER)
    first = service.respond(
        state, "I feel like you don't make time for me anymore.", EmotionState()
    )
    second = service.respond(
        state, "I want you to be more available.", EmotionState()
    )
    final = service.respond(
        state, "I would like two evenings each week when we spend an hour together.", EmotionState()
    )
    assert "do differently" in first
    assert "look like in practice" in second
    assert state.status == RolePlayStatus.COMPLETED
    assert "clear understanding" in final
    feedback = service.feedback(state)
    metric_names = {metric.name for metric in feedback.metrics}
    assert metric_names == {"I-statements", "specific need", "non-blaming language"}
    assert "boundary maintenance" not in " ".join(feedback.suggestions).lower()


def test_difficult_boundary_requires_maintaining_refusal_and_feedback_does_not_escalate() -> None:
    service = RolePlayService()
    state, _ = service.start("boundary", Difficulty.DIFFICULT)
    prompt = service.respond(state, "I am busy and I can't this week.", EmotionState())
    assert state.status == RolePlayStatus.ACTIVE
    assert "answer still no" in prompt
    service.respond(state, "Yes, my answer is still no. I cannot take this on.", EmotionState())
    assert state.status == RolePlayStatus.COMPLETED
    feedback = service.feedback(state)
    assert all("higher difficulty" not in item for item in feedback.suggestions)


@pytest.mark.asyncio
async def test_openai_generator_offline_fallback_records_reason(monkeypatch) -> None:
    monkeypatch.setattr("app.services.llm_service.settings.openai_api_key", None)
    generator = OpenAIResponseGenerator()
    session = Session(user_id=User(email="x@example.com", password_hash="x", consented_at=utcnow()).id)
    text, metadata = await generator.generate(session, "Help me", "validation")
    assert text and metadata.source == "template" and metadata.fallback_reason == "missing_api_key"


@pytest.mark.asyncio
async def test_openai_reflection_explicitly_disables_response_storage() -> None:
    generator = OpenAIResponseGenerator()

    class Response:
        output_text = "That sounds difficult. What outcome would feel most useful?"
        usage = None

    class Responses:
        async def create(self, **kwargs):
            assert kwargs["store"] is False
            return Response()

    class Client:
        responses = Responses()

    generator.client = Client()
    session = Session(
        user_id=User(
            email="privacy@example.com", password_hash="x", consented_at=utcnow()
        ).id
    )
    text, metadata = await generator.generate(
        session, "I need help preparing for a conversation", SupportStrategy.REFLECTION
    )
    assert text.startswith("That sounds difficult")
    assert metadata.source == "openai"


@pytest.mark.asyncio
async def test_emotional_statements_receive_specific_offline_support() -> None:
    analyzer = RuleBasedEmotionAnalyzer()
    selector = ScoredStrategySelector()
    cognitive = RuleBasedCognitiveAnalyzer()
    for message in (
        "I am nervous, I have an interview tomorrow.",
        "I had a fight with my manager again.",
    ):
        state = analyzer.analyze(message)
        decision = selector.decide(state, cognitive.analyze(message))
        text, _ = await TemplateResponseGenerator().generate(
            Session(user_id=User(email="x@example.com", password_hash="x", consented_at=utcnow()).id, emotion_state=state),
            message,
            decision.strategy,
        )
        assert "Tell me a little more" not in text
        assert state.dominant_emotion.value in text.lower()


@pytest.mark.asyncio
async def test_roleplay_generation_accepts_only_the_deterministic_action() -> None:
    generator = OpenAIResponseGenerator()

    class Response:
        output_parsed = RolePlayWording(
            dialogue="I hear that this week is full. Is your answer still no?",
            character_action="apply_pressure",
        )
        usage = None

    class Responses:
        async def parse(self, **kwargs):
            assert kwargs["store"] is False
            assert kwargs["text_format"] is RolePlayWording
            return Response()

    class Client:
        responses = Responses()

    generator.client = Client()
    roleplay, _ = RolePlayService().start("boundary", Difficulty.DIFFICULT)
    session = Session(
        user_id=User(email="x@example.com", password_hash="x", consented_at=utcnow()).id,
        roleplay=roleplay,
    )
    text, metadata = await generator.generate_roleplay(
        session, SCENARIOS["boundary"], "apply_pressure", "fallback"
    )
    assert "answer still no" in text
    assert metadata.source == "openai_roleplay"

    Response.output_parsed = RolePlayWording(
        dialogue="Here is some coaching.", character_action="accept_and_close"
    )
    text, metadata = await generator.generate_roleplay(
        session, SCENARIOS["boundary"], "apply_pressure", "fallback"
    )
    assert text == "fallback"
    assert metadata.fallback_reason == "invalid_roleplay_output"


@pytest.mark.asyncio
async def test_dataset_freeze_allows_only_one_owner_and_commits_atomically() -> None:
    repository = MemoryRepository()
    protocol = "freeze-concurrency-test"
    await repository.save_study_lifecycle(StudyLifecycle(protocol_version=protocol))
    tokens = uuid4(), uuid4()

    claims = await asyncio.gather(
        *(repository.begin_dataset_freeze(protocol, token) for token in tokens)
    )

    assert sum(claim is not None for claim in claims) == 1
    winning_token = tokens[claims.index(next(claim for claim in claims if claim is not None))]
    export = FrozenStudyExport(
        protocol_version=protocol,
        record_count=0,
        participant_count=0,
        sha256="0" * 64,
        csv_content="header\n",
    )
    await repository.complete_dataset_freeze(export, winning_token)

    lifecycle = await repository.get_study_lifecycle(protocol)
    assert lifecycle is not None
    assert lifecycle.dataset_frozen_at == export.created_at
    assert lifecycle.frozen_export_id == export.id
    assert lifecycle.freeze_token is None
    assert await repository.get_frozen_export(export.id) == export


@pytest.mark.asyncio
async def test_dataset_freeze_abort_releases_claim_without_export() -> None:
    repository = MemoryRepository()
    protocol = "freeze-retry-test"
    await repository.save_study_lifecycle(StudyLifecycle(protocol_version=protocol))
    first_token, retry_token = uuid4(), uuid4()

    assert await repository.begin_dataset_freeze(protocol, first_token)
    await repository.abort_dataset_freeze(protocol, first_token)

    assert await repository.begin_dataset_freeze(protocol, retry_token)
    assert repository.frozen_exports == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("next_scenario", ["workload", "boundary"])
async def test_new_rehearsal_preserves_attempt_ratings_and_study_record(next_scenario) -> None:
    repository = MemoryRepository()
    user = User(
        email="attempts@example.com", password_hash="unused", consented_at=utcnow(),
        pilot_enrolled_at=utcnow(),
        study_consent=StudyConsentRecord(version=settings.study_consent_version, protocol_version=settings.study_protocol_version),
        study_eligibility=StudyEligibilityRecord(version=eligibility_version(), protocol_version=settings.study_protocol_version),
    )
    await repository.create_user(user)
    service = ConversationService(repository, generator=TemplateResponseGenerator())
    workspace = await service.create_session(user.id)
    first, _, _ = await service.start_roleplay(workspace.id, user.id, "workload", Difficulty.INTERMEDIATE, pre_ratings={"confidence": 2, "anxiety": 6})
    assert first.id == workspace.id  # Do not leave an empty workspace behind.
    await service.chat(first.id, user.id, "I need you to move the report deadline to Friday because I have 12 hours of work this week.")
    assert first.feedback is not None
    await service.submit_questionnaire(first.id, user.id, "post", {"confidence": 6, "realism": 5, "usefulness": 7}, post_token=first.post_questionnaire_token)
    await service.save_takeaway(first.id, user.id, "Keep the first takeaway.")
    original_session = first.model_dump(mode="json")
    original_record = (await repository.list_study_records(user.id))[0].model_dump(mode="json")

    second, _, _ = await service.start_roleplay(first.id, user.id, next_scenario, Difficulty.INTERMEDIATE, pre_ratings={"confidence": 3, "anxiety": 4})
    assert second.id != first.id
    assert second.questionnaires["pre"].confidence == 3
    assert "post" not in second.questionnaires
    assert second.takeaway == ""
    assert second.feedback is None
    assert len(second.turns) == 1
    assert len(await repository.list_sessions(user.id)) == 2
    assert (await repository.get_session(first.id, user.id)).model_dump(mode="json") == original_session
    records = {record.session_id: record for record in await repository.list_study_records(user.id)}
    assert len(records) == 2
    assert records[first.id].model_dump(mode="json") == original_record
    assert records[second.id].questionnaires["pre"].confidence == 3
    assert "post" not in records[second.id].questionnaires

    if next_scenario == "workload":
        await service.chat(second.id, user.id, "I need you to prioritise the deadline because it is this week.")
        assert second.feedback.compared_with_session_id == first.id
        assert second.feedback.comparisons
        original_metrics = {metric.name: metric.score for metric in first.feedback.metrics}
        for comparison in second.feedback.comparisons:
            assert comparison.previous_score == original_metrics[comparison.name]
        assert (await repository.get_session(first.id, user.id)).model_dump(mode="json") == original_session

    # An invalid start must not create an orphan attempt or alter either session.
    with pytest.raises(KeyError):
        await service.start_roleplay(second.id, user.id, "unknown", Difficulty.INTERMEDIATE)
    assert len(await repository.list_sessions(user.id)) == 2


@pytest.mark.asyncio
async def test_reflection_messages_do_not_advance_a_paused_rehearsal():
    repository = MemoryRepository()
    user = User(email="pause-reflect@example.com", password_hash="unused", consented_at=utcnow())
    await repository.create_user(user)
    service = ConversationService(repository, generator=TemplateResponseGenerator())
    workspace = await service.create_session(user.id)
    session, _, _ = await service.start_roleplay(workspace.id, user.id, "boundary", Difficulty.INTERMEDIATE, pre_skipped=True)
    await service.set_roleplay_status(session.id, user.id, "pause")
    evidence = session.roleplay.evidence.copy()
    reply, _, reflected = await service.chat(session.id, user.id, "I feel nervous about this conversation.")
    assert reply.content
    assert reflected.roleplay.status == RolePlayStatus.PAUSED
    assert reflected.roleplay.turn == 0 and reflected.roleplay.evidence == evidence
    await service.set_roleplay_status(session.id, user.id, "resume")
    _, _, resumed = await service.chat(session.id, user.id, "I cannot help this week.")
    assert resumed.roleplay.turn == 1
