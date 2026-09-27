"""Synthetic predictions test application policy, not model accuracy or people."""
import asyncio
import base64
from uuid import uuid4

import pytest

from app.models.domain import AffectDecision, Difficulty, MultimodalEstimate, Session
from app.repositories.memory import MemoryRepository
from app.repositories.mongo import ConcurrentSessionUpdateError
from app.schemas.chat import ChatRequest
from app.services.affect_pacing import select
from app.services.conversation_service import ConversationService
from app.services.llm_service import TemplateResponseGenerator


def prediction(label="sadness", text_label=None, audio_label=None, confidence=.8):
    labels = ["anger", "happiness", "neutral", "sadness"] if label in {"anger", "happiness", "neutral", "sadness"} else [label, "other"]
    def distribution(chosen):
        return {key: confidence if key == chosen else (1-confidence)/(len(labels)-1) for key in labels}
    text_label, audio_label = text_label or label, audio_label or label
    return dict(label=label, confidence=confidence, distribution=distribution(label),
        text_label=text_label, text_confidence=confidence, text_distribution=distribution(text_label),
        audio_label=audio_label, audio_confidence=confidence, audio_distribution=distribution(audio_label),
        modalities_agree=text_label == audio_label, confidence_level="high", low_confidence_threshold=.55,
        model_version="synthetic-test-model", latency_ms=12, queue_ms=2)


def record(**kwargs):
    return AffectDecision(request_id=uuid4(), session_version=2, user_turn_id=uuid4(), assistant_turn_id=uuid4(), **kwargs)


@pytest.mark.parametrize("estimate,action,reason", [
    (prediction(), "acknowledge", "supported_matching_estimates"),
    (prediction("happiness"), "baseline", "no_adaptation_for_label"),
    (prediction(audio_label="anger"), "offer_pacing", "modality_disagreement"),
    (prediction(confidence=.4), "offer_pacing", "low_confidence"),
    (prediction("unsupported"), "baseline", "unsupported_categories"),
])
def test_policy_table(estimate, action, reason):
    r = record(adaptation_enabled=True, prediction=MultimodalEstimate.model_validate(estimate))
    select(r, eligible=True)
    assert (r.action, r.reason) == (action, reason)


@pytest.mark.parametrize("preference,action", [("keep_going", "baseline"), ("gentler", "gentler"), ("more_challenge", "more_challenge")])
@pytest.mark.parametrize("enabled", [True, False])
def test_user_preference_precedes_estimates_and_automatic_setting(preference, action, enabled):
    r = record(adaptation_enabled=enabled, preference=preference, prediction=MultimodalEstimate.model_validate(prediction(confidence=.4)))
    select(r, eligible=True)
    assert r.action == action and r.reason == "user_preference"


def test_disabled_and_missing_audio_baselines():
    r = record(prediction=MultimodalEstimate.model_validate(prediction()))
    assert select(r, eligible=True) == "" and r.reason == "adaptation_disabled"
    r = record(adaptation_enabled=True)
    assert select(r, eligible=True) == "" and r.reason == "missing_audio"


def test_schema_rejects_unbound_and_client_predictions():
    for extra in [{"audio_wav_base64":"AAAA"}, {"adaptation_enabled":True}, {"prediction":prediction()}]:
        with pytest.raises(ValueError):
            ChatRequest(session_id=uuid4(), message="test", **extra)
    malformed = prediction()
    malformed["distribution"]["sadness"] = float("nan")
    with pytest.raises(ValueError):
        MultimodalEstimate.model_validate(malformed)


class FakeModel:
    available = True
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail
    async def analyze(self, session, message, audio):
        self.calls.append((session.version, message, audio, len(session.turns)))
        await asyncio.sleep(.01)
        if self.fail:
            raise RuntimeError("synthetic private error")
        return prediction()


async def start(repository=None):
    service = ConversationService(repository or MemoryRepository(), generator=TemplateResponseGenerator())
    session = await service.create_session(uuid4())
    session, _, _ = await service.start_roleplay(session.id, session.user_id, "workload", Difficulty.INTERMEDIATE,
        pre_skipped=True, character_profile="cooperative")
    return service, session


async def submit(service, session, **kwargs):
    return await service.chat(session.id, session.user_id, "I am overloaded with tasks. Could you help me prioritise?",
        expected_version=session.version, request_id=uuid4(), **kwargs)


@pytest.mark.asyncio
async def test_linking_final_text_persistence_and_rewind():
    service, session = await start()
    model = FakeModel()
    audio = base64.b64encode(b"synthetic-transient-wave").decode()
    request_id = uuid4()
    turn, _, saved = await service.chat(session.id, session.user_id, "I have too many tasks. Could we prioritise?",
        expected_version=session.version, request_id=request_id, audio_wav_base64=audio, adaptation_enabled=True, multimodal=model)
    assert model.calls == [(session.version, "I have too many tasks. Could we prioritise?", b"synthetic-transient-wave", 1)]
    decision = turn.affect_decision
    assert decision.user_turn_id == saved.turns[-2].id
    assert decision.assistant_turn_id == turn.id
    assert decision == saved.roleplay.decisions[-1].affect_decision
    assert decision.action == "acknowledge"
    assert turn.content.startswith("I hear you.")
    assert audio not in saved.model_dump_json()
    reloaded = Session.model_validate_json(saved.model_dump_json())
    assert reloaded.turns[-1].affect_decision == decision
    assert decision.prediction.model_version == "synthetic-test-model"
    assert decision.prediction.latency_ms == 12
    with pytest.raises(ValueError, match="already processed"):
        await service.chat(saved.id, saved.user_id, "Changed text", expected_version=saved.version, request_id=request_id)
    _, saved = await service.rewind_roleplay(saved.id, saved.user_id)
    assert not saved.roleplay.decisions
    assert all(t.affect_decision is None for t in saved.turns)
    assert request_id in saved.submission_ids


@pytest.mark.asyncio
async def test_stale_and_parallel_requests_cannot_publish_wrong_estimates():
    service, session = await start()
    model = FakeModel()
    with pytest.raises(ValueError, match="Session changed"):
        await service.chat(session.id, session.user_id, "old", expected_version=session.version-1, request_id=uuid4(), multimodal=model)
    assert not model.calls
    results = await asyncio.gather(*(submit(service, session, audio_wav_base64="AAAA", multimodal=model, adaptation_enabled=True) for _ in range(2)), return_exceptions=True)
    assert sum(isinstance(r, ConcurrentSessionUpdateError) for r in results) == 1
    saved = await service.get_session(session.id, session.user_id)
    assert len(saved.turns) == 3 and len(saved.roleplay.decisions) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["missing", "unavailable", "failure", "invalid_audio", "invalid_estimate"])
async def test_failure_keeps_usable_rehearsal(case):
    service, session = await start()
    model = FakeModel(fail=case=="failure")
    model.available = case != "unavailable"
    if case == "invalid_estimate":
        async def invalid(*args):
            return {"untrusted": "invalid output"}
        model.analyze = invalid
    audio = None if case == "missing" else "%%%" if case == "invalid_audio" else "AAAA"
    turn, _, saved = await submit(service, session, audio_wav_base64=audio, multimodal=model, adaptation_enabled=True)
    assert saved.roleplay.dialogue.stage == "constraints"
    assert turn.affect_decision.action == "baseline"
    assert turn.affect_decision.prediction is None
    assert "synthetic private error" not in saved.model_dump_json()


@pytest.mark.asyncio
async def test_disabled_setting_is_same_dialogue_and_lexical_state():
    baseline_service, baseline = await start()
    enhanced_service, enhanced = await start()
    ordinary, decision, plain = await submit(baseline_service, baseline)
    with_audio, audio_decision, saved = await submit(enhanced_service, enhanced, audio_wav_base64="AAAA", multimodal=FakeModel())
    assert ordinary.content == with_audio.content
    assert decision.emotion_state == audio_decision.emotion_state
    assert plain.roleplay.dialogue == saved.roleplay.dialogue
    assert with_audio.affect_decision.reason == "adaptation_disabled"


@pytest.mark.asyncio
async def test_safety_skips_inference_and_overrides_preferences():
    service, session = await start()
    model = FakeModel()
    turn, _, saved = await service.chat(session.id, session.user_id, "I want to kill myself", expected_version=session.version,
        request_id=uuid4(), audio_wav_base64="AAAA", multimodal=model, pacing="more_challenge", adaptation_enabled=True)
    assert not model.calls
    assert turn.affect_decision.reason == "safety_override"
    assert turn.affect_decision.action == "baseline"
    assert saved.roleplay.status == "interrupted"


@pytest.mark.asyncio
async def test_legacy_baseline_never_uses_prediction_or_pacing():
    service, session = await start()
    session.roleplay.dialogue = None
    model = FakeModel()
    turn, _, saved = await submit(service, session, audio_wav_base64="AAAA", multimodal=model, pacing="gentler", adaptation_enabled=True)
    assert not model.calls
    assert turn.affect_decision.reason == "baseline_session"
    assert turn.affect_decision.action == "baseline"


@pytest.mark.asyncio
async def test_inflight_analysis_cannot_recreate_deleted_session():
    service, session = await start()
    entered, release = asyncio.Event(), asyncio.Event()
    class WaitingModel(FakeModel):
        async def analyze(self, *args):
            entered.set()
            await release.wait()
            return prediction()
    task = asyncio.create_task(submit(service,session,audio_wav_base64="AAAA",multimodal=WaitingModel()))
    await entered.wait()
    await service.delete_session(session.id,session.user_id)
    release.set()
    with pytest.raises(ConcurrentSessionUpdateError):
        await task
    assert await service.repository.get_session(session.id,session.user_id) is None


@pytest.mark.asyncio
async def test_required_rehearsal_ignores_automatic_and_explicit_pacing():
    service, session = await start()
    session.roleplay.attempt_purpose = "required"
    session.roleplay.required_task_id = "workload"
    model = FakeModel()
    turn, _, _ = await submit(service,session,audio_wav_base64="AAAA",multimodal=model,adaptation_enabled=True,pacing="more_challenge")
    assert not model.calls and turn.affect_decision.reason == "baseline_session"


def test_ending_never_adds_a_pacing_question():
    r = record(adaptation_enabled=True, preference="gentler", prediction=MultimodalEstimate.model_validate(prediction(confidence=.4)))
    assert select(r,eligible=True,ended=True) == ""
    assert r.action == "baseline" and r.reason == "rehearsal_ended"
