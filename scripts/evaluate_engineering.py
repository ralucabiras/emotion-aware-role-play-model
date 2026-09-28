"""Authored synthetic engineering fixtures; neither model nor participant evaluation."""
import asyncio
import hashlib
import json
import platform
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from app.models.domain import AffectDecision, Difficulty, MultimodalEstimate  # noqa: E402
from app.repositories.memory import MemoryRepository  # noqa: E402
from app.services.affect_pacing import select  # noqa: E402
from app.services.conversation_service import ConversationService  # noqa: E402
from app.services.llm_service import TemplateResponseGenerator  # noqa: E402
from app.services.scenario_dialogue import features  # noqa: E402

OPEN = 'I have too many tasks and 12 hours of work. Could you help me prioritise?'
PROPOSE = 'I understand the report must be ready by Friday. Could we move the other tasks to Monday?'
CASES = [
    ('workload', [OPEN, PROPOSE, 'Agreed, I will carry out that plan.'], ['constraints', 'agree', 'resolved']),
    ('workload', [OPEN, PROPOSE, 'I cannot agree to that.'], ['constraints', 'agree', 'agree']),
    ('boundary', ['I cannot take this on.', 'My answer is still no. Thank you for understanding.'], ['pressure', 'resolved']),
    ('relationship', ['When we spend evenings apart, I feel lonely and I need time together.',
                      'I understand you are tired. Could we talk for 20 minutes on Saturday as a trial and review it on Sunday?',
                      'Agreed.'], ['perspective', 'agree', 'resolved']),
    ('relationship', ['When we spend evenings apart, I feel lonely and I need time together.',
                      "Let's agree to disagree and leave this unresolved."], ['perspective', 'unresolved']),
]
# Expected labels are human-authored semantic judgments, deliberately including
# paraphrases and reported speech outside the lexical recognizer's strengths.
EVIDENCE = [
    ('boundary', 'refusal', 'I cannot take this on.', True),
    ('boundary', 'refusal', 'My answer is still no.', True),
    ('boundary', 'refusal', 'I can take this on.', False),
    ('boundary', 'refusal', 'I cannot take this on, unless it is tomorrow.', False),
    ('boundary', 'refusal', 'That exceeds what I am available for.', True),
    ('workload', 'workable_option', 'Could we move the other tasks to Monday?', True),
    ('workload', 'workable_option', 'Could we shift the other tasks to Monday?', True),
    ('workload', 'workable_option', 'I cannot move the other tasks to Monday.', False),
    ('relationship', 'need', 'I need time together.', True),
    ('relationship', 'need', 'They said "I need time together".', False),
    ('relationship', 'practical_request', 'Could we talk on Saturday?', True),
    ('relationship', 'practical_request', 'The weather is nice.', False),
]


def prediction(audio='sadness', confidence=.8):
    labels = ['anger', 'happiness', 'neutral', 'sadness']
    def dist(label):
        return {key: confidence if key == label else (1-confidence)/3 for key in labels}
    return MultimodalEstimate(label='sadness', confidence=confidence, distribution=dist('sadness'),
        text_label='sadness', text_confidence=confidence, text_distribution=dist('sadness'),
        audio_label=audio, audio_confidence=confidence, audio_distribution=dist(audio),
        modalities_agree=audio == 'sadness', confidence_level='high' if confidence >= .55 else 'low',
        low_confidence_threshold=.55, model_version='synthetic-engineering-v1', latency_ms=0, queue_ms=0)


async def main():
    trajectories, latencies = [], []
    for index, (scenario, messages, expected) in enumerate(CASES):
        for policy in ('fixed', 'enhanced'):
            service = ConversationService(MemoryRepository(), generator=TemplateResponseGenerator())
            session = await service.create_session(uuid4())
            session, _, _ = await service.start_roleplay(session.id, session.user_id, scenario,
                Difficulty.INTERMEDIATE, pre_skipped=True, attempt_purpose='retry',
                character_profile='cooperative' if policy == 'enhanced' else None)
            stages = []
            for message in messages:
                if session.roleplay.status != 'active':
                    break
                start = time.perf_counter()
                _, _, session = await service.chat(session.id, session.user_id, message)
                latencies.append((time.perf_counter()-start)*1000)
                stages.append(session.roleplay.dialogue.stage if session.roleplay.dialogue else session.roleplay.status)
            trajectories.append({'case': index+1, 'scenario': scenario, 'policy': policy, 'inputs': messages,
                'stages': stages, 'expected_enhanced_stages': expected, 'consumed_inputs': len(stages),
                'status': session.roleplay.status, 'completion_reason': session.roleplay.completion_reason,
                'transition_match': stages == expected if policy == 'enhanced' else None})
    confusion = dict(TP=0, TN=0, FP=0, FN=0)
    evidence = []
    for scenario, feature, message, expected in EVIDENCE:
        actual = feature in features(scenario, message)
        category = ('T' if actual == expected else 'F') + ('P' if actual else 'N')
        confusion[category] += 1
        evidence.append(dict(scenario=scenario, feature=feature, text=message, expected=expected, actual=actual, result=category))
    affect = []
    for name, estimate, preference, enabled, fallback, action in [
        ('matching', prediction(), 'auto', True, None, 'acknowledge'),
        ('disagreement', prediction('anger'), 'auto', True, None, 'offer_pacing'),
        ('uncertain', prediction(confidence=.4), 'auto', True, None, 'offer_pacing'),
        ('text_only', None, 'auto', True, None, 'baseline'),
        ('model_unavailable', None, 'auto', True, 'model_unavailable', 'baseline'),
        ('disabled', prediction(), 'auto', False, None, 'baseline'),
        ('explicit_choice', prediction(), 'gentler', True, None, 'gentler'),
    ]:
        record = AffectDecision(request_id=uuid4(), session_version=1, user_turn_id=uuid4(), assistant_turn_id=uuid4(),
            prediction=estimate, adaptation_enabled=enabled, preference=preference, fallback_reason=fallback)
        select(record, eligible=True)
        affect.append({'case': name, 'prediction': estimate.model_dump(mode='json') if estimate else None,
                       'action': record.action, 'reason': record.reason, 'expected_action': action, 'passed': record.action == action})
    sources = ['backend/app/services/scenario_dialogue.py', 'backend/app/services/workload_dialogue.py',
               'backend/app/services/affect_pacing.py', 'backend/app/services/roleplay_service.py', 'scripts/evaluate_engineering.py']
    result = {'version': 1, 'recorded_at': datetime.now(UTC).isoformat(), 'synthetic': True, 'scope': 'authored fixtures; no participant data or model inference',
        'environment': {'python': platform.python_version(), 'platform': platform.platform()},
        'source_sha256': {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in sources},
        'dialogue': trajectories, 'evidence': evidence, 'evidence_confusion': confusion, 'affect': affect,
        'latency': {'scope': 'in-process deterministic service with MemoryRepository; excludes HTTP and trained inference',
                    'n': len(latencies), 'p50_ms': statistics.median(latencies),
                    'p95_ms': sorted(latencies)[int(.95*(len(latencies)-1))], 'samples_ms': latencies}}
    output = ROOT/'docs/evidence-package/generated/engineering-v1.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'transition_matches': sum(x['transition_match'] is True for x in trajectories),
                      'enhanced_cases': len(CASES), 'evidence': confusion, 'affect_passes': sum(x['passed'] for x in affect), 'latency': result['latency']}, indent=2))
    return 0 if all(x['transition_match'] is not False for x in trajectories) and all(x['passed'] for x in affect) else 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
